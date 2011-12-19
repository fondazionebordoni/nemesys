
#include <headers.h>

struct devices
{
    char *name;
    char *ip;
    char *net;
    char *mask;
};

struct statistics
{
    u_long  pkt_pcap_proc;
    u_long  pkt_pcap_tot;
    u_long  pkt_pcap_drop;
    u_long  pkt_pcap_dropif;
};

int DEBUG_MODE=0;
FILE *debug_log;

char *dump_file;

int err_flag=0;
char err_str[88]="No Error";

PyGILState_STATE gil_state;
PyObject *py_pcap_hdr, *py_pcap_data;

int no_stop=0, ind_dev=0, num_dev=0;

int data_link=0, sniff_mode=0, online=1;

int pkt_start=0, pkt_stop=0;

pcap_t *handle;

struct devices device[22];
struct pcap_stat pcapstat;
struct statistics mystat;


void mydump(u_char *dumpfile, const struct pcap_pkthdr *pcap_hdr, const u_char *pcap_data)
{
    pcap_dump(dumpfile, pcap_hdr, pcap_data);

    mystat.pkt_pcap_proc++;

    // DEBUG-BEGIN
    if(DEBUG_MODE)
    {
        fprintf(debug_log,"\n[My Dump - Packet Number %li]\n",mystat.pkt_pcap_proc);
    }
    // DEBUG-END
}


void dumper(void)
{
    pcap_dumper_t *dumpfile;

    pcap_stats(handle,&pcapstat);

    if((pcapstat.ps_drop)>0 || (pcapstat.ps_ifdrop)>0)
    {
        pcapstat.ps_drop=0;
        pcapstat.ps_ifdrop=0;
    }

    dumpfile = pcap_dump_open(handle,dump_file);

    if (dumpfile == NULL)
    {sprintf(err_str,"Error opening savefile %s for writing: %s\n",dump_file, pcap_geterr(handle));err_flag=-1;return;}

    //DEBUG-BEGIN
    if(DEBUG_MODE)
    {
        fprintf(debug_log,"\n[Infinite Loop]\n");
    }
    //DEBUG-END

    if (pcap_loop(handle, sniff_mode, mydump, (u_char *)dumpfile) == -1)
    {sprintf(err_str,"Pcap loop error: %s",pcap_geterr(handle));err_flag=-1;return;}

    pcap_stats(handle,&pcapstat);

    mystat.pkt_pcap_tot=pcapstat.ps_recv;
    mystat.pkt_pcap_drop=pcapstat.ps_drop;
    mystat.pkt_pcap_dropif=pcapstat.ps_ifdrop;

    pcap_close(handle);

    pcap_dump_close(dumpfile);
}


void print_hex_ascii_line(const u_char *payload, int len, int offset)
{

	int i;
	int gap;
	const u_char *ch;

	/* offset */
	printf("%05d   ", offset);

	/* hex */
	ch = payload;
	for(i = 0; i < len; i++)
	{
		printf("%02x ", *ch);
		ch++;
		/* print extra space after 8th byte for visual aid */
		if (i == 7) {printf(" ");}
	}
	/* print space to handle line less than 8 bytes */
	if (len < 8) {printf(" ");}

	/* fill hex gap with spaces if not full line */
	if (len < 16)
	{
		gap = 16 - len;
		for (i = 0; i < gap; i++) {printf("   ");}
	}
	printf("   ");

	/* ascii (if printable) */
	ch = payload;
	for(i = 0; i < len; i++)
	{
		if (isprint(*ch)) {printf("%c", *ch);}
		else {printf(".");}
		ch++;
	}

	printf("\n");

    return;
}


void print_payload(const u_char *payload, int len)
{

	int len_rem = len;
	int line_width = 16;			/* number of bytes per line */
	int line_len;
	int offset = 0;					/* zero-based offset counter */
	const u_char *ch = payload;

	printf("\n");

	if (len <= 0) {return;}

	/* data fits on one line */
	if (len <= line_width)
	{
		print_hex_ascii_line(ch, len, offset);
		return;
	}

	/* data spans multiple lines */
	for ( ;; )
	{
		/* compute current line length */
		line_len = line_width % len_rem;
		/* print line */
		print_hex_ascii_line(ch, line_len, offset);
		/* compute total remaining */
		len_rem = len_rem - line_len;
		/* shift pointer to remaining bytes to print */
		ch = ch + line_len;
		/* add offset */
		offset = offset + line_width;
		/* check if we have line width chars or less */
		if (len_rem <= line_width)
		{
			/* print last line and get out */
			print_hex_ascii_line(ch, len_rem, offset);
			break;
		}
	}

    return;
}


unsigned int dot_to_int(const char *dot)
{
    u_int res;
    u_int dot1,dot2,dot3,dot4;

    if (sscanf(dot,"%u.%u.%u.%u", &dot1, &dot2, &dot3, &dot4) == 4)
    {
        res=(dot1*16777216)+(dot2*65536)+(dot3*256)+(dot4*1);
        return res;
    }

    return 0;
}


int ip_in_net(const char *ip, const char *net, const char *mask)
{
    u_int ui_ip=0, ui_net=0, ui_mask=0;

    ui_ip = dot_to_int(ip);
    ui_net = dot_to_int(net);
    ui_mask = dot_to_int(mask);

    if ((ui_ip & ui_mask) == (ui_net & ui_mask))
    {return 1;}
    else
    {return 0;}
}


void find_devices(void)
{
    int IpInNet=0;

    char *ip, *net, *mask;
    char errbuf[PCAP_ERRBUF_SIZE];

    struct in_addr addr;

    bpf_u_int32 netp, maskp;

    pcap_if_t *alldevs, *dl;

    #if _WIN32
    WSADATA wsa_Data;
    char HostName[255];
    struct hostent *host_entry;
	int addr_num = 0;
    #endif

    ind_dev=0;

    if (pcap_findalldevs (&alldevs, errbuf) != 0)
    {sprintf(err_str,"FindAllDevs error: %s\n",errbuf);err_flag=-1;return;}

    if (alldevs == NULL)
    {sprintf(err_str,"No Sniffable Device or User Without Root Permissions");err_flag=-1;return;}

    dl=alldevs;

    for(dl=alldevs; dl; dl=dl->next)
    {
        ind_dev++;

        device[ind_dev].name=PyMem_New(char,strlen(dl->name)+1);
        memcpy(device[ind_dev].name,dl->name,strlen(dl->name)+1);

        //printf("\nNAME: %s",device[ind_dev].name);

        if (pcap_lookupnet(dl->name, &netp, &maskp, errbuf) != 0)
        {sprintf (err_str,"LookUpNet Warnings: %s", errbuf);err_flag=0;}

        addr.s_addr = netp;
        net = inet_ntoa(addr);
        device[ind_dev].net=PyMem_New(char,strlen(net)+1);
        memcpy(device[ind_dev].net,net,strlen(net)+1);

        //printf("\nNET: %s",device[ind_dev].net);

        addr.s_addr = maskp;
        mask = inet_ntoa(addr);
        device[ind_dev].mask=PyMem_New(char,strlen(mask)+1);
        memcpy(device[ind_dev].mask,mask,strlen(mask)+1);

        //printf("\nMASK: %s",device[ind_dev].mask);

        if(dl->addresses!=NULL)
        {
            addr.s_addr = ((struct sockaddr_in *)(dl->addresses->addr))->sin_addr.s_addr;
            ip = inet_ntoa(addr);

			//printf("\nProvo: %s",ip);

            IpInNet = ip_in_net(ip,device[ind_dev].net,device[ind_dev].mask);

            if(IpInNet != 1)
            {
                #if _WIN32
                WSAStartup(0x101,&wsa_Data);
                gethostname(HostName, 255);
                host_entry = gethostbyname(HostName);
				addr_num = 0;
				while((IpInNet != 1) && (host_entry->h_addr_list[addr_num] != NULL))
                {
					ip = inet_ntoa (*(struct in_addr *)(host_entry->h_addr_list)[addr_num]);
					//printf("\nProvo: %s",ip);
					IpInNet = ip_in_net(ip,device[ind_dev].net,device[ind_dev].mask);
					addr_num++;
				}
                WSACleanup();
                #else
                while((IpInNet != 1) && (dl->addresses->next))
                {
                    dl->addresses=dl->addresses->next;
                    addr.s_addr = ((struct sockaddr_in *)(dl->addresses->addr))->sin_addr.s_addr;
                    ip = inet_ntoa(addr);
					//printf("\nProvo: %s",ip);
                    IpInNet = ip_in_net(ip,device[ind_dev].net,device[ind_dev].mask);
                }
                #endif
            }

			if(IpInNet == 1)
            {
				device[ind_dev].ip=PyMem_New(char,strlen(ip)+1);
				memcpy(device[ind_dev].ip,ip,strlen(ip)+1);
			}
			else
			{
				device[ind_dev].ip="0.0.0.0";
			}


        }
        else
        {
            device[ind_dev].ip="0.0.0.0";
        }

        //printf("\nIP: %s\n\n",device[ind_dev].ip);
    }

    pcap_freealldevs(alldevs);
}


void initialize(char *dev_sel, int promisc, int timeout, int snaplen, int buffer)
{
    int i=0;

    char errbuf[PCAP_ERRBUF_SIZE];

    memset(&mystat,0,sizeof(struct statistics));

    if (online==0)
    {
        handle=pcap_open_offline(dump_file,errbuf);
    }
    else
    {
        find_devices();

        if(err_flag != 0) {return;}

        for(i=1; i<=ind_dev; i++)
        {
            if ((strcmp(dev_sel,device[i].name)==0)||(strcmp(dev_sel,device[i].ip)==0))
            {
                num_dev=i;
            }
        }

        if (num_dev==0)
        {sprintf(err_str,"Device Not Found or Not Initialized");err_flag=-1;return;}

        if ((handle=pcap_create(device[num_dev].name,errbuf)) == NULL)
        {sprintf (err_str,"Couldn't open device: %s",errbuf);err_flag=-1;return;}

        if (pcap_set_promisc(handle,promisc) != 0)
        {sprintf(err_str,"PromiscuousMode error: %s",pcap_geterr(handle));err_flag=-1;return;}

        if (pcap_set_timeout(handle,timeout) != 0)
        {sprintf(err_str,"Timeout error: %s",pcap_geterr(handle));err_flag=-1;return;}

        if (pcap_set_snaplen(handle,snaplen) != 0)
        {sprintf(err_str,"Snapshot error: %s",pcap_geterr(handle));err_flag=-1;return;}

        if (pcap_set_buffer_size(handle,buffer) !=0)
        {sprintf(err_str,"SetBuffer error: %s",pcap_geterr(handle));err_flag=-1;return;}

        if (pcap_activate(handle) !=0)
        {sprintf(err_str,"Activate error: %s",pcap_geterr(handle));err_flag=-1;return;}

        if (pcap_setnonblock(handle,0,errbuf) !=0)
        {sprintf(err_str,"Non Block error: %s",errbuf);err_flag=-1;return;}
    }

    data_link=pcap_datalink(handle);

    //DEBUG-BEGIN
    if(DEBUG_MODE)
    {
        if(num_dev>0)
        {
            fprintf(debug_log,"\nData Link Type: [%s] %s\n",pcap_datalink_val_to_name(data_link),pcap_datalink_val_to_description(data_link));
        }
    }
    //DEBUG-END
}


void setfilter(const char *filter)
{
    bpf_u_int32 netp, maskp;

    struct bpf_program filterprog;

    char errbuf[PCAP_ERRBUF_SIZE];

    if (pcap_lookupnet(device[num_dev].name, &netp, &maskp, errbuf) != 0)
    {sprintf (err_str,"LookUpNet Warnings: %s", errbuf);err_flag=0;}

    if (pcap_compile(handle,&filterprog,filter,0,maskp) == -1)
    {sprintf(err_str,"Error in pcap_compile filter");err_flag=-1;return;}

    if(pcap_setfilter(handle,&filterprog) == -1)
    {sprintf(err_str,"Error setting filter");err_flag=-1;return;}

    pcap_freecode(&filterprog);
}




/*----Python----*/

static PyObject *sniffer_debugmode(PyObject *self, PyObject *args)
{
    PyArg_ParseTuple(args, "i", &DEBUG_MODE);

    // DEBUG-BEGIN
    if(DEBUG_MODE) {debug_log = fopen("sniffer.txt","w");}
    // DEBUG-END

    return Py_BuildValue("i",DEBUG_MODE);
}

static PyObject *sniffer_getdev(PyObject *self, PyObject *args)
{
    int i=0, find_dev=0;

    char build_string[202];

    char *dev;

    err_flag=0; strcpy(err_str,"No Error");

    PyArg_ParseTuple(args, "|z",&dev);

    find_devices();

    if (err_flag == 0 && dev!=NULL)
    {
        for(i=1; i<=ind_dev; i++)
        {
            if ((strcmp(dev,device[i].name)==0)||(strcmp(dev,device[i].ip)==0))
            {
                find_dev=i;
            }
        }

        if(find_dev!=0)
        {
            if (strcmp(dev,device[find_dev].name)==0)
            {
                return Py_BuildValue ("{s:i,s:s,s:s,s:s,s:s}",
                                      "err_flag",err_flag,"err_str",err_str,
                                      "dev_ip",device[find_dev].ip,"dev_net",device[find_dev].net,"dev_mask",device[find_dev].mask);
            }
            else if (strcmp(dev,device[find_dev].ip)==0)
            {
                return Py_BuildValue ("{s:i,s:s,s:s,s:s,s:s}",
                                      "err_flag",err_flag,"err_str",err_str,
                                      "dev_name",device[find_dev].name,"dev_net",device[find_dev].net,"dev_mask",device[find_dev].mask);
            }
        }
        else
        {
            sprintf(err_str,"Device Not Found");err_flag=-1;
            return Py_BuildValue ("{s:i,s:s}",
                                  "err_flag",err_flag,"err_str",err_str);
        }
    }

    strcpy(build_string,"{s:i,s:s,s:i");

    for(i=1; i<=ind_dev; i++)
    {
        strcat(build_string,",s:s,s:s");
    }

    strcat(build_string,"}");

    return Py_BuildValue (build_string,
                          "err_flag",err_flag,"err_str",err_str,"num_dev",ind_dev,
                          "dev1_name",device[1].name,"dev1_ip",device[1].ip,"dev2_name",device[2].name,"dev2_ip",device[2].ip,
                          "dev3_name",device[3].name,"dev3_ip",device[3].ip,"dev4_name",device[4].name,"dev4_ip",device[4].ip,
                          "dev5_name",device[5].name,"dev5_ip",device[5].ip,"dev6_name",device[6].name,"dev6_ip",device[6].ip,
                          "dev7_name",device[7].name,"dev7_ip",device[7].ip,"dev8_name",device[8].name,"dev8_ip",device[8].ip,
                          "dev9_name",device[9].name,"dev9_ip",device[9].ip,"dev10_name",device[10].name,"dev10_ip",device[10].ip,
                          "dev11_name",device[11].name,"dev11_ip",device[11].ip,"dev12_name",device[12].name,"dev12_ip",device[12].ip,
                          "dev13_name",device[13].name,"dev13_ip",device[13].ip,"dev14_name",device[14].name,"dev14_ip",device[14].ip,
                          "dev15_name",device[15].name,"dev15_ip",device[15].ip,"dev16_name",device[16].name,"dev16_ip",device[16].ip,
                          "dev17_name",device[17].name,"dev17_ip",device[17].ip,"dev18_name",device[18].name,"dev18_ip",device[18].ip,
                          "dev19_name",device[19].name,"dev19_ip",device[19].ip,"dev20_name",device[20].name,"dev20_ip",device[20].ip);
}

static PyObject *sniffer_initialize(PyObject *self, PyObject *args)
{
    int promisc=1, timeout=1, snaplen=BUFSIZ, buffer=44*1024000;

    char *dev;

    err_flag=0; strcpy(err_str,"No Error");

    PyArg_ParseTuple(args, "s|iiiiisii", &dev, &buffer, &snaplen, &timeout, &promisc, &online, &dump_file, &pkt_start, &pkt_stop);

    if (err_flag == 0)
    {initialize(dev, promisc, timeout, snaplen, buffer);}

    // DEBUG-BEGIN
    if(DEBUG_MODE)
    {
        fprintf(debug_log,"\nInitialize Device: %s\n",dev);
        fprintf(debug_log,"\nPromisc: %i\tTimeout: %i\tSnaplen: %i\tBuffer: %i\n",promisc,timeout,snaplen,buffer);
    }
    // DEBUG-END

    return Py_BuildValue("{s:i,s:s}","err_flag",err_flag,"err_str",err_str);
}

static PyObject *sniffer_setfilter(PyObject *self, PyObject *args)
{
    char *filter;

    err_flag=0; strcpy(err_str,"No Error");

    PyArg_ParseTuple(args, "s", &filter);

    if (err_flag == 0 && filter != NULL)
    {setfilter(filter);}

    //DEBUG-BEGIN
    if(DEBUG_MODE)
    {
        fprintf(debug_log,"\nFILTRO: %s \n",filter);
    }
    //DEBUG-END

    return Py_BuildValue("{s:i,s:s}","err_flag",err_flag,"err_str",err_str);
}

static PyObject *sniffer_start(PyObject *self, PyObject *args)
{
    struct pcap_pkthdr *pcap_hdr;
    const u_char *pcap_data;

    int pkt_received=0;

    err_flag=0; strcpy(err_str,"No Error");

    PyArg_ParseTuple(args, "|i", &sniff_mode);

    if (sniff_mode >= 0)
    {
        Py_BEGIN_ALLOW_THREADS;
        gil_state = PyGILState_Ensure();

        no_stop=1;

        if (handle != NULL)
        {
            pkt_received=pcap_next_ex(handle,&pcap_hdr,&pcap_data);

            switch (pkt_received)
            {
            case  0 : err_flag=pkt_received;
                      sprintf(err_str,"Timeout was reached during packet receive");
                      py_pcap_hdr = Py_None;
                      py_pcap_data = Py_None;
                      break;

            case -1 : err_flag=pkt_received;
                      sprintf(err_str,"Error reading the packet: %s",pcap_geterr(handle));
                      py_pcap_hdr = Py_None;
                      py_pcap_data = Py_None;
                      break;

            case -2 : err_flag=pkt_received;
                      sprintf(err_str,"Error reading the packet: %s",pcap_geterr(handle));
                      py_pcap_hdr = Py_None;
                      py_pcap_data = Py_None;
                      break;

            default : err_flag=pkt_received;
                      sprintf(err_str,"One packet received");

                      if ((sniff_mode>0) && (pcap_hdr!=NULL) && (pcap_data!=NULL))
                      {
                          py_pcap_hdr = PyString_FromStringAndSize((const char *)pcap_hdr,sizeof(struct pcap_pkthdr));
                          py_pcap_data = PyString_FromStringAndSize((const char *)pcap_data,(pcap_hdr->caplen));

                          if ((py_pcap_hdr==NULL) || (py_pcap_data==NULL))
                          {
                              py_pcap_hdr = Py_None;
                              py_pcap_data = Py_None;
                          }
                      }
                      else
                      {
                          py_pcap_hdr = Py_None;
                          py_pcap_data = Py_None;
                      }

                      if(online==1)
                      {
                          pcap_stats(handle,&pcapstat);

                          if((mystat.pkt_pcap_proc==0) && ((pcapstat.ps_drop)>0 || (pcapstat.ps_ifdrop)>0))
                          {
                              pcapstat.ps_drop=0;
                              pcapstat.ps_ifdrop=0;
                          }

                          mystat.pkt_pcap_tot=pcapstat.ps_recv;
                          mystat.pkt_pcap_drop=pcapstat.ps_drop;
                          mystat.pkt_pcap_dropif=pcapstat.ps_ifdrop;
                      }

                      mystat.pkt_pcap_proc++;

                      if (pkt_stop>pkt_start && pkt_stop>0)
                      {
                          if (mystat.pkt_pcap_proc<pkt_start || mystat.pkt_pcap_proc>pkt_stop)
                          {
                              err_flag=2;
                              py_pcap_hdr = Py_None;
                              py_pcap_data = Py_None;
                          }
                      }

                      // DEBUG-BEGIN
                      if(DEBUG_MODE)
                      {
                          fprintf(debug_log,"\n%li) CapLen: %i\tLen: %i",mystat.pkt_pcap_proc,(pcap_hdr->caplen),(pcap_hdr->len));
                      }
                      // DEBUG-END

                      break;
            }
        }
        else
        {
            sprintf(err_str,"Couldn't receive any packet: No Hadle Active on Networks Interfaces");err_flag=-1;

            py_pcap_hdr = Py_None;
            py_pcap_data = Py_None;
        }

        // DEBUG-BEGIN
        if(DEBUG_MODE)
        {;}
        // DEBUG-END

        no_stop=0;

        PyGILState_Release(gil_state);
        Py_END_ALLOW_THREADS;

        return Py_BuildValue("{s:i,s:s,s:i,s:S,s:S}","err_flag",err_flag,"err_str",err_str,"datalink",data_link,"py_pcap_hdr",py_pcap_hdr,"py_pcap_data",py_pcap_data);
    }
    else
    {
        Py_BEGIN_ALLOW_THREADS;
        gil_state = PyGILState_Ensure();

        sniff_mode = -1;

        dumper();

        PyGILState_Release(gil_state);
        Py_END_ALLOW_THREADS;

        return Py_BuildValue("{s:i,s:s,s:i,s:s}","err_flag",err_flag,"err_str",err_str,"datalink",data_link,"dumpfile","dumpfile.pcap");
    }
}

static PyObject *sniffer_clear(PyObject *self)
{
    err_flag=0; strcpy(err_str,"No Error");

    if (py_pcap_hdr != Py_None)
    {Py_CLEAR(py_pcap_hdr);}
    if (py_pcap_data != Py_None)
    {Py_CLEAR(py_pcap_data);}

    return Py_BuildValue("{s:i,s:s}","err_flag",err_flag,"err_str",err_str);
}

static PyObject *sniffer_stop(PyObject *self)
{
    err_flag=0; strcpy(err_str,"No Error");

    if (sniff_mode>=0)
    {
        while(no_stop){;}

        pcap_close(handle);

        handle = NULL;
    }
    else
    {
        pcap_breakloop(handle);
    }

    //DEBUG-BEGIN
    if(DEBUG_MODE) {fclose(debug_log);}
    //DEBUG-END

    return Py_BuildValue("{s:i,s:s}","err_flag",err_flag,"err_str",err_str);
}

static PyObject *sniffer_getstat(PyObject *self)
{
    char request_time[44];
    struct tm *rt;
    time_t req_time;

    if (handle != NULL && online==1)
    {
        pcap_stats(handle,&pcapstat);

        mystat.pkt_pcap_tot=pcapstat.ps_recv;
        mystat.pkt_pcap_drop=pcapstat.ps_drop;
        mystat.pkt_pcap_dropif=pcapstat.ps_ifdrop;
    }

    req_time=time(0);
    rt=localtime(&req_time);
    strftime(request_time, sizeof request_time, "%a %Y/%m/%d %H:%M:%S", (const struct tm *) rt);

    return Py_BuildValue("{s:s,s:l,s:l,s:l,s:l}",
                         "stat_time",request_time,"pkt_pcap_proc",mystat.pkt_pcap_proc,
                         "pkt_pcap_tot",mystat.pkt_pcap_tot,"pkt_pcap_drop",mystat.pkt_pcap_drop,"pkt_pcap_dropif",mystat.pkt_pcap_dropif);
}

static PyMethodDef sniffer_methods[] =
{
    { "debugmode", (PyCFunction)sniffer_debugmode, METH_VARARGS, NULL},
    { "getdev", (PyCFunction)sniffer_getdev, METH_VARARGS, NULL},
    { "initialize", (PyCFunction)sniffer_initialize, METH_VARARGS, NULL},
    { "setfilter", (PyCFunction)sniffer_setfilter, METH_VARARGS, NULL},
    { "start", (PyCFunction)sniffer_start, METH_VARARGS, NULL},
    { "clear", (PyCFunction)sniffer_clear, METH_NOARGS, NULL},
    { "stop", (PyCFunction)sniffer_stop, METH_NOARGS, NULL},
    { "getstat", (PyCFunction)sniffer_getstat, METH_NOARGS, NULL},
    { NULL, NULL, 0, NULL }
};

void initsniffer(void)
{
    Py_InitModule("sniffer", sniffer_methods);
}
