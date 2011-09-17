//
//Linux: gcc sniffer.c -shared -I./ -I/usr/include/python2.7 -lpython2.7 -lpcap -osniffer.so
//
//Win: gcc sniffer.c -shared -I. -I C:\Python27\include -I C:\winpcap\Include -I C:\winpcap\Include\pcap -L C:\Programmi\CodeBlocks\MinGW\lib -L C:\Python27\libs -L C:\winpcap\Lib -o sniffer.pyd -lpython27 -lwpcap -lwsock32
//
// gcc -fPIC                        [per 64bit .so .pyd]
// gcc -fno-stack-protector         [disabilitare la protezione di overflow]


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
