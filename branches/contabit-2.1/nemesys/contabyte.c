
#include <headers.h>

#define IP_ADDR_LEN 4
#define ETHER_ADDR_LEN	6
#define SIZE_ETHERNET 14

struct hdr_ethernet     /* Ethernet header */
{
    u_char ether_dhost[ETHER_ADDR_LEN]; /* Destination host address */
    u_char ether_shost[ETHER_ADDR_LEN]; /* Source host address */
    u_short ether_type;                 /* IP? ARP? RARP? etc */
};

struct hdr_arp          /* Arp header */
{
  u_short hwtype;                   /* Hardware type */
  u_short proto;                    /* Protocol type */
  u_short _hwlen_protolen;          /* Protocol address length */
  u_short opcode;                   /* Opcode */
  u_char  mac_src[ETHER_ADDR_LEN];  /* Source hardware address */
  u_char  arp_src[IP_ADDR_LEN];     /* Source protocol address */
  u_char  mac_dst[ETHER_ADDR_LEN];  /* Target hardware address */
  u_char  arp_dst[IP_ADDR_LEN];     /* Target protocol address */
};

struct hdr_ipv4         /* IPv4 header */
{
    u_char ip_vhl;		    /* version << 4 | header length >> 2 */
#define IP_HL(ip)   (((ip)->ip_vhl) & 0x0f)
#define IP_V(ip)    (((ip)->ip_vhl) >> 4)
    u_char ip_tos;		    /* type of service */
    u_short ip_len;		    /* total length */
    u_short ip_id;		    /* identification */
    u_short ip_off;		    /* fragment offset field */
#define IP_RF 0x8000		/* reserved fragment flag */
#define IP_DF 0x4000		/* dont fragment flag */
#define IP_MF 0x2000		/* more fragments flag */
#define IP_OFFMASK 0x1fff	/* mask for fragmenting bits */
    u_char ip_ttl;		    /* time to live */
    u_char ip_p;		    /* protocol */
    u_short ip_sum;		    /* checksum */
    struct in_addr ip_src,ip_dst; /* source and dest address */
};

struct hdr_ipv6         /* IPv6 header */
{
    u_int32_t    ver_tr_flo;
    u_int16_t    payload_len;
    u_int8_t     next_header;
    u_int8_t     hop_limit;
    u_char       src_addr[16];
    u_char       dst_addr[16];
};

#define IP_VER(ip)  ((((ip)->ver_tr_flo) & 0xf0000000) >> 28)
#define IP_TR(ip)   ((((ip)->ver_tr_flo) & 0x0ff00000) >> 20)
#define IP_FLO(ip)  (((ip)->ver_tr_flo) & 0x000fffff)

struct hdr_tcp          /* TCP header */
{
    u_short th_sport;	    /* source port */
    u_short th_dport;	    /* destination port */
    u_int32_t th_seq;		/* sequence number DA RIVEDERE tcp_seq*/
    u_int32_t th_ack;		/* acknowledgement number DA RIVEDERE tcp_seq*/

    u_char th_offx2;	    /* data offset, rsvd */
#define TH_OFF(th)  (((th)->th_offx2 & 0xf0) >> 4)
    u_char th_flags;
#define TH_FIN 0x01
#define TH_SYN 0x02
#define TH_RST 0x04
#define TH_PUSH 0x08
#define TH_ACK 0x10
#define TH_URG 0x20
#define TH_ECE 0x40
#define TH_CWR 0x80
#define TH_FLAGS (TH_FIN|TH_SYN|TH_RST|TH_ACK|TH_URG|TH_ECE|TH_CWR)
    u_short th_win;		    /* window */
    u_short th_sum;		    /* checksum */
    u_short th_urp;		    /* urgent pointer */
};

struct statistics
{
    u_long  pkt_up_nem;
    u_long  pkt_up_oth;
    u_long  pkt_up_all;

    u_long  pkt_down_nem;
    u_long  pkt_down_oth;
    u_long  pkt_down_all;

    u_long  pkt_tot_nem;
    u_long  pkt_tot_oth;
    u_long  pkt_tot_all;

    u_long  byte_up_nem;
    u_long  byte_up_oth;
    u_long  byte_up_all;

    u_long  byte_down_nem;
    u_long  byte_down_oth;
    u_long  byte_down_all;

    u_long  byte_tot_nem;
    u_long  byte_tot_oth;
    u_long  byte_tot_all;

    u_long  payload_up_nem;
    u_long  payload_up_oth;
    u_long  payload_up_all;

    u_long  payload_down_nem;
    u_long  payload_down_oth;
    u_long  payload_down_all;

    u_long  payload_tot_nem;
    u_long  payload_tot_oth;
    u_long  payload_tot_all;
};

int DEBUG_MODE=0;
FILE *debug_log;

int no_stop=0, hdr_size=0;

struct statistics mystat;

u_long ip_dev_int=0, ip_nem_int=0;


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


int tipo_frame(int datalink)
{
    switch (datalink)
    {
        case 0: return 4;       /* no encaps funziona con 4 */
        case 1: return 14;      /* ethernet */
        case 9: return 5;       /* ppp */
        case 8: return 1;       /* slip */
        case 12: return 0;      /* RAW */
        case 13: return 1;      /* BSD/SLIP ????? */
        case 14: return 0;      /* BSD/PPP ????? */
        case 15: return 22;     /* LAN 802.3 */
        default: return 0;
    }
}


int invalid_ip(const char *ip_string)
{
	char ip_cmp[88];
	u_int ip1,ip2,ip3,ip4;

	if(ip_string==NULL)
	{return 1;}

	if(sscanf(ip_string,"%u.%u.%u.%u", &ip1, &ip2, &ip3, &ip4) != 4)
	{return 1;}

	if((ip1 != 0) && (ip1 <= 255) && (ip2 <= 255) && (ip3 <= 255) && (ip4 <= 255))
	{
		sprintf(ip_cmp,"%u.%u.%u.%u",ip1,ip2,ip3,ip4);
		if(strcmp(ip_cmp,ip_string)!=0){return 1;}
		return 0;
	}
	return 1;
}


void analyzer(const struct pcap_pkthdr *hdr, const u_char *data)
{
    const struct hdr_ethernet *ethernet;    /* The ethernet header */
    const struct hdr_arp *arp;              /* The Arp header */
	const struct hdr_ipv4 *ipv4;            /* The IPv4 header */
	const struct hdr_ipv6 *ipv6;            /* The IPv6 header */
	const struct hdr_tcp *tcp;              /* The TCP header */
	const char *payload;                    /* Packet payload */

	struct in_addr addr;

	u_long ip_src_int=0, ip_dst_int=0;

	u_int size_ipv4=0, size_ipv6=40, size_tcp=0, size_payload=0;

    char type[22], buff_temp[22], mac_src[22], mac_dst[22], src[22], dst[22], up_down[22], txrx[3];
    int proto=0, hdr_len=0, pktpad=0;

    ethernet = (struct hdr_ethernet*)(data);

    sprintf(mac_src,"%.2X:%.2X:%.2X:%.2X:%.2X:%.2X",
            ethernet->ether_shost[0],ethernet->ether_shost[1],ethernet->ether_shost[2],
            ethernet->ether_shost[3],ethernet->ether_shost[4],ethernet->ether_shost[5]);
    sprintf(mac_dst,"%.2X:%.2X:%.2X:%.2X:%.2X:%.2X",
            ethernet->ether_dhost[0],ethernet->ether_dhost[1],ethernet->ether_dhost[2],
            ethernet->ether_dhost[3],ethernet->ether_dhost[4],ethernet->ether_dhost[5]);

    proto = ntohs(ethernet->ether_type);

    switch(proto)
    {
    case 0x0800 :   strcpy(type,"IPv4");

                    ipv4 = (struct hdr_ipv4*)(data + SIZE_ETHERNET);
                    size_ipv4 = IP_HL(ipv4)*4;

                    strcpy(src,inet_ntoa(ipv4->ip_src));
                    strcpy(dst,inet_ntoa(ipv4->ip_dst));

                    switch ((int)(ipv4->ip_p))
                    {
                    case 6  :   strcat(type,"|TCP");
                                tcp = (struct hdr_tcp*)(data + SIZE_ETHERNET + size_ipv4);
                                size_tcp = TH_OFF(tcp)*4;

                                hdr_len=(SIZE_ETHERNET + size_ipv4 + size_tcp);
                                payload = (u_char *)(data + SIZE_ETHERNET + size_ipv4 + size_tcp);
                                size_payload = ntohs(ipv4->ip_len) - (size_ipv4 + size_tcp);
                                break;

                    case 17 :   strcat(type,"|UDP");
                                hdr_len=(SIZE_ETHERNET + size_ipv4 + 8);
                                payload = (u_char *)(data + SIZE_ETHERNET + size_ipv4 + 8);
                                size_payload = ntohs(ipv4->ip_len) - (size_ipv4 + 8);
                                break;

                    case 1  :   strcat(type,"|ICMPv4");
                                break;

                    case 2  :   strcat(type,"|IGMPv4");
                                break;

                    case 89 :   strcat(type,"|OSPF");
                                break;

                    default :   sprintf(buff_temp,"|T:%d",(int)(ipv4->ip_p));
                                strcat(type,buff_temp);
                                break;
                    }
                    break;

    case 0x86dd :   strcpy(type,"IPv6");

                    ipv6 = (struct hdr_ipv6*)(data + SIZE_ETHERNET);
                    size_ipv6 = 40;

                    sprintf(src,"***.***.***.***");
                    sprintf(dst,"***.***.***.***");

                    switch (ipv6->next_header)
                    {
                    case 6  :   strcat(type,"|TCP");
                                tcp = (struct hdr_tcp*)(data + SIZE_ETHERNET + size_ipv6);
                                size_tcp = TH_OFF(tcp)*4;

                                hdr_len=(SIZE_ETHERNET + size_ipv6 + size_tcp);
                                payload = (u_char *)(data + SIZE_ETHERNET + size_ipv6 + size_tcp);
                                size_payload = ntohs(ipv6->payload_len) - (size_tcp);
                                break;
                    case 17 :   strcat(type,"|UDP");
                                hdr_len=(SIZE_ETHERNET + size_ipv6 + 8);
                                payload = (u_char *)(data + SIZE_ETHERNET + size_ipv6 + 8);
                                size_payload = ntohs(ipv6->payload_len) - (8);
                                break;
                    case 1  :   strcat(type,"|ICMPv4");
                                break;
                    case 2  :   strcat(type,"|IGMPv4");
                                break;
                    case 58 :   strcat(type,"|ICMPv6");
                                break;
                    default :   sprintf(buff_temp,"|T:%d",ipv6->next_header);
                                strcat(type,buff_temp);
                                break;
                    }

                    break;

    case 0x0806 :   strcpy(type,"ARP\t");
                    arp = (struct hdr_arp*)(data + SIZE_ETHERNET);
                    switch (ntohs(arp->opcode))
                    {
                    case 1 : strcpy(type,"ARP|REQ\t");
                             break;
                    case 2 : strcpy(type,"ARP|REP\t");
                             break;
                    case 3 : strcpy(type,"RARP|REQ\t");
                             break;
                    case 4 : strcpy(type,"RARP|REP\t");
                             break;
                    }
                    strcpy(src,inet_ntoa (*(struct in_addr*)(arp->arp_src)));
                    strcpy(dst,inet_ntoa (*(struct in_addr*)(arp->arp_dst)));
                    break;

    default     :   strcpy(type,"UNKNOW:");
                    if(proto<0x05dd)
                    {
                        sprintf(buff_temp,"%i byte",proto);
                    }
                    else
                    {
                        sprintf(buff_temp,"%x",proto);
                    }
                    strcat(type,buff_temp);
                    sprintf(src,"***.***.***.***");
                    sprintf(dst,"***.***.***.***");
                    break;
    }


    ip_src_int=(u_long)inet_addr(src);
    ip_dst_int=(u_long)inet_addr(dst);

    if((ip_src_int==ip_dev_int || ip_src_int==ip_nem_int) && (ip_dst_int==ip_dev_int || ip_dst_int==ip_nem_int))
    {
        strcat(type,"|NEM");
    }


    if(ip_src_int!=ip_dev_int)
    {
        strcpy(txrx,"Rx");

        sprintf(up_down,"0\t%d",((hdr->len)+4));

        mystat.pkt_down_all++;
        mystat.pkt_tot_all++;

        mystat.byte_down_all += ((hdr->len)+4);
        mystat.byte_tot_all += ((hdr->len)+4);

        mystat.payload_down_all += size_payload;
        mystat.payload_tot_all += size_payload;

        if((ip_src_int==ip_nem_int) && (ip_dst_int==ip_dev_int))
        {
            mystat.pkt_down_nem++;
            mystat.pkt_tot_nem++;

            mystat.byte_down_nem += ((hdr->len)+4);
            mystat.byte_tot_nem += ((hdr->len)+4);

            mystat.payload_down_nem += size_payload;
            mystat.payload_tot_nem += size_payload;
        }
        else
        {
            mystat.pkt_down_oth++;
            mystat.pkt_tot_oth++;

            mystat.byte_down_oth += ((hdr->len)+4);
            mystat.byte_tot_oth += ((hdr->len)+4);

            mystat.payload_down_oth += size_payload;
            mystat.payload_tot_oth += size_payload;
        }

    }
    else
    {
        strcpy(txrx,"Tx");

        if((pktpad=(60-(hdr->len)))>0)
        {
            sprintf(up_down,"%d+%d\t0",((hdr->len)+4),pktpad);
        }
        else
        {
            sprintf(up_down,"%d\t0",((hdr->len)+4));
        }

        mystat.pkt_up_all++;
        mystat.pkt_tot_all++;

        mystat.byte_up_all += ((hdr->len)+pktpad+4);
        mystat.byte_tot_all += ((hdr->len)+pktpad+4);

        mystat.payload_up_all += size_payload;
        mystat.payload_tot_all += size_payload;

        if((ip_src_int==ip_dev_int) && (ip_dst_int==ip_nem_int))
        {
            mystat.pkt_up_nem++;
            mystat.pkt_tot_nem++;

            mystat.byte_up_nem += ((hdr->len)+pktpad+4);
            mystat.byte_tot_nem += ((hdr->len)+pktpad+4);

            mystat.payload_up_nem += size_payload;
            mystat.payload_tot_nem += size_payload;
        }
        else
        {
            mystat.pkt_up_oth++;
            mystat.pkt_tot_oth++;

            mystat.byte_up_oth += ((hdr->len)+pktpad+4);
            mystat.byte_tot_oth += ((hdr->len)+pktpad+4);

            mystat.payload_up_oth += size_payload;
            mystat.payload_tot_oth += size_payload;
        }
    }

    // DEBUG-BEGIN
    if(DEBUG_MODE)
    {
        fprintf(debug_log,"%li)\t%s\t\t%s\t\t%s\t\t%s\t%li,%.6li\t%s\n",mystat.pkt_tot_all,src,dst,up_down,type,hdr->ts.tv_sec,hdr->ts.tv_usec,txrx);
        fprintf(debug_log,"\t%s\t%s\t%i=%i+%i+4(CRC)\n\n",mac_src,mac_dst,(hdr->len)+4, hdr_len, size_payload);
    }
    // DEBUG-END
}


/*----Python----*/

static PyObject *contabyte_initialize(PyObject *self, PyObject *args)
{
    char *dev, *nem;

    PyArg_ParseTuple(args,"zz",&dev,&nem);

    memset(&mystat,0,sizeof(struct statistics));

    hdr_size=sizeof(struct pcap_pkthdr);

    if (invalid_ip(nem)) {strcpy(nem,"none");}

    ip_dev_int=(u_long)inet_addr(dev);
    ip_nem_int=(u_long)inet_addr(nem);

    // DEBUG-BEGIN
    if(DEBUG_MODE)
    {
        fprintf(debug_log,"\nDevice IP: %s [%li]\tNeMeSys IP: %s [%li]\n",dev,ip_dev_int,nem,ip_nem_int);
    }
    // DEBUG-END

    return Py_BuildValue("i",0);
}

static PyObject *contabyte_analyze(PyObject *self, PyObject *args)
{
    char build_string[282], request_time[44];

    struct tm *rt;
    time_t req_time;

    int datalink=0;

    PyObject *py_pcap_hdr, *py_pcap_data;

    u_char *pcap_hdr;
    u_char *pcap_data;

    PyArg_ParseTuple(args,"OOi",&py_pcap_hdr,&py_pcap_data,&datalink);

    pcap_hdr = (u_char*)PyString_AsString(py_pcap_hdr);
    pcap_data = (u_char*)PyString_AsString(py_pcap_data);

    Py_BEGIN_ALLOW_THREADS;

    no_stop=1;

    analyzer((const struct pcap_pkthdr *)pcap_hdr, pcap_data);

    no_stop=0;

    req_time=time(0);
    rt=localtime(&req_time);
    strftime(request_time, sizeof request_time, "%a %Y/%m/%d %H:%M:%S", (const struct tm *) rt);

    strcpy(build_string,"{s:s,s:l,s:l,s:l,s:l,s:l,s:l,s:l,s:l,s:l,s:l,s:l,s:l,s:l,s:l,s:l,s:l,s:l,s:l,s:l,s:l,s:l,s:l,s:l,s:l,s:l,s:l,s:l}");

    Py_END_ALLOW_THREADS;

    return Py_BuildValue(build_string,
                         "stat_time",request_time,
                         "pkt_up_nem",mystat.pkt_up_nem,"pkt_up_oth",mystat.pkt_up_oth,"pkt_up_all",mystat.pkt_up_all,
                         "pkt_down_nem",mystat.pkt_down_nem,"pkt_down_oth",mystat.pkt_down_oth,"pkt_down_all",mystat.pkt_down_all,
                         "pkt_tot_nem",mystat.pkt_tot_nem,"pkt_tot_oth",mystat.pkt_tot_oth,"pkt_tot_all",mystat.pkt_tot_all,
                         "byte_up_nem",mystat.byte_up_nem,"byte_up_oth",mystat.byte_up_oth,"byte_up_all",mystat.byte_up_all,
                         "byte_down_nem",mystat.byte_down_nem,"byte_down_oth",mystat.byte_down_oth,"byte_down_all",mystat.byte_down_all,
                         "byte_tot_nem",mystat.byte_tot_nem,"byte_tot_oth",mystat.byte_tot_oth,"byte_tot_all",mystat.byte_tot_all,
                         "payload_up_nem",mystat.payload_up_nem,"payload_up_oth",mystat.payload_up_oth,"payload_up_all",mystat.payload_up_all,
                         "payload_down_nem",mystat.payload_down_nem,"payload_down_oth",mystat.payload_down_oth,"payload_down_all",mystat.payload_down_all,
                         "payload_tot_nem",mystat.payload_tot_nem,"payload_tot_oth",mystat.payload_tot_oth,"payload_tot_all",mystat.payload_tot_all);
}

static PyObject *contabyte_close(PyObject *self)
{
    while(no_stop){printf("%i|",no_stop);}

    //DEBUG-BEGIN
    if(DEBUG_MODE) {fclose(debug_log);}
    //DEBUG-END

    return Py_BuildValue("i",0);
}

static PyObject *contabyte_getstat(PyObject *self)
{
    char build_string[282], request_time[44];
    struct tm *rt;
    time_t req_time;

    req_time=time(0);
    rt=localtime(&req_time);
    strftime(request_time, sizeof request_time, "%a %Y/%m/%d %H:%M:%S", (const struct tm *) rt);

    strcpy(build_string,"{s:s,s:l,s:l,s:l,s:l,s:l,s:l,s:l,s:l,s:l,s:l,s:l,s:l,s:l,s:l,s:l,s:l,s:l,s:l,s:l,s:l,s:l,s:l,s:l,s:l,s:l,s:l,s:l}");

    return Py_BuildValue(build_string,
                         "stat_time",request_time,
                         "pkt_up_nem",mystat.pkt_up_nem,"pkt_up_oth",mystat.pkt_up_oth,"pkt_up_all",mystat.pkt_up_all,
                         "pkt_down_nem",mystat.pkt_down_nem,"pkt_down_oth",mystat.pkt_down_oth,"pkt_down_all",mystat.pkt_down_all,
                         "pkt_tot_nem",mystat.pkt_tot_nem,"pkt_tot_oth",mystat.pkt_tot_oth,"pkt_tot_all",mystat.pkt_tot_all,
                         "byte_up_nem",mystat.byte_up_nem,"byte_up_oth",mystat.byte_up_oth,"byte_up_all",mystat.byte_up_all,
                         "byte_down_nem",mystat.byte_down_nem,"byte_down_oth",mystat.byte_down_oth,"byte_down_all",mystat.byte_down_all,
                         "byte_tot_nem",mystat.byte_tot_nem,"byte_tot_oth",mystat.byte_tot_oth,"byte_tot_all",mystat.byte_tot_all,
                         "payload_up_nem",mystat.payload_up_nem,"payload_up_oth",mystat.payload_up_oth,"payload_up_all",mystat.payload_up_all,
                         "payload_down_nem",mystat.payload_down_nem,"payload_down_oth",mystat.payload_down_oth,"payload_down_all",mystat.payload_down_all,
                         "payload_tot_nem",mystat.payload_tot_nem,"payload_tot_oth",mystat.payload_tot_oth,"payload_tot_all",mystat.payload_tot_all);
}

static PyObject *contabyte_debugmode(PyObject *self, PyObject *args)
{
    PyArg_ParseTuple(args, "i", &DEBUG_MODE);

    // DEBUG-BEGIN
    if(DEBUG_MODE) {debug_log = fopen("contabyte.txt","w");}
    // DEBUG-END

    return Py_BuildValue("i",DEBUG_MODE);
}

static PyMethodDef contabyte_methods[] =
{
    { "debugmode", (PyCFunction)contabyte_debugmode, METH_VARARGS, NULL},
    { "initialize", (PyCFunction)contabyte_initialize, METH_VARARGS, NULL},
    { "analyze", (PyCFunction)contabyte_analyze, METH_VARARGS, NULL},
    { "close", (PyCFunction)contabyte_close, METH_NOARGS, NULL},
    { "getstat", (PyCFunction)contabyte_getstat, METH_NOARGS, NULL},
    { NULL, NULL, 0, NULL }
};

void initcontabyte(void)
{
    Py_InitModule("contabyte", contabyte_methods);
}
