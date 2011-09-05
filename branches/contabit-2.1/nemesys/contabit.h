//contabit header file

#include <Python.h>
#include <pcap.h>

#ifdef HAVE_SYS_TYPES_H
#include <sys/types.h>
#endif

#ifdef HAVE_NETINET_IN_H
#include <netinet/in.h>
#endif

#ifndef _WIN32
#include <arpa/inet.h>
#include <netdb.h>
#endif

#ifdef HAVE_SYS_TYPES_H
#include <sys/types.h>
#endif

#ifdef HAVE_SYS_SOCKET_H
#include <sys/socket.h>
#endif

#ifdef HAVE_WINSOCK2_H
#include <winsock2.h>
#endif

#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <time.h>
#include <math.h>

#define IP_ADDR_LEN 4
#define ETHER_ADDR_LEN	6
#define SIZE_ETHERNET 14

/* Ethernet header */
struct	ether_addr {
	u_char octet[ETHER_ADDR_LEN];
};

struct hdr_ethernet
{
    u_char ether_dhost[ETHER_ADDR_LEN]; /* Destination host address */
    u_char ether_shost[ETHER_ADDR_LEN]; /* Source host address */
    u_short ether_type;                 /* IP? ARP? RARP? etc */
};

/* Arp header */
struct hdr_arp
{
  u_short hwtype;                   /* Hardware type */
  u_short proto;                    /* Protocol type */
  u_short _hwlen_protolen;          /* Protocol address length */
  u_short opcode;                   /* Opcode */
  u_short eth_src1;
  u_short eth_src2;
  u_short eth_src3;                 /* Source hardware address */
  u_char  arp_src[IP_ADDR_LEN];     /* Source protocol address */
  u_short eth_dst1;
  u_short eth_dst2;
  u_short eth_dst3;;                /* Target hardware address */
  u_char  arp_dst[IP_ADDR_LEN];     /* Target protocol address */
};

/* IP header */
struct hdr_ipv4
{
    u_char ip_vhl;		    /* version << 4 | header length >> 2 */
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

#define IP_HL(ip)		(((ip)->ip_vhl) & 0x0f)
#define IP_V(ip)		(((ip)->ip_vhl) >> 4)

/* IPv6 header */
struct hdr_ipv6
{
#if defined(WORDS_BIGENDIAN)
  u_int8_t       version:4,
                 traffic_class_high:4;
  u_int8_t       traffic_class_low:4,
                 flow_label_high:4;
#else
  u_int8_t       traffic_class_high:4,
                 version:4;
  u_int8_t       flow_label_high:4,
                 traffic_class_low:4;
#endif
  u_int16_t      flow_label_low;
  u_int16_t      payload_len;
  u_int8_t       next_header;
  u_int8_t       hop_limit;
  u_int8_t       src_addr[16];
  u_int8_t       dst_addr[16];
};

/* TCP header */
struct hdr_tcp
{
    u_short th_sport;	    /* source port */
    u_short th_dport;	    /* destination port */
    u_int32_t th_seq;		/* sequence number DA RIVEDERE tcp_seq*/
    u_int32_t th_ack;		/* acknowledgement number DA RIVEDERE tcp_seq*/

    u_char th_offx2;	    /* data offset, rsvd */
#define TH_OFF(th)	(((th)->th_offx2 & 0xf0) >> 4)
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

struct devices
{
    char *name;
    char *ip;
    char *net;
    char *mask;
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

    u_long  pkt_pcap_tot;
    u_long  pkt_pcap_drop;
    u_long  pkt_pcap_dropif;
};
