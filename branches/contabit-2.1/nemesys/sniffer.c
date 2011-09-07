
#include <sniffer.h>

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

int err_flag=0;
char err_str[88]="No Error";

u_char *blocks_box;

int no_stop=1, ind_dev=0, num_dev=0;

int blocks_num=0, block_ind=0, block_size=0, blocks_offset=0;

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


void mydump(u_char *dumpfile, const struct pcap_pkthdr *pcap_hdr, const u_char *pcap_data)
{
    pcap_dump(dumpfile, pcap_hdr, pcap_data);

    mystat.pkt_pcap_proc++;

    pcap_stats(handle,&pcapstat);

    mystat.pkt_pcap_tot=pcapstat.ps_recv;
    mystat.pkt_pcap_drop=pcapstat.ps_drop;
    mystat.pkt_pcap_dropif=pcapstat.ps_ifdrop;

    // DEBUG-BEGIN
    if(DEBUG_MODE)
    {
        fprintf(debug_log,"\n[My Dump - Packet Number %li]\n",mystat.pkt_pcap_proc);
        //analyze(pcap_hdr,pcap_data,debug_log,device[num_dev].ip,"194.244.5.206");
    }
    // DEBUG-END
}


void mycallback(u_char *unused, const struct pcap_pkthdr *pcap_hdr, const u_char *pcap_data)
{
    int hdr_size=sizeof(struct pcap_pkthdr);
    int data_size=(block_size-hdr_size);
    int pad_size=(data_size-(pcap_hdr->caplen));

    struct pcap_pkthdr *pcap_hdr_mod;

    u_char *block_hdr, *block_data , *block_pad;

    block_hdr=(u_char*)calloc(1,hdr_size);
    block_data=(u_char*)calloc(1,data_size);
    block_pad=(u_char*)calloc(1,pad_size);

    block_ind++;

    pcap_hdr_mod=(struct pcap_pkthdr*)calloc(1,hdr_size);

    memcpy(pcap_hdr_mod,pcap_hdr,hdr_size);

    if (pad_size>0)
    {
        memcpy(block_data,pcap_data,(pcap_hdr->caplen));
        memset(block_pad,0,pad_size);
        memcpy(block_data+(pcap_hdr->caplen),block_pad,pad_size);
    }
    else
    {
        pad_size=0;
        pcap_hdr_mod->caplen=data_size;
        memcpy(block_data,pcap_data,data_size);
    }

    memcpy(block_hdr,pcap_hdr_mod,hdr_size);

    memcpy(blocks_box+blocks_offset+(block_ind*block_size),block_hdr,hdr_size);
    memcpy(blocks_box+blocks_offset+(block_ind*block_size)+hdr_size,block_data,data_size);

    mystat.pkt_pcap_proc++;

    pcap_stats(handle,&pcapstat);

    mystat.pkt_pcap_tot=pcapstat.ps_recv;
    mystat.pkt_pcap_drop=pcapstat.ps_drop;
    mystat.pkt_pcap_dropif=pcapstat.ps_ifdrop;

    // DEBUG-BEGIN
    if(DEBUG_MODE)
    {
        fprintf(debug_log,"\n[My CallBack - Packet Number %li]",mystat.pkt_pcap_proc);
        fprintf(debug_log,"\nPcapHdrSize: %i\tPadSize: %i\tCapLen: %i\tLen: %i",hdr_size,pad_size,(pcap_hdr_mod->caplen),(pcap_hdr_mod->len));
        fprintf(debug_log,"\tBlockSize: %i\tBlockHdrSize: %i\tBlockDataSize: %i\n",block_size,hdr_size,data_size);
        //analyze((const struct pcap_pkthdr *)(blocks_box+blocks_offset+(block_ind*block_size)),blocks_box+blocks_offset+(block_ind*block_size)+hdr_size,debug_log,device[num_dev].ip,"194.244.5.206");
    }
    // DEBUG-END

    free(block_hdr);
    free(block_data);
    free(block_pad);
    free(pcap_hdr_mod);
}


void find_devices()
{
    int i=0;

    char *ip, *net, *mask, *point;
    char errbuf[PCAP_ERRBUF_SIZE];

    struct in_addr addr;

    bpf_u_int32 netp, maskp;

    pcap_if_t *alldevs, *dl;

    #if _WIN32
    WSADATA wsa_Data;
    char HostName[255];
    struct hostent *host_entry;
    #endif

    ind_dev=0;

    if (pcap_findalldevs (&alldevs, errbuf) != 0)
    {sprintf(err_str,"FindAllDevs error: %s\n",errbuf);err_flag=-1;return;}

    dl=alldevs;

    for(dl=alldevs; dl; dl=dl->next)
    {
        ind_dev++;

        device[ind_dev].name=dl->name;

        //printf("\nNAME: %s",device[ind_dev].name);

        if (pcap_lookupnet(dl->name, &netp, &maskp, errbuf) != 0)
        {sprintf (err_str,"LookUpNet error: %s", errbuf);err_flag=-1;}

        addr.s_addr = netp;
        net = inet_ntoa(addr);
        device[ind_dev].net=(char*)calloc(22,sizeof(char));
        memcpy(device[ind_dev].net,net,strlen(net)+1);

        //printf("\nNET: %s",device[ind_dev].net);

        addr.s_addr = maskp;
        mask = inet_ntoa(addr);
        device[ind_dev].mask=(char*)calloc(22,sizeof(char));
        memcpy(device[ind_dev].mask,mask,strlen(mask)+1);

        //printf("\nMASK: %s",device[ind_dev].mask);

        if(dl->addresses!=NULL)
        {
            addr.s_addr = ((struct sockaddr_in *)(dl->addresses->addr))->sin_addr.s_addr;
            ip = inet_ntoa(addr);

            point=strrchr(device[ind_dev].net,'.');
            i=point-device[ind_dev].net+1;

            if(strncmp(ip,device[ind_dev].net,i) != 0)
            {
                #if _WIN32
                WSAStartup(0x101,&wsa_Data);
                gethostname(HostName, 255);
                host_entry = gethostbyname(HostName);
                ip = inet_ntoa (*(struct in_addr *)*host_entry->h_addr_list);
                WSACleanup();
                #else
                while((strncmp(ip,device[ind_dev].net,i) != 0) && (dl->addresses->next))
                {
                    dl->addresses=dl->addresses->next;
                    addr.s_addr = ((struct sockaddr_in *)(dl->addresses->addr))->sin_addr.s_addr;
                    ip = inet_ntoa(addr);
                }
                #endif
            }

            device[ind_dev].ip=(char*)calloc(22,sizeof(char));
            memcpy(device[ind_dev].ip,ip,strlen(ip)+1);

        }
        else
        {
            device[ind_dev].ip="0.0.0.0";
        }

        //printf("\nIP: %s\n\n",device[ind_dev].ip);

    }
}


void initialize(char *dev_sel, int promisc, int timeout, int snaplen, int buffer)
{
    int i=0;

    char errbuf[PCAP_ERRBUF_SIZE];

    memset(&mystat,0,sizeof(struct statistics));

    find_devices();

    err_flag=0; strcpy(err_str,"No Error");

    for(i=1; i<=ind_dev; i++)
    {
        if ((strcmp(dev_sel,device[i].name)==0)||(strcmp(dev_sel,device[i].ip)==0))
        {
            num_dev=i;
        }
    }

    if (num_dev==0)
    {sprintf(err_str,"Device Not Found");err_flag=-1;return;}

    if ((handle=pcap_create(device[num_dev].name,errbuf)) == NULL)
    {sprintf (err_str,"Couldn't open device: %s",errbuf);err_flag=-1;return;}

    if (pcap_set_promisc(handle,promisc) != 0)
    {sprintf(err_str,"PromiscuousMode error: %s",errbuf);err_flag=-1;return;}

    if (pcap_set_timeout(handle,timeout) != 0)
    {sprintf(err_str,"Timeout error: %s",errbuf);err_flag=-1;return;}

    if (pcap_set_snaplen(handle,snaplen) != 0)
    {sprintf(err_str,"Snapshot error: %s",errbuf);err_flag=-1;return;}

    if (pcap_set_buffer_size(handle,buffer) !=0)
    {sprintf(err_str,"SetBuffer error: %s",errbuf);err_flag=-1;return;}

    if (pcap_activate(handle) !=0)
    {sprintf(err_str,"Activate error: %s",errbuf);err_flag=-1;return;}

    //DEBUG-BEGIN
    if(DEBUG_MODE)
    {
        if(num_dev>0)
        {
            fprintf(debug_log,"\nData Link Type: [%s] %s\n",pcap_datalink_val_to_name(pcap_datalink(handle)),pcap_datalink_val_to_description(pcap_datalink(handle)));
        }
    }
    //DEBUG-END
}


void finite_loop()
{
    if (blocks_num==0)
    {
        pcap_stats(handle,&pcapstat);

        mystat.pkt_pcap_tot=pcapstat.ps_recv;
        mystat.pkt_pcap_drop=pcapstat.ps_drop;
        mystat.pkt_pcap_dropif=pcapstat.ps_ifdrop;

        blocks_num=mystat.pkt_pcap_tot-mystat.pkt_pcap_proc;

        if (blocks_num<=0) {return;}
        if (blocks_num>2000) {blocks_num=2000;}
    }

    free(blocks_box);

    blocks_box=(u_char*)calloc((blocks_num*block_size)+blocks_offset,sizeof(u_char));

    memset(blocks_box,0,blocks_offset);

    if(mystat.pkt_pcap_proc==0)
    {
            pcap_stats(handle,&pcapstat);

            if((pcapstat.ps_drop)>0 || (pcapstat.ps_ifdrop)>0)
            {
                pcapstat.ps_drop=0;
                pcapstat.ps_ifdrop=0;
            }
    }

    //DEBUG-BEGIN
    if(DEBUG_MODE)
    {
        fprintf(debug_log,"\n[Finite Loop]\n");
    }
    //DEBUG-END

    block_ind=-1;

    pcap_loop(handle, blocks_num, mycallback, NULL);
}


void infinite_loop()
{
    pcap_dumper_t *dumpfile;

    char filename[]="dumpfile.pcap";

    pcap_stats(handle,&pcapstat);

    if((pcapstat.ps_drop)>0 || (pcapstat.ps_ifdrop)>0)
    {
        pcapstat.ps_drop=0;
        pcapstat.ps_ifdrop=0;
    }

    dumpfile = pcap_dump_open(handle,filename);

    if (dumpfile == NULL)
    {sprintf(err_str,"Error opening savefile %s for writing: %s\n",filename, pcap_geterr(handle));err_flag=-1;return;}

    //DEBUG-BEGIN
    if(DEBUG_MODE)
    {
        fprintf(debug_log,"\n[Infinite Loop]\n");
    }
    //DEBUG-END

    pcap_loop(handle, blocks_num, mydump, (u_char *)dumpfile);

    pcap_stats(handle,&pcapstat);

    mystat.pkt_pcap_tot=pcapstat.ps_recv;
    mystat.pkt_pcap_drop=pcapstat.ps_drop;
    mystat.pkt_pcap_dropif=pcapstat.ps_ifdrop;

    pcap_close(handle);

    pcap_dump_close(dumpfile);
}


/*----Python----*/

static PyObject *sniffer_getdev(PyObject *self, PyObject *args)
{
    int i=0, find_dev=0;

    char build_string[202];

    char *dev=(char*)calloc(88,sizeof(char));

    err_flag=0; strcpy(err_str,"No Error");

    PyArg_ParseTuple(args, "|z",&dev);

    find_devices();

    if (dev!=NULL)
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
    int promisc=1, timeout=1, snaplen=BUFSIZ, buffer=32*1024000;

    char *dev_sel=(char*)calloc(88,sizeof(char));

    err_flag=0; strcpy(err_str,"No Error");

    PyArg_ParseTuple(args, "s|iiii", &dev_sel, &buffer, &snaplen, &timeout, &promisc);

    initialize(dev_sel, promisc, timeout, snaplen, buffer);

    block_size=snaplen;

    // DEBUG-BEGIN
    if(DEBUG_MODE)
    {
        fprintf(debug_log,"\nInitialize Device: %s\n",dev_sel);
        fprintf(debug_log,"\nPromisc: %i\tTimeout: %i\tSnaplen: %i\tBuffer: %i\tBlock Size: %i\n",promisc,timeout,snaplen,buffer,block_size);
    }
    // DEBUG-END

    return Py_BuildValue("{s:i,s:s}","err_flag",err_flag,"err_str",err_str);
}

static PyObject *sniffer_start(PyObject *self, PyObject *args)
{
    PyObject *py_byte_array;

    err_flag=0; strcpy(err_str,"No Error");

    PyArg_ParseTuple(args, "|i", &blocks_num);

    if (blocks_num>=0)
    {
        Py_BEGIN_ALLOW_THREADS;

        no_stop=1;

        finite_loop();

        if (blocks_num==0)
        {
            free(blocks_box);

            blocks_box=(u_char*)calloc(8+blocks_offset,sizeof(u_char));

            memset(blocks_box,0,8+blocks_offset);

            py_byte_array=PyByteArray_FromStringAndSize(blocks_box,8+blocks_offset);
        }
        else
        {
            py_byte_array=PyByteArray_FromStringAndSize(blocks_box,(blocks_num*block_size)+blocks_offset);

            // DEBUG-BEGIN
            if(DEBUG_MODE)
            {
                fprintf(debug_log,"\nNumero di Pacchetti: %i\t",blocks_num);
                fprintf(debug_log,"Dimensione del ByteArray: %i\n\n",(int)PyByteArray_Size(py_byte_array));
                //print_payload(blocks_box,(block_size*2)+blocks_offset);
            }
            // DEBUG-END

        }

        no_stop=0;

        Py_END_ALLOW_THREADS;

        return Py_BuildValue("{s:i,s:i,s:i,s:O}","block_size",block_size,"blocks_num",blocks_num,"datalink",pcap_datalink(handle),"py_byte_array",py_byte_array);
    }
    else
    {
        Py_BEGIN_ALLOW_THREADS;

        infinite_loop();

        Py_END_ALLOW_THREADS;

        return Py_BuildValue("{s:i,s:s,s:i,s:s}","err_flag",err_flag,"err_str",err_str,"datalink",pcap_datalink(handle),"dumpfile","dumpfile.pcap");
    }
}

static PyObject *sniffer_stop(PyObject *self)
{
    err_flag=0; strcpy(err_str,"No Error");

    if (blocks_num>=0)
    {
        while(no_stop){;}

        pcap_stats(handle,&pcapstat);

        mystat.pkt_pcap_tot=pcapstat.ps_recv;
        mystat.pkt_pcap_drop=pcapstat.ps_drop;
        mystat.pkt_pcap_dropif=pcapstat.ps_ifdrop;

        pcap_close(handle);

        free(blocks_box);
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
    char build_string[44], request_time[44];
    struct tm *rt;
    time_t req_time;

    req_time=time(0);
    rt=localtime(&req_time);
    strftime(request_time, sizeof request_time, "%a %Y/%m/%d %H:%M:%S", (const struct tm *) rt);

    strcpy(build_string,"{s:s,s:l,s:l,s:l,s:l}");

    return Py_BuildValue(build_string,
                         "stat_time",request_time,"pkt_pcap_proc",mystat.pkt_pcap_proc,
                         "pkt_pcap_tot",mystat.pkt_pcap_tot,"pkt_pcap_drop",mystat.pkt_pcap_drop,"pkt_pcap_dropif",mystat.pkt_pcap_dropif);
}

static PyObject *sniffer_debugmode(PyObject *self, PyObject *args)
{
    PyArg_ParseTuple(args, "i", &DEBUG_MODE);

    // DEBUG-BEGIN
    if(DEBUG_MODE) {debug_log = fopen("sniffer.txt","w");}
    // DEBUG-END

    return Py_BuildValue("i",DEBUG_MODE);
}

static PyMethodDef sniffer_methods[] =
{
    { "debugmode", (PyCFunction)sniffer_debugmode, METH_VARARGS, NULL},
    { "getdev", (PyCFunction)sniffer_getdev, METH_VARARGS, NULL},
    { "initialize", (PyCFunction)sniffer_initialize, METH_VARARGS, NULL},
    { "start", (PyCFunction)sniffer_start, METH_VARARGS, NULL},
    { "stop", (PyCFunction)sniffer_stop, METH_NOARGS, NULL},
    { "getstat", (PyCFunction)sniffer_getstat, METH_NOARGS, NULL},
    { NULL, NULL, 0, NULL }
};

void initsniffer(void)
{
    Py_InitModule("sniffer", sniffer_methods);
}

//printf("\n\nFIN QUI TUTTO OK\n\n");
