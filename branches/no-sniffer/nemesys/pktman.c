
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

int no_stop=0, tot_dev=0, num_dev=0;

int data_link=0, sniff_mode=0, online=1;

int pkt_start=0, pkt_stop=0;

pcap_t *handle;

struct devices device[22];
struct pcap_stat pcapstat;
struct statistics mystat;


void print_hex_ascii_line(const u_char *payload, int len, int offset)
{

	int i;
	int gap;
	const u_char *ch;

	/* offset */
	fprintf(debug_log,"%05d   ", offset);

	/* hex */
	ch = payload;
	for(i = 0; i < len; i++)
	{
		fprintf(debug_log,"%02x ", *ch);
		ch++;
		/* print extra space after 8th byte for visual aid */
		if (i == 7) {fprintf(debug_log," ");}
	}
	/* print space to handle line less than 8 bytes */
	if (len < 8) {fprintf(debug_log," ");}

	/* fill hex gap with spaces if not full line */
	if (len < 16)
	{
		gap = 16 - len;
		for (i = 0; i < gap; i++) {fprintf(debug_log,"   ");}
	}
	fprintf(debug_log,"   ");

	/* ascii (if printable) */
	ch = payload;
	for(i = 0; i < len; i++)
	{
		if (isprint(*ch)) {fprintf(debug_log,"%c", *ch);}
		else {fprintf(debug_log,".");}
		ch++;
	}

	fprintf(debug_log,"\n");

    return;
}


void print_payload(const u_char *payload, int len)
{

	int len_rem = len;
	int line_width = 16;			/* number of bytes per line */
	int line_len;
	int offset = 0;					/* zero-based offset counter */
	const u_char *ch = payload;

	fprintf(debug_log,"\n");

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

    //DEBUG-BEGIN
    if(DEBUG_MODE)
    {
        fprintf(debug_log,"\nFILTRO: %s \n",filter);
    }
    //DEBUG-END
}


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


int sniffer(int sniff_mode)
{
    struct pcap_pkthdr *pcap_hdr;
    const u_char *pcap_data;

    int pkt_received=0;

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
                      fprintf(debug_log,"\n[Packet N.%li\t\tCapLen: %i\t\tLen: %i\t\tTime: %li.%li]",mystat.pkt_pcap_proc,(pcap_hdr->caplen),(pcap_hdr->len),(pcap_hdr->ts.tv_sec),(pcap_hdr->ts.tv_usec));
                      print_payload(pcap_data,pcap_hdr->caplen);
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

    return pkt_received;
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

    char mask255[] = "255.255.255.255";

    ui_ip = dot_to_int(ip);
    ui_net = dot_to_int(net);
    ui_mask = dot_to_int(mask);

    if (((ui_ip & ui_mask) == (ui_net & ui_mask)) && (ui_mask!=0))
    {return 1;}
    else if (strcmp(mask,mask255)==0)
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

    tot_dev=0;

    if (pcap_findalldevs (&alldevs, errbuf) != 0)
    {sprintf(err_str,"FindAllDevs error: %s\n",errbuf);err_flag=-1;return;}

    if (alldevs == NULL)
    {sprintf(err_str,"No Sniffable Device or User Without Root Permissions");err_flag=-1;return;}

    dl=alldevs;

    for(dl=alldevs; dl; dl=dl->next)
    {
        tot_dev++;

        device[tot_dev].name=PyMem_New(char,strlen(dl->name)+1);
        memcpy(device[tot_dev].name,dl->name,strlen(dl->name)+1);

        if (pcap_lookupnet(dl->name, &netp, &maskp, errbuf) != 0)
        {sprintf (err_str,"LookUpNet Warnings: %s", errbuf);err_flag=0;}

        addr.s_addr = netp;
        net = inet_ntoa(addr);
        device[tot_dev].net=PyMem_New(char,strlen(net)+1);
        memcpy(device[tot_dev].net,net,strlen(net)+1);

        addr.s_addr = maskp;
        mask = inet_ntoa(addr);
        device[tot_dev].mask=PyMem_New(char,strlen(mask)+1);
        memcpy(device[tot_dev].mask,mask,strlen(mask)+1);

        // DEBUG-BEGIN
        if(DEBUG_MODE)
        {
            fprintf(debug_log,"\nNAME: %s",device[tot_dev].name);
            fprintf(debug_log,"\nNET: %s",device[tot_dev].net);
            fprintf(debug_log,"\nMASK: %s",device[tot_dev].mask);
        }
        // DEBUG-END//

        if(dl->addresses!=NULL)
        {
            addr.s_addr = ((struct sockaddr_in *)(dl->addresses->addr))->sin_addr.s_addr;
            ip = inet_ntoa(addr);
            // DEBUG-BEGIN
            if(DEBUG_MODE)
            {
                fprintf(debug_log,"\nAddrPcap: %s",ip);
            }
            // DEBUG-END//
            IpInNet = ip_in_net(ip,device[tot_dev].net,device[tot_dev].mask);

            while((IpInNet != 1) && (dl->addresses->next))
            {
                dl->addresses=dl->addresses->next;
                addr.s_addr = ((struct sockaddr_in *)(dl->addresses->addr))->sin_addr.s_addr;
                ip = inet_ntoa(addr);
                // DEBUG-BEGIN
                if(DEBUG_MODE)
                {
                    fprintf(debug_log,"\nAddrPcap: %s",ip);
                }
                // DEBUG-END//
                IpInNet = ip_in_net(ip,device[tot_dev].net,device[tot_dev].mask);
            }

            #if _WIN32
            if(IpInNet != 1)
            {
                WSAStartup(0x101,&wsa_Data);
                gethostname(HostName, 255);
                host_entry = gethostbyname(HostName);
				addr_num = 0;
				while((IpInNet != 1) && (host_entry->h_addr_list[addr_num] != NULL))
                {
					ip = inet_ntoa (*(struct in_addr *)(host_entry->h_addr_list)[addr_num]);
                    // DEBUG-BEGIN
                    if(DEBUG_MODE)
                    {
                        fprintf(debug_log,"\nAddrWin: %s",ip);
                    }
                    // DEBUG-END//
					IpInNet = ip_in_net(ip,device[tot_dev].net,device[tot_dev].mask);
					addr_num++;
				}
                WSACleanup();
            }
            #endif

			if(IpInNet == 1)
            {
				device[tot_dev].ip=PyMem_New(char,strlen(ip)+1);
				memcpy(device[tot_dev].ip,ip,strlen(ip)+1);
			}
			else
			{
				device[tot_dev].ip="0.0.0.0";
			}
        }
        else
        {
            device[tot_dev].ip="0.0.0.0";
        }

        // DEBUG-BEGIN
        if(DEBUG_MODE)
        {
            fprintf(debug_log,"\nIP: %s\n\n",device[tot_dev].ip);
        }
        // DEBUG-END//
    }

    pcap_freealldevs(alldevs);
}


void select_device(char *dev)
{
    int indice=0, IpInNet=0, active=0;

    int find[22];

    char errbuf[PCAP_ERRBUF_SIZE];

    find_devices();
    if(err_flag != 0) {return;}

    num_dev=0;

    for(num_dev=1; num_dev<=tot_dev; num_dev++)
    {
        IpInNet = ip_in_net(dev,device[num_dev].net,device[num_dev].mask);

        // DEBUG-BEGIN
        if(DEBUG_MODE)
        {
            fprintf(debug_log,"\nREQUEST: %s\nNAME: %s\nIP: %s\nNET: %s\nMASK: %s\nIpInNet: %i\n",dev,device[num_dev].name,device[num_dev].ip,device[num_dev].net,device[num_dev].mask,IpInNet);
        }
        // DEBUG-END//

        if (strstr(device[num_dev].name,dev)!=NULL||(strcmp(dev,device[num_dev].name)==0)||(strcmp(dev,device[num_dev].ip)==0)||(IpInNet==1))
        {
            indice++;
            find[indice]=num_dev;
            //printf("\nFIND n°%i = %i\n",indice,num_dev);
        }
    }

    num_dev=0;

    while (indice!=0)
    {
        num_dev=find[indice];
        //printf("\nDevice Scelto: %i\n",num_dev);

        indice--;

        if (indice>0)
        {
            if ((handle=pcap_open_live(device[num_dev].name,BUFSIZ,1,4000,errbuf)) == NULL)
            {
                if ((handle=pcap_open_live(device[num_dev].name,BUFSIZ,0,4000,errbuf)) == NULL)
                {sprintf (err_str,"Couldn't open device: %s",errbuf);err_flag=-1;return;}
            }

            active=sniffer(1);

            pcap_stats(handle,&pcapstat);

            //printf("\nActive: %i\tPacchetti: %i\n",active,pcapstat.ps_recv);
            if ((active>0)||(pcapstat.ps_recv > 0))
            {indice=0;}

            err_flag=0; strcpy(err_str,"No Error");
            pcap_close(handle);
        }
    }

    if (num_dev==0)
    {sprintf(err_str,"Device Not Found or Not Initialized");err_flag=-1;return;}
}


void initialize(char *dev, int promisc, int timeout, int snaplen, int buffer)
{
    char errbuf[PCAP_ERRBUF_SIZE];

    memset(&mystat,0,sizeof(struct statistics));

    if (online==0)
    {
        handle=pcap_open_offline(dump_file,errbuf);
    }
    else
    {
        select_device(dev);
        if(err_flag != 0) {return;}

        if ((handle=pcap_create(device[num_dev].name,errbuf)) == NULL)
        {sprintf (err_str,"Couldn't open device: %s",errbuf);err_flag=-1;return;}

        if (pcap_set_timeout(handle,timeout) != 0)
        {sprintf(err_str,"Timeout error: %s",pcap_geterr(handle));err_flag=-1;return;}

        if (pcap_set_snaplen(handle,snaplen) != 0)
        {sprintf(err_str,"Snapshot error: %s",pcap_geterr(handle));err_flag=-1;return;}

        if (pcap_set_buffer_size(handle,buffer) !=0)
        {sprintf(err_str,"SetBuffer error: %s",pcap_geterr(handle));err_flag=-1;return;}
        
        if (pcap_set_promisc(handle,promisc) != 0)
        {sprintf(err_str,"PromiscuousMode error: %s",pcap_geterr(handle));err_flag=-1;return;}

        if (pcap_activate(handle) !=0)
        {
            if (pcap_set_promisc(handle,0) != 0)
            {sprintf(err_str,"PromiscuousMode error: %s",pcap_geterr(handle));err_flag=-1;return;}
            if (pcap_activate(handle) !=0)
            {sprintf(err_str,"Activate error: %s",pcap_geterr(handle));err_flag=-1;return;}
        }

        data_link=pcap_datalink(handle);

        //DEBUG-BEGIN
        if(DEBUG_MODE)
        {
            if(num_dev>0)
            {
                fprintf(debug_log,"\nInitialize Device: %s\n",dev);
                fprintf(debug_log,"\nPromisc: %i\tTimeout: %i\tSnaplen: %i\tBuffer: %i\n",promisc,timeout,snaplen,buffer);
                fprintf(debug_log,"\nData Link Type: %i - %s - %s\n",data_link,pcap_datalink_val_to_name(data_link),pcap_datalink_val_to_description(data_link));
            }
        }
        //DEBUG-END
    }
}




/*----Python----*/

static PyObject *pktman_debugmode(PyObject *self, PyObject *args)
{
    PyArg_ParseTuple(args, "i", &DEBUG_MODE);

    // DEBUG-BEGIN
    if(DEBUG_MODE) {debug_log = fopen("pktman.txt","w");}
    // DEBUG-END

    return Py_BuildValue("i",DEBUG_MODE);
}

static PyObject *pktman_getdev(PyObject *self, PyObject *args)
{
    int i=0;

    char build_string[202];

    char *dev=NULL;

    err_flag=0; strcpy(err_str,"No Error");

    PyArg_ParseTuple(args, "|z",&dev);

    if (dev!=NULL)
    {
        select_device(dev);
        if(err_flag != 0) {return Py_BuildValue ("{s:i,s:s}","err_flag",err_flag,"err_str",err_str);}

        return Py_BuildValue ("{s:i,s:s,s:s,s:s,s:s,s:s}",
                              "err_flag",err_flag,"err_str",err_str,
                              "dev_name",device[num_dev].name,"dev_ip",device[num_dev].ip,
                              "dev_net",device[num_dev].net,"dev_mask",device[num_dev].mask);
    }

    find_devices();
    if(err_flag != 0) {return Py_BuildValue ("{s:i,s:s}","err_flag",err_flag,"err_str",err_str);}

    strcpy(build_string,"{s:i,s:s,s:i");

    for(i=1; i<=tot_dev; i++)
    {
        strcat(build_string,",s:s,s:s");
    }

    strcat(build_string,"}");

    return Py_BuildValue (build_string,
                          "err_flag",err_flag,"err_str",err_str,"tot_dev",tot_dev,
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

static PyObject *pktman_initialize(PyObject *self, PyObject *args)
{
    int promisc=1, timeout=1, snaplen=BUFSIZ, buffer=44*1024000;

    char *dev;

    err_flag=0; strcpy(err_str,"No Error");

    PyArg_ParseTuple(args, "s|iiiiizii", &dev, &buffer, &snaplen, &timeout, &promisc, &online, &dump_file, &pkt_start, &pkt_stop);

    if (err_flag == 0)
    {initialize(dev, promisc, timeout, snaplen, buffer);}

    return Py_BuildValue("{s:i,s:s}","err_flag",err_flag,"err_str",err_str);
}

static PyObject *pktman_setfilter(PyObject *self, PyObject *args)
{
    char *filter;

    err_flag=0; strcpy(err_str,"No Error");

    PyArg_ParseTuple(args, "s", &filter);

    if (handle != NULL && filter != NULL)
    {setfilter(filter);}
    else
    {sprintf(err_str,"Couldn't Set Filter: No Hadle Active on Networks Interfaces");err_flag=-1;}

    return Py_BuildValue("{s:i,s:s}","err_flag",err_flag,"err_str",err_str);
}

static PyObject *pktman_push(PyObject *self, PyObject *args)
{
    Py_BEGIN_ALLOW_THREADS;
    gil_state = PyGILState_Ensure();

    PyObject *py_pkt;

    int pkt_size=0;

    u_char *pkt_to_send;

    err_flag=0; strcpy(err_str,"No Error");

    PyArg_ParseTuple(args,"O",&py_pkt);

    pkt_size=(int)PyString_Size(py_pkt);

    pkt_to_send=(u_char*)PyString_AsString(py_pkt);

    if (handle != NULL)
    {
        if (pcap_sendpacket(handle, pkt_to_send, pkt_size) != 0)
        {sprintf(err_str,"Couldn't send the packet: %s",pcap_geterr(handle));err_flag=-1;}
    }
    else
    {
        sprintf(err_str,"Couldn't send any packet: No Hadle Active on Networks Interfaces");err_flag=-1;
    }

//    if((py_pkt->ob_refcnt)>0)
//    {Py_CLEAR(py_pkt);}

    PyGILState_Release(gil_state);
    Py_END_ALLOW_THREADS;

    return Py_BuildValue("{s:i,s:s}","err_flag",err_flag,"err_str",err_str);
}

static PyObject *pktman_pull(PyObject *self, PyObject *args)
{
    err_flag=0; strcpy(err_str,"No Error");

    PyArg_ParseTuple(args, "|i", &sniff_mode);

    if (sniff_mode >= 0)
    {
        Py_BEGIN_ALLOW_THREADS;
        gil_state = PyGILState_Ensure();

        sniffer(sniff_mode);

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

static PyObject *pktman_clear(PyObject *self)
{
    err_flag=0; strcpy(err_str,"No Error");

    if (py_pcap_hdr != Py_None)
    {Py_CLEAR(py_pcap_hdr);}
    if (py_pcap_data != Py_None)
    {Py_CLEAR(py_pcap_data);}

    return Py_BuildValue("{s:i,s:s}","err_flag",err_flag,"err_str",err_str);
}

static PyObject *pktman_close(PyObject *self)
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

static PyObject *pktman_getstat(PyObject *self)
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

static PyMethodDef pktman_methods[] =
{
    { "debugmode", (PyCFunction)pktman_debugmode, METH_VARARGS, NULL},
    { "getdev", (PyCFunction)pktman_getdev, METH_VARARGS, NULL},
    { "initialize", (PyCFunction)pktman_initialize, METH_VARARGS, NULL},
    { "setfilter", (PyCFunction)pktman_setfilter, METH_VARARGS, NULL},
    { "push", (PyCFunction)pktman_push, METH_VARARGS, NULL},
    { "pull", (PyCFunction)pktman_pull, METH_VARARGS, NULL},
    { "clear", (PyCFunction)pktman_clear, METH_NOARGS, NULL},
    { "close", (PyCFunction)pktman_close, METH_NOARGS, NULL},
    { "getstat", (PyCFunction)pktman_getstat, METH_NOARGS, NULL},
    { NULL, NULL, 0, NULL }
};

void initpktman(void)
{
    Py_InitModule("pktman", pktman_methods);
}
