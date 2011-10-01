# contabyte.py
# -*- coding: utf8 -*-

# Copyright (c) 2010 Fondazione Ugo Bordoni.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from exceptions import Exception
from logger import logging

import socket
import string
import struct
import time

logger = logging.getLogger()


##############
#Pcap Pkt Hdr#
##############

# Costant
PCAP_HDR_LEN        = 16

# Header Structure and Dictionary
PCAP_HDR =                      \
{                               \
'hdrType'    : 'PCAP',          \
'hdrStruct'  : 'LLII',          \
'tsSec'      : 0,               \
'tsUsec'     : 0,               \
'pktCaplen'  : 0,               \
'pktLen'     : 0,               \
}                               \


###########
#ETHERTNET#
###########

# Costant
ETH_HDR_LEN        = 14
ETH_CRC_LEN        = 4

ETH_LEN_MIN        = 64        # minimum frame length with CRC
ETH_LEN_MAX        = 1518      # maximum frame length with CRC

ETH_MTU            = (ETH_LEN_MAX - ETH_HDR_LEN - ETH_CRC_LEN)
ETH_MIN            = (ETH_LEN_MIN - ETH_HDR_LEN - ETH_CRC_LEN)

# Ethernet payload types - http://standards.ieee.org/regauth/ethertype
ETH_PR_PUP         = 0x0200    # PUP protocol
ETH_PR_IP          = 0x0800    # IP protocol
ETH_PR_ARP         = 0x0806    # address resolution protocol
ETH_PR_CDP         = 0x2000    # Cisco Discovery Protocol
ETH_PR_DTP         = 0x2004    # Cisco Dynamic Trunking Protocol
ETH_PR_REVARP      = 0x8035    # reverse addr resolution protocol
ETH_PR_8021Q       = 0x8100    # IEEE 802.1Q VLAN tagging
ETH_PR_IPX         = 0x8137    # Internetwork Packet Exchange
ETH_PR_IP6         = 0x86DD    # IPv6 protocol
ETH_PR_PPP         = 0x880B    # PPP
ETH_PR_MPLS        = 0x8847    # MPLS
ETH_PR_MPLS_MCAST  = 0x8848    # MPLS Multicast
ETH_PR_PPPoE_DISC  = 0x8863    # PPP Over Ethernet Discovery Stage
ETH_PR_PPPoE       = 0x8864    # PPP Over Ethernet Session Stage

# Header Structure and Dictionary
ETH_HDR =                       \
{                               \
'hdrType'     : 'ETH',          \
'hdrStruct'   : '!6s6sH',       \
'ethDst'      : None,           \
'ethSrc'      : None,           \
'ethPayType'  : ETH_PR_IP,      \
}                               \


#####
#ARP#
#####

# Costant
ARP_HDR_LEN = 28

ARP_HW_ETH_LEN     = 6
ARP_PR_IP_LEN      = 4 

# Hardware address format
ARP_HW_ETH         = 0x0001  # ethernet hardware
ARP_HW_IEEE802     = 0x0006  # IEEE 802 hardware

# Protocol address format
ARP_PR_IP          = 0x0800  # IP protocol

# ARP operation
ARP_OP_REQUEST     = 1       # request to resolve ha given pa
ARP_OP_REPLY       = 2       # response giving hardware address
ARP_OP_REVREQUEST  = 3       # request to resolve pa given ha
ARP_OP_REVREPLY    = 4       # response giving protocol address

# Header Structure and Dictionary
ARP_HDR =                         \
{                                 \
'hdrType'    : 'ARP',             \
'hdrStruct'  : '!HHBBH6s4s6s4s',  \
'arpHwAT'    : ARP_HW_ETH,        \
'arpPrAT'    : ARP_PR_IP,         \
'arpHwAL'    : ARP_HW_ETH_LEN,    \
'arpPrAL'    : ARP_PR_IP_LEN,     \
'arpOpCode'  : 0,                 \
'arpHwSrc'   : None,              \
'arpPrSrc'   : None,              \
'arpHwDst'   : None,              \
'arpPrDst'   : None,              \
}                                 \


#############
#IPv4 / IPv6#
#############

# Costant 
IPv4_HDR_LEN        = 20
IPv6_HDR_LEN        = 40

IPv4_VER            = 4
IPv6_VER            = 6

IP_TTL_MIN          = 64            # default ttl, RFC 1122, RFC 1340
IP_TTL_MAX          = 255           # maximum ttl

# Fragmentation Offset Flags
IPv4_RF             = 0x8000        # reserved
IPv4_DF             = 0x4000        # don't fragment
IPv4_MF             = 0x2000        # more fragments (not last frag)
IPv4_OFFMASK        = 0x1fff        # mask for fragment offset

# IP payload types - http://www.iana.org/assignments/protocol-numbers
IP_PR_IP            = 0            # dummy for IP
IP_PR_HOPOPTS       = IP_PR_IP     # IPv6 hop-by-hop options
IP_PR_ICMP          = 1            # ICMP
IP_PR_IGMP          = 2            # IGMP
IP_PR_GGP           = 3            # gateway-gateway protocol
IP_PR_IPIP          = 4            # IP in IP
IP_PR_ST            = 5            # ST datagram mode
IP_PR_TCP           = 6            # TCP
IP_PR_CBT           = 7            # CBT
IP_PR_EGP           = 8            # exterior gateway protocol
IP_PR_IGP           = 9            # interior gateway protocol
IP_PR_BBNRCC        = 10           # BBN RCC monitoring
IP_PR_NVP           = 11           # Network Voice Protocol
IP_PR_PUP           = 12           # PARC universal packet
IP_PR_ARGUS         = 13           # ARGUS
IP_PR_EMCON         = 14           # EMCON
IP_PR_XNET          = 15           # Cross Net Debugger
IP_PR_CHAOS         = 16           # Chaos
IP_PR_UDP           = 17           # UDP
IP_PR_MUX           = 18           # multiplexing
IP_PR_DCNMEAS       = 19           # DCN measurement
IP_PR_HMP           = 20           # Host Monitoring Protocol
IP_PR_PRM           = 21           # Packet Radio Measurement
IP_PR_IDP           = 22           # Xerox NS IDP
IP_PR_TRUNK1        = 23           # Trunk-1
IP_PR_TRUNK2        = 24           # Trunk-2
IP_PR_LEAF1         = 25           # Leaf-1
IP_PR_LEAF2         = 26           # Leaf-2
IP_PR_RDP           = 27           # "Reliable Datagram" proto
IP_PR_IRTP          = 28           # Inet Reliable Transaction
IP_PR_TP            = 29           # ISO TP class 4
IP_PR_NETBLT        = 30           # Bulk Data Transfer
IP_PR_MFPNSP        = 31           # MFE Network Services
IP_PR_MERITINP      = 32           # Merit Internodal Protocol
IP_PR_SEP           = 33           # Sequential Exchange proto
IP_PR_3PC           = 34           # Third Party Connect proto
IP_PR_IDPR          = 35           # Interdomain Policy Route
IP_PR_XTP           = 36           # Xpress Transfer Protocol
IP_PR_DDP           = 37           # Datagram Delivery Proto
IP_PR_CMTP          = 38           # IDPR Ctrl Message Trans
IP_PR_TPPP          = 39           # TP++ Transport Protocol
IP_PR_IL            = 40           # IL Transport Protocol
IP_PR_IP6           = 41           # IPv6
IP_PR_SDRP          = 42           # Source Demand Routing
IP_PR_ROUTING       = 43           # IPv6 routing header
IP_PR_FRAGMENT      = 44           # IPv6 fragmentation header
IP_PR_RSVP          = 46           # Reservation protocol
IP_PR_GRE           = 47           # General Routing Encap
IP_PR_MHRP          = 48           # Mobile Host Routing
IP_PR_ENA           = 49           # ENA
IP_PR_ESP           = 50           # Encap Security Payload
IP_PR_AH            = 51           # Authentication Header
IP_PR_INLSP         = 52           # Integated Net Layer Sec
IP_PR_SWIPE         = 53           # SWIPE
IP_PR_NARP          = 54           # NBMA Address Resolution
IP_PR_MOBILE        = 55           # Mobile IP, RFC 2004
IP_PR_TLSP          = 56           # Transport Layer Security
IP_PR_SKIP          = 57           # SKIP
IP_PR_ICMP6         = 58           # ICMP for IPv6
IP_PR_NONE          = 59           # IPv6 no next header
IP_PR_DSTOPTS       = 60           # IPv6 destination options
IP_PR_ANYHOST       = 61           # any host internal proto
IP_PR_CFTP          = 62           # CFTP
IP_PR_ANYNET        = 63           # any local network
IP_PR_EXPAK         = 64           # SATNET and Backroom EXPAK
IP_PR_KRYPTOLAN     = 65           # Kryptolan
IP_PR_RVD           = 66           # MIT Remote Virtual Disk
IP_PR_IPPC          = 67           # Inet Pluribus Packet Core
IP_PR_DISTFS        = 68           # any distributed fs
IP_PR_SATMON        = 69           # SATNET Monitoring
IP_PR_VISA          = 70           # VISA Protocol
IP_PR_IPCV          = 71           # Inet Packet Core Utility
IP_PR_CPNX          = 72           # Comp Proto Net Executive
IP_PR_CPHB          = 73           # Comp Protocol Heart Beat
IP_PR_WSN           = 74           # Wang Span Network
IP_PR_PVP           = 75           # Packet Video Protocol
IP_PR_BRSATMON      = 76           # Backroom SATNET Monitor
IP_PR_SUNND         = 77           # SUN ND Protocol
IP_PR_WBMON         = 78           # WIDEBAND Monitoring
IP_PR_WBEXPAK       = 79           # WIDEBAND EXPAK
IP_PR_EON           = 80           # ISO CNLP
IP_PR_VMTP          = 81           # Versatile Msg Transport
IP_PR_SVMTP         = 82           # Secure VMTP
IP_PR_VINES         = 83           # VINES
IP_PR_TTP           = 84           # TTP
IP_PR_NSFIGP        = 85           # NSFNET-IGP
IP_PR_DGP           = 86           # Dissimilar Gateway Proto
IP_PR_TCF           = 87           # TCF
IP_PR_EIGRP         = 88           # EIGRP
IP_PR_OSPF          = 89           # Open Shortest Path First
IP_PR_SPRITERPC     = 90           # Sprite RPC Protocol
IP_PR_LARP          = 91           # Locus Address Resolution
IP_PR_MTP           = 92           # Multicast Transport Proto
IP_PR_AX25          = 93           # AX.25 Frames
IP_PR_IPIPENCAP     = 94           # yet-another IP encap
IP_PR_MICP          = 95           # Mobile Internet Ctrl
IP_PR_SCCSP         = 96           # Semaphore Comm Sec Proto
IP_PR_ETHERIP       = 97           # Ethernet in IPv4
IP_PR_ENCAP         = 98           # encapsulation header
IP_PR_ANYENC        = 99           # private encryption scheme
IP_PR_GMTP          = 100          # GMTP
IP_PR_IFMP          = 101          # Ipsilon Flow Mgmt Proto
IP_PR_PNNI          = 102          # PNNI over IP
IP_PR_PIM           = 103          # Protocol Indep Multicast
IP_PR_ARIS          = 104          # ARIS
IP_PR_SCPS          = 105          # SCPS
IP_PR_QNX           = 106          # QNX
IP_PR_AN            = 107          # Active Networks
IP_PR_IPCOMP        = 108          # IP Payload Compression
IP_PR_SNP           = 109          # Sitara Networks Protocol
IP_PR_COMPAQPEER    = 110          # Compaq Peer Protocol
IP_PR_IPXIP         = 111          # IPX in IP
IP_PR_VRRP          = 112          # Virtual Router Redundancy
IP_PR_PGM           = 113          # PGM Reliable Transport
IP_PR_ANY0HOP       = 114          # 0-hop protocol
IP_PR_L2TP          = 115          # Layer 2 Tunneling Proto
IP_PR_DDX           = 116          # D-II Data Exchange (DDX)
IP_PR_IATP          = 117          # Interactive Agent Xfer
IP_PR_STP           = 118          # Schedule Transfer Proto
IP_PR_SRP           = 119          # SpectraLink Radio Proto
IP_PR_UTI           = 120          # UTI
IP_PR_SMP           = 121          # Simple Message Protocol
IP_PR_SM            = 122          # SM
IP_PR_PTP           = 123          # Performance Transparency
IP_PR_ISIS          = 124          # ISIS over IPv4
IP_PR_FIRE          = 125          # FIRE
IP_PR_CRTP          = 126          # Combat Radio Transport
IP_PR_CRUDP         = 127          # Combat Radio UDP
IP_PR_SSCOPMCE      = 128          # SSCOPMCE
IP_PR_IPLT          = 129          # IPLT
IP_PR_SPS           = 130          # Secure Packet Shield
IP_PR_PIPE          = 131          # Private IP Encap in IP
IP_PR_SCTP          = 132          # Stream Ctrl Transmission
IP_PR_FC            = 133          # Fibre Channel
IP_PR_RSVPIGN       = 134          # RSVP-E2E-IGNORE
IP_PR_RAW           = 255          # Raw IP packets
IP_PR_RESERVED      = IP_PR_RAW    # Reserved
IP_PR_MAX           = 255

# IPv4 Header Structure and Dictionary
IPv4_HDR =                           \
{                                    \
'hdrType'     : 'IPv4',              \
'hdrStruct'   : '!BBHHHBBH4s4s',     \
'ipVer'       : IPv4_VER,            \
'ipHdrLen'    : IPv4_HDR_LEN,        \
'ipToS'       : None,                \
'ipTotLen'    : IPv4_HDR_LEN,        \
'ipId'        : 0,                   \
'ipOffset'    : None,                \
'ipTtl'       : IP_TTL_MIN,          \
'ipPayType'   : 0,                   \
'ipCheckSum'  : None,                \
'ipSrc'       : None,                \
'ipDst'       : None,                \
'ipOptions'   : None,                \
}                                    \

# IPv6 Header Structure and Dictionary
IPv6_HDR =                           \
{                                    \
'hdrType'     : 'IPv6',              \
'hdrStruct'   : '!IHBB16s16s',       \
'ipVer'        : IPv6_VER,           \
'ipTrClass'    : None,               \
'ipFlowLabel'  : None,               \
'ipPayLen'     : 0,                  \
'ipPayType'    : 0,                  \
'ipTtl'        : IP_TTL_MIN,         \
'ipSrc'        : None,               \
'ipDst'        : None,               \
}                                    \


#####
#TCP#
#####

# Costant
TCP_HDR_LEN         = 20

TCP_PORT_MAX        = 65535    # maximum port
TCP_WIN_MAX         = 65535    # maximum (unscaled) window

# TCP control flags
TCP_FIN             = 0x01     # end of data
TCP_SYN             = 0x02     # synchronize sequence numbers
TCP_RST             = 0x04     # reset connection
TCP_PSH             = 0x08     # push
TCP_ACK             = 0x10     # acknowledgment number set
TCP_URG             = 0x20     # urgent pointer set
TCP_ECE             = 0x40     # ECN echo, RFC 3168
TCP_CWR             = 0x80     # congestion window reduced

# Options - http://www.iana.org/assignments/tcp-parameters
TCP_OPT_EOL         = 0        # end of option list
TCP_OPT_NOP         = 1        # no operation
TCP_OPT_MSS         = 2        # maximum segment size
TCP_OPT_WSCALE      = 3        # window scale factor, RFC 1072
TCP_OPT_SACKOK      = 4        # SACK permitted, RFC 2018
TCP_OPT_SACK        = 5        # SACK, RFC 2018
TCP_OPT_ECHO        = 6        # echo (obsolete), RFC 1072
TCP_OPT_ECHOREPLY   = 7        # echo reply (obsolete), RFC 1072
TCP_OPT_TIMESTAMP   = 8        # timestamp, RFC 1323
TCP_OPT_POCONN      = 9        # partial order conn, RFC 1693
TCP_OPT_POSVC       = 10       # partial order service, RFC 1693
TCP_OPT_CC          = 11       # connection count, RFC 1644
TCP_OPT_CCNEW       = 12       # CC.NEW, RFC 1644
TCP_OPT_CCECHO      = 13       # CC.ECHO, RFC 1644
TCP_OPT_ALTSUM      = 14       # alt checksum request, RFC 1146
TCP_OPT_ALTSUMDATA  = 15       # alt checksum data, RFC 1146
TCP_OPT_SKEETER     = 16       # Skeeter
TCP_OPT_BUBBA       = 17       # Bubba
TCP_OPT_TRAILSUM    = 18       # trailer checksum
TCP_OPT_MD5         = 19       # MD5 signature, RFC 2385
TCP_OPT_SCPS        = 20       # SCPS capabilities
TCP_OPT_SNACK       = 21       # selective negative acks
TCP_OPT_REC         = 22       # record boundaries
TCP_OPT_CORRUPT     = 23       # corruption experienced
TCP_OPT_SNAP        = 24       # SNAP
TCP_OPT_TCPCOMP     = 26       # TCP compression filter
TCP_OPT_MAX         = 27

# Header Structure and Dictionary
TCP_HDR =                       \
{                               \
'hdrType'     : 'TCP',          \
'hdrStruct'   : '!HHIIBBHHH',   \
'tcpSrcPort'   : 0,             \
'tcpDstPort'   : 0,             \
'tcpSeqNum'    : 0,             \
'tcpAckNum'    : 0,             \
'tcpHdrLen'    : TCP_HDR_LEN,   \
'tcpFin'       : 0,             \
'tcpSyn'       : 0,             \
'tcpRst'       : 0,             \
'tcpPsh'       : 0,             \
'tcpAck'       : 0,             \
'tcpUrg'       : 0,             \
'tcpEce'       : 0,             \
'tcpCwr'       : 0,             \
'tcpWin'       : None,          \
'tcpCheckSum'  : None,          \
'tcpUrgent'    : None,          \
'tcpOptions'   : None,          \
}                               \


#####
#UDP#
#####

# Costant
UDP_HDR_LEN     = 8

UDP_PORT_MAX    = 65535        # maximum port

# Header Structure and Dictionary
UDP_HDR =                       \
{                               \
'hdrType'     : 'UDP',          \
'hdrStruct'   : '!HHHH',        \
'udpSrcPort'   : 0,             \
'udpDstPort'   : 0,             \
'udpTotLen'    : UDP_HDR_LEN,   \
'udpCheckSum'  : None,          \
}                               \


############
#STATISTICS#
############
STATISTICS =              \
{                         \
'packet_up_nem'     : 0,  \
'packet_up_oth'     : 0,  \
'packet_up_all'     : 0,  \
'packet_down_nem'   : 0,  \
'packet_down_oth'   : 0,  \
'packet_down_all'   : 0,  \
'packet_tot_nem'    : 0,  \
'packet_tot_oth'    : 0,  \
'packet_tot_all'    : 0,  \
'byte_up_nem'       : 0,  \
'byte_up_oth'       : 0,  \
'byte_up_all'       : 0,  \
'byte_down_nem'     : 0,  \
'byte_down_oth'     : 0,  \
'byte_down_all'     : 0,  \
'byte_tot_nem'      : 0,  \
'byte_tot_oth'      : 0,  \
'byte_tot_all'      : 0,  \
'payload_up_nem'    : 0,  \
'payload_up_oth'    : 0,  \
'payload_up_all'    : 0,  \
'payload_down_nem'  : 0,  \
'payload_down_oth'  : 0,  \
'payload_down_all'  : 0,  \
'payload_tot_nem'   : 0,  \
'payload_tot_oth'   : 0,  \
'payload_tot_all'   : 0,  \
}                         \

def _pcap_hdr_unpack(pcapHdrPkt):
  
  pcapHdr = PCAP_HDR
  
  if (len(pcapHdrPkt) >= PCAP_HDR_LEN):
    
    pcap01, pcap02, pcap03, pcap04 = struct.unpack(pcapHdr['hdrStruct'],pcapHdrPkt[:len(pcapHdrPkt)])
    
    #pcapTimeStamp = float(pcap01) + (float(pcap02)/1000000)
    
    pcapHdr['tsSec']      = pcap01
    pcapHdr['tsUsec']     = pcap02
    pcapHdr['pktCaplen']  = pcap03
    pcapHdr['pktLen']     = pcap04
        
  else:
    raise Exception ("Contabyte Error: Pcap Hdr too small")
    
  return (pcapHdr)


def _display_mac(value):
    return string.join(["%02X" % ord(b) for b in value], ':')


def _eth_unpack(ethPkt):
  
  ethHdr = ETH_HDR
  
  if (len(ethPkt) >= ETH_HDR_LEN):
    
    eth01, eth02, eth03 = struct.unpack(ethHdr['hdrStruct'],ethPkt[:ETH_HDR_LEN])

    ethHdr['ethDst']      = _display_mac(eth01)
    ethHdr['ethSrc']      = _display_mac(eth02)
    ethHdr['ethPayType']  = eth03
    
    ethData = ethPkt[ETH_HDR_LEN:]
    
  else:
    raise Exception ("Contabyte Error: Eth Pkt too small")
    
  return (ethHdr,ethData)


def _arp_unpack(arpPkt):
  
  arpHdr = ARP_HDR
  
  if (len(arpPkt) >= ARP_HDR_LEN):
    
    arp01, arp02, arp03, arp04, arp05, arp06, arp07, arp08, arp09 = struct.unpack(arpHdr['hdrStruct'],arpPkt[:ARP_HDR_LEN])
    
    arpHdr['arpHwAT']    = arp01 
    arpHdr['arpPrAT']    = arp02
    arpHdr['arpHwAL']    = arp03
    arpHdr['arpPrAL']    = arp04
    arpHdr['arpOpCode']  = arp05
    arpHdr['arpHwSrc']   = _display_mac(arp06)
    arpHdr['arpPrSrc']   = socket.inet_ntop(socket.AF_INET,arp07)
    arpHdr['arpHwDst']   = _display_mac(arp08)
    arpHdr['arpPrDst']   = socket.inet_ntop(socket.AF_INET,arp09)
    
    arpData = arpPkt[ARP_HDR_LEN:]
    
  else:
    raise Exception ("Contabyte Error: Arp Pkt too small")
    
  return (arpHdr,arpData)


def _ipv4_unpack(ipv4Pkt):
  
  ipv4Hdr = IPv4_HDR
  
  if (len(ipv4Pkt) >= IPv4_HDR_LEN):
    
    ip01, ip02, ip03, ip04, ip05, ip06, ip07, ip08, ip09, ip10 = struct.unpack(ipv4Hdr['hdrStruct'],ipv4Pkt[:IPv4_HDR_LEN])
    
    ipVer     = ((ip01 & 0xf0) >> 4)
    ipHdrLen  = ((ip01 & 0x0f) << 2)
    
    ipv4Hdr['ipVer']       = ipVer
    ipv4Hdr['ipHdrLen']    = ipHdrLen
    ipv4Hdr['ipToS']       = ip02
    ipv4Hdr['ipTotLen']    = ip03
    ipv4Hdr['ipId']        = ip04
    ipv4Hdr['ipOffset']    = ip05
    ipv4Hdr['ipTtl']       = ip06
    ipv4Hdr['ipPayType']   = ip07
    ipv4Hdr['ipCheckSum']  = ip08
    ipv4Hdr['ipSrc']       = socket.inet_ntop(socket.AF_INET,ip09)
    ipv4Hdr['ipDst']       = socket.inet_ntop(socket.AF_INET,ip10)
    
#    if (ipHdrLen > IPv4_HDR_LEN):
#      ipv4Hdr['ipOptions'] = str(ipv4Pkt[IPv4_HDR_LEN:ipHdrLen])
    
    ipv4Data = ipv4Pkt[ipHdrLen:]
    
  else:
    raise Exception ("Contabyte Error: Ipv4 Pkt too small")
    
  return (ipv4Hdr,ipv4Data)


def _ipv6_unpack(ipv6Pkt):
  
  ipv6Hdr = IPv6_HDR
  
  if (len(ipv6Pkt) >= IPv6_HDR_LEN):
    
    ip01, ip02, ip03, ip04, ip05, ip06 = struct.unpack(ipv6Hdr['hdrStruct'],ipv6Pkt[:IPv6_HDR_LEN])
    
    ipv6Hdr['ipVer']        = ((ip01 & 0xf0000000) >> 28)
    ipv6Hdr['ipTrClass']    = ((ip01 & 0x0ff00000) >> 20)
    ipv6Hdr['ipFlowLabel']  = ((ip01 & 0x000fffff)      )
    ipv6Hdr['ipPayLen']     = ip02
    ipv6Hdr['ipPayType']    = ip03
    ipv6Hdr['ipTtl']        = ip04
    ipv6Hdr['ipSrc']        = socket.inet_ntop(socket.AF_INET6,ip05)
    ipv6Hdr['ipDst']        = socket.inet_ntop(socket.AF_INET6,ip06)
    
    ipv6Data = ipv6Pkt[IPv6_HDR_LEN:]
    
  else:
    raise Exception ("Contabyte Error: Ipv6 Pkt too small")
    
  return (ipv6Hdr,ipv6Data)


def _tcp_unpack(tcpPkt):
  
  tcpHdr = TCP_HDR
  
  if (len(tcpPkt) >= TCP_HDR_LEN):
    
    tcp01, tcp02, tcp03, tcp04, tcp05, tcp06, tcp07, tcp08, tcp09 = struct.unpack(tcpHdr['hdrStruct'],tcpPkt[:TCP_HDR_LEN])
    
    tcpHdrLen = ((tcp05 & 0xf0) >> 2)
    tcpFin    = ((tcp06 & TCP_FIN)     )
    tcpSyn    = ((tcp06 & TCP_SYN) >> 1)
    tcpRst    = ((tcp06 & TCP_RST) >> 2)
    tcpPsh    = ((tcp06 & TCP_PSH) >> 3)
    tcpAck    = ((tcp06 & TCP_ACK) >> 4)
    tcpUrg    = ((tcp06 & TCP_URG) >> 5)
    tcpEce    = ((tcp06 & TCP_ECE) >> 6)
    tcpCwr    = ((tcp06 & TCP_CWR) >> 7)
    
    tcpHdr['tcpSrcPort']   = tcp01
    tcpHdr['tcpDstPort']   = tcp02
    tcpHdr['tcpSeqNum']    = tcp03
    tcpHdr['tcpAckNum']    = tcp04
    tcpHdr['tcpHdrLen']    = tcpHdrLen
    tcpHdr['tcpFin']       = tcpFin
    tcpHdr['tcpSyn']       = tcpSyn
    tcpHdr['tcpRst']       = tcpRst
    tcpHdr['tcpPsh']       = tcpPsh
    tcpHdr['tcpAck']       = tcpAck
    tcpHdr['tcpUrg']       = tcpUrg
    tcpHdr['tcpEce']       = tcpEce
    tcpHdr['tcpCwr']       = tcpCwr
    tcpHdr['tcpWin']       = tcp07
    tcpHdr['tcpCheckSum']  = tcp08
    tcpHdr['tcpUrgent']    = tcp09

#    if (tcpHdrLen > TCP_HDR_LEN):
#      tcpHdr['tcpOptions'] = str(tcpPkt[TCP_HDR_LEN:tcpHdrLen])
    
    tcpData = tcpPkt[tcpHdrLen:]
    
  else:
    raise Exception ("Contabyte Error: Tcp Pkt too small")
    
  return (tcpHdr,tcpData)


def _udp_unpack(udpPkt):
  
  udpHdr = UDP_HDR
  
  if (len(udpPkt) >= UDP_HDR_LEN):
    
    udp01, udp02, udp03, udp04 = struct.unpack(udpHdr['hdrStruct'],udpPkt[:UDP_HDR_LEN])
        
    udpHdr['udpSrcPort']   = udp01
    udpHdr['udpDstPort']   = udp02
    udpHdr['udpTotLen']    = udp03
    udpHdr['udpCheckSum']  = udp04
    
    udpData = udpPkt[UDP_HDR_LEN:]
    
  else:
    raise Exception ("Contabyte Error: Udp Pkt too small")
    
  return (udpHdr,udpData)

def reset():
  
  global STATISTICS
  
  STATISTICS =              \
  {                         \
  'packet_up_nem'     : 0,  \
  'packet_up_oth'     : 0,  \
  'packet_up_all'     : 0,  \
  'packet_down_nem'   : 0,  \
  'packet_down_oth'   : 0,  \
  'packet_down_all'   : 0,  \
  'packet_tot_nem'    : 0,  \
  'packet_tot_oth'    : 0,  \
  'packet_tot_all'    : 0,  \
  'byte_up_nem'       : 0,  \
  'byte_up_oth'       : 0,  \
  'byte_up_all'       : 0,  \
  'byte_down_nem'     : 0,  \
  'byte_down_oth'     : 0,  \
  'byte_down_all'     : 0,  \
  'byte_tot_nem'      : 0,  \
  'byte_tot_oth'      : 0,  \
  'byte_tot_all'      : 0,  \
  'payload_up_nem'    : 0,  \
  'payload_up_oth'    : 0,  \
  'payload_up_all'    : 0,  \
  'payload_down_nem'  : 0,  \
  'payload_down_oth'  : 0,  \
  'payload_down_all'  : 0,  \
  'payload_tot_nem'   : 0,  \
  'payload_tot_oth'   : 0,  \
  'payload_tot_all'   : 0,  \
  }                         \
  
#  if (STATISTICS != None):
#    keys = STATISTICS.keys()
#    keys.sort()
#    for key in keys:
#      STATISTICS[key] = 0
  
  return None

def analyze(ipDev, ipNem, pcapHdrPkt, pcapDataPkt):
  
  global STATISTICS
  
  statistics = STATISTICS
  
  tcpHdrLen = 0
  udpHdrLen = 0
  PayloadLen = 0
  
  ipSrc = None
  ipDst = None
  
  eth_switch =                 \
  {                            \
   ETH_PR_ARP : _arp_unpack,   \
   ETH_PR_IP  : _ipv4_unpack,  \
   ETH_PR_IP6 : _ipv6_unpack,  \
  }                            \
  
  ip_switch =                \
  {                          \
   IP_PR_TCP : _tcp_unpack,  \
   IP_PR_UDP : _udp_unpack,  \
  }                          \
  
#  #LOGGER#
#  logger.debug("  ")
#  logger.debug("="*88 + " [PACKET N°:%d]" % (STATISTICS['packet_tot_all']+1))
#  ########
  
  pcapHdr = _pcap_hdr_unpack(pcapHdrPkt)
  
#  #LOGGER#
#  logger.debug("|%s|" % pcapHdr['hdrType'])
#  keys = pcapHdr.keys()
#  keys.sort()
#  for key in keys:
#    logger.debug("%s:\t%s" % (key,pcapHdr[key]))
#  logger.debug("-"*88)
#  ########
#  
  (l2_hdr,l2_data) = _eth_unpack(pcapDataPkt)
   
#  #LOGGER#  
#  logger.debug("|%s|" % l2_hdr['hdrType'])
#  keys = l2_hdr.keys()
#  keys.sort()
#  for key in keys:
#    logger.debug("%s:\t%s" % (key,l2_hdr[key]))
#  logger.debug("-"*88)
#  ########
  
  if (l2_hdr['ethPayType'] in eth_switch):
  
    (l3_hdr,l3_data) = eth_switch[l2_hdr['ethPayType']](l2_data)
    
#    #LOGGER#
#    logger.debug("|%s|" % l3_hdr['hdrType'])
#    keys = l3_hdr.keys()
#    keys.sort()
#    for key in keys:
#      logger.debug("%s:\t%s" % (key,l3_hdr[key]))
#    logger.debug("-"*88)
#    ########
    
    if (l2_hdr['ethPayType'] == ETH_PR_ARP):
      
      ipSrc = l3_hdr['arpPrSrc']
      ipDst = l3_hdr['arpPrDst']
    
    elif (l2_hdr['ethPayType'] == ETH_PR_IP or l2_hdr['ethPayType'] == ETH_PR_IP6):
            
      if ('ipPayLen' in l3_hdr):
        
        ipPayLen = l3_hdr['ipPayLen']
          
      else:
        
        ipPayLen = (l3_hdr['ipTotLen']) - (l3_hdr['ipHdrLen'])
        
        ipSrc = l3_hdr['ipSrc']
        ipDst = l3_hdr['ipDst']
        
        
      if (l3_hdr['ipPayType'] in ip_switch):
      
        (l4_hdr,l4_data) = ip_switch[l3_hdr['ipPayType']](l3_data)
        
#        #LOGGER#
#        logger.debug("|%s|" % l4_hdr['hdrType'])
#        keys = l4_hdr.keys()
#        keys.sort()
#        for key in keys:
#          logger.debug("%s:\t%s" % (key,l4_hdr[key]))
#        logger.debug("-"*88)
#        ########  
          
        if ('tcpHdrLen' in l4_hdr):
          tcpHdrLen = l4_hdr['tcpHdrLen']
          
#          if(l4_hdr['tcpSyn'] == 1):
#            logger.debug("|SYN| SEQ:%i\tACK:%i" % (l4_hdr['tcpSeqNum'],l4_hdr['tcpAckNum']))
          
        elif ('udpTotLen' in l4_hdr):
          udpHdrLen = UDP_HDR_LEN
                
        PayloadLen = ipPayLen - tcpHdrLen - udpHdrLen
        
  
  if (ipSrc != ipDev):
    
    statistics['packet_down_all']   += 1
    statistics['packet_tot_all']    += 1

    statistics['byte_down_all']     += (pcapHdr['pktLen'] + ETH_CRC_LEN)
    statistics['byte_tot_all']      += (pcapHdr['pktLen'] + ETH_CRC_LEN)

    statistics['payload_down_all']  += PayloadLen
    statistics['payload_tot_all']   += PayloadLen

    if ((ipSrc == ipNem) and (ipDst == ipDev)):
        
      statistics['packet_down_nem']   += 1
      statistics['packet_tot_nem']    += 1
  
      statistics['byte_down_nem']     += (pcapHdr['pktLen'] + ETH_CRC_LEN)
      statistics['byte_tot_nem']      += (pcapHdr['pktLen'] + ETH_CRC_LEN)
  
      statistics['payload_down_nem']  += PayloadLen
      statistics['payload_tot_nem']   += PayloadLen

    else:
      
      statistics['packet_down_oth']   += 1
      statistics['packet_tot_oth']    += 1
  
      statistics['byte_down_oth']     += (pcapHdr['pktLen'] + ETH_CRC_LEN)
      statistics['byte_tot_oth']      += (pcapHdr['pktLen'] + ETH_CRC_LEN)
  
      statistics['payload_down_oth']  += PayloadLen
      statistics['payload_tot_oth']   += PayloadLen

  else:

    pktPad = (ETH_LEN_MIN - pcapHdr['pktLen'] - ETH_CRC_LEN)
      
    if (pktPad < 0):
      pktPad = 0

    statistics['packet_up_all']    += 1
    statistics['packet_tot_all']   += 1

    statistics['byte_up_all']      += (pcapHdr['pktLen'] + pktPad + ETH_CRC_LEN)
    statistics['byte_tot_all']     += (pcapHdr['pktLen'] + pktPad + ETH_CRC_LEN)

    statistics['payload_up_all']   += PayloadLen
    statistics['payload_tot_all']  += PayloadLen

    if ((ipSrc == ipDev) and (ipDst == ipNem)):
        
      statistics['packet_up_nem']    += 1
      statistics['packet_tot_nem']   += 1
  
      statistics['byte_up_nem']      += (pcapHdr['pktLen'] + pktPad + ETH_CRC_LEN)
      statistics['byte_tot_nem']     += (pcapHdr['pktLen'] + pktPad + ETH_CRC_LEN)
  
      statistics['payload_up_nem']   += PayloadLen
      statistics['payload_tot_nem']  += PayloadLen

    else:
      
      statistics['packet_up_oth']    += 1
      statistics['packet_tot_oth']   += 1
  
      statistics['byte_up_oth']      += (pcapHdr['pktLen'] + pktPad + ETH_CRC_LEN)
      statistics['byte_tot_oth']     += (pcapHdr['pktLen'] + pktPad + ETH_CRC_LEN)
  
      statistics['payload_up_oth']   += PayloadLen
      statistics['payload_tot_oth']  += PayloadLen
  
  
  STATISTICS = statistics
  
  return STATISTICS

