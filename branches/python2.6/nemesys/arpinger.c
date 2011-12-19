
#include <headers.h>

struct devices
{
    char *name;
    char *ip;
    char *net;
    char *mask;
};

int DEBUG_MODE=0;
FILE *debug_log;

int err_flag=0;
char err_str[88]="No Error";

PyGILState_STATE gil_state;
PyObject *py_pcap_hdr, *py_pcap_data;

int ind_dev=0, num_dev=0;

pcap_t *handle;

struct devices device[22];

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

int ip_in_net (const char *ip, const char *net, const char *mask)
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


void initialize(char *dev, int promisc, int timeout, int snaplen, int buffer)
{
    int i=0;

    char errbuf[PCAP_ERRBUF_SIZE];

    find_devices();

    if(err_flag != 0) {return;}

    for(i=1; i<=ind_dev; i++)
    {
        if ((strcmp(dev,device[i].name)==0)||(strcmp(dev,device[i].ip)==0))
        {
            num_dev=i;
        }
    }

	//printf("Device Scelto: %i",num_dev);

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


/*----Python----*/

static PyObject *arpinger_initialize(PyObject *self, PyObject *args)
{
    int promisc=1, timeout=1000, snaplen=BUFSIZ, buffer=22*1024000;

    char *dev, *filter;

    err_flag=0; strcpy(err_str,"No Error");

    PyArg_ParseTuple(args,"z|zi",&dev,&filter,&timeout);

    if (err_flag == 0)
    {initialize(dev, promisc, timeout, snaplen, buffer);}

    if (err_flag == 0)
    {setfilter(filter);}

    return Py_BuildValue("{s:i,s:s}","err_flag",err_flag,"err_str",err_str);
}

static PyObject *arpinger_send(PyObject *self, PyObject *args)
{
    Py_BEGIN_ALLOW_THREADS;
    gil_state = PyGILState_Ensure();

    PyObject *py_pkt;

    char errbuf[PCAP_ERRBUF_SIZE];

    int pkt_size=0;

    u_char *pkt_to_send;

    err_flag=0; strcpy(err_str,"No Error");

    PyArg_ParseTuple(args,"O",&py_pkt);

    pkt_size=(int)PyString_Size(py_pkt);

    pkt_to_send=(u_char*)PyString_AsString(py_pkt);

    if (handle != NULL)
    {
        if (pcap_sendpacket(handle, pkt_to_send, pkt_size) != 0)
        {sprintf(err_str,"Couldn't send the packet: %s",errbuf);err_flag=-1;}
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

static PyObject *arpinger_receive(PyObject *self)
{
    //PyObject *py_pcap_hdr, *py_pcap_data;

    struct pcap_pkthdr *pcap_hdr;
    const u_char *pcap_data;

    int pkt_received=0;

    err_flag=0; strcpy(err_str,"No Error");

    Py_BEGIN_ALLOW_THREADS;
    gil_state = PyGILState_Ensure();

    if (handle != NULL)
    {
        pkt_received=pcap_next_ex(handle,&pcap_hdr,&pcap_data);

        switch (pkt_received)
        {
            case  0 :   err_flag=pkt_received;
                        sprintf(err_str,"Timeout was reached during ARP packet receive");
                        py_pcap_hdr = Py_None;
                        py_pcap_data = Py_None;
                        break;
            case -1 :   err_flag=pkt_received;
                        sprintf(err_str,"Error reading the packet: %s",pcap_geterr(handle));
                        py_pcap_hdr = Py_None;
                        py_pcap_data = Py_None;
                        break;
            case -2 :   err_flag=pkt_received;
                        sprintf(err_str,"Error reading the packet: %s",pcap_geterr(handle));
                        py_pcap_hdr = Py_None;
                        py_pcap_data = Py_None;
                        break;
            default :   err_flag=pkt_received;
                        sprintf(err_str,"ARP packet received");
                        if ((pcap_hdr!=NULL) && (pcap_data!=NULL))
                        {
                          py_pcap_hdr = PyString_FromStringAndSize((const char *)pcap_hdr,sizeof(struct pcap_pkthdr));
                          py_pcap_data = PyString_FromStringAndSize((const char *)pcap_data,(pcap_hdr->caplen));
                        }
                        else
                        {
                          py_pcap_hdr = Py_None;
                          py_pcap_data = Py_None;
                        }
                        break;
        }
    }
    else
    {
        sprintf(err_str,"Couldn't receive any packet: No Hadle Active on Networks Interfaces");err_flag=-1;

        py_pcap_hdr = Py_None;
        py_pcap_data = Py_None;
    }

    PyGILState_Release(gil_state);
    Py_END_ALLOW_THREADS;

    return Py_BuildValue("{s:i,s:s,s:S,s:S}","err_flag",err_flag,"err_str",err_str,"py_pcap_hdr",py_pcap_hdr,"py_pcap_data",py_pcap_data);
}

static PyObject *arpinger_clear(PyObject *self)
{
    err_flag=0; strcpy(err_str,"No Error");

    if (py_pcap_hdr != Py_None)
    {Py_CLEAR(py_pcap_hdr);}
    if (py_pcap_data != Py_None)
    {Py_CLEAR(py_pcap_data);}

    return Py_BuildValue("{s:i,s:s}","err_flag",err_flag,"err_str",err_str);
}

static PyObject *arpinger_close(PyObject *self)
{
    if (handle != NULL) {pcap_close(handle);}

    Py_RETURN_NONE;
}

static PyMethodDef arpinger_methods[] =
{
    { "initialize", (PyCFunction)arpinger_initialize, METH_VARARGS, NULL},
    { "send", (PyCFunction)arpinger_send, METH_VARARGS, NULL},
    { "receive", (PyCFunction)arpinger_receive, METH_NOARGS, NULL},
    { "clear", (PyCFunction)arpinger_clear, METH_NOARGS, NULL},
    { "close", (PyCFunction)arpinger_close, METH_NOARGS, NULL},
    { NULL, NULL, 0, NULL }
};

void initarpinger(void)
{
    Py_InitModule("arpinger", arpinger_methods);
}
