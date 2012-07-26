/* -------------------------------- */
/* | PKTMAN by Domenico Izzo 2012 | */
/* |  c/o Fondazione Ugo Bordoni  | */
/* -------------------------------- */

#include <Python.h>

#include <conio.h>			/* serve per getch() */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <math.h>

#include <winsock2.h>
#include <iphlpapi.h>
#include <ntddndis.h>
#include <NMApi.h>
#include <windows.h>

/* Link with LIB */
#pragma comment(lib, "IPHLPAPI.lib")
#pragma comment(lib, "Ws2_32.lib")
//#pragma comment(lib, "NmApi.lib")
//#pragma comment(lib, "Python27.lib")

#define MALLOC(x) HeapAlloc(GetProcessHeap(), 0, (x))
#define FREE(x) HeapFree(GetProcessHeap(), 0, (x))

char *MediumName[] =
{
	"NdisMedium802_3",
	"NdisMedium802_5",
	"NdisMediumFddi",
	"NdisMediumWan",
	"NdisMediumLocalTalk",
	"NdisMediumDix",
	"NdisMediumArcnetRaw",
	"NdisMediumArcnet878_2",
	"NdisMediumAtm",
	"NdisMediumWirelessWan",
	"NdisMediumIrda",
	"NdisMediumBpc",
	"NdisMediumCoWan",
	"NdisMedium1394",
	"NdisMediumInfiniBand",
	#if ((NTDDI_VERSION >= NTDDI_VISTA) || NDIS_SUPPORT_NDIS6)
		"NdisMediumTunnel",
		"NdisMediumNative802_11",
		"NdisMediumLoopback",
		#if (NTDDI_VERSION >= NTDDI_WIN7)
			"NdisMediumWiMAX",
			"NdisMediumIP",
		#endif 
	#endif 
	"NdisMediumMax" 
};

char *PhysicalMediumName[] = 
{
	"NdisPhysicalMediumUnspecified",
	"NdisPhysicalMediumWirelessLan",
	"NdisPhysicalMediumCableModem",
	"NdisPhysicalMediumPhoneLine",
	"NdisPhysicalMediumPowerLine",
	"NdisPhysicalMediumDSL",			/* includes ADSL and UADSL (G.Lite) */
	"NdisPhysicalMediumFibreChannel",
	"NdisPhysicalMedium1394",
	"NdisPhysicalMediumWirelessWan",
	"NdisPhysicalMediumNative802_11",
	"NdisPhysicalMediumBluetooth",
	"NdisPhysicalMediumInfiniband",
	"NdisPhysicalMediumWiMax",
	"NdisPhysicalMediumUWB",
	"NdisPhysicalMedium802_3",
	"NdisPhysicalMedium802_5",
	"NdisPhysicalMediumIrda",
	"NdisPhysicalMediumWiredWAN",
	"NdisPhysicalMediumWiredCoWan",
	"NdisPhysicalMediumOther",
};

struct device
{
	int		index;
	int		type;
	char	*description;
    char	*name;
	char	*mac;
    char	*ip;
    char	*net;
    char	*mask;
};

struct packet_header
{
	ULONG	sec;
	ULONG	usec;
	UINT	caplen;
	UINT	len;
};

struct packet_unit
{
	packet_header*	header;
	char*			data;
};

char *sniff_error[] = 
{
	"Timeout was reached during packet receive",
	"One packet pulled",
	"Packet out of range",
};

struct statistics
{
    ULONG	last_read;
	ULONG   last_write;
    ULONG	pkt_tot;
    ULONG	pkt_drop;
    ULONG	pkt_dropHandle;
	ULONG	pkt_filtered;
	ULONG	write_dropped;
};

UINT DEBUG_MODE=0;
FILE *debug_log = NULL;

char *dump_file;

int err_flag=0;
char err_str[88]="No Error";

PyGILState_STATE gil_state;
PyObject *py_pkt_header, *py_pkt_data;

time_t sniff_start = 0, sniff_stop = 0;

int sniff_mode=0, online=1;

UINT data_link=0, timeout = 1;

UINT pkt_start=0, pkt_stop=0;

/* NMapi variables START */
HANDLE inputHandle = NULL;
HANDLE outputHandle = NULL;

ULONG response = 0;
ULONG adapterIndex = 0;
ULONG adapterCount = 0;
ULONG maxFileSize = 0;

NM_NIC_ADAPTER_INFO AdapterInfo;
NM_CAPTURE_STATISTICS NMstats;
/* NMapi variables END */

/* Buffer Variables START */
UINT maxSnapLen=160, maxBufferSize=(44*1024000);
packet_unit **bufferTot;
UINT num_unit = 0;
/* Buffer Variables END */

struct device devices[22];
struct statistics stats;




void print_hex_ascii_line(const u_char *payload, int len, int offset, char *packet)
{
	int i;
	int gap;
	const u_char *ch;
	char buffer[22];

	/* offset */
	sprintf_s(buffer,22,"| %05d |  ", offset);
	strcat(packet,buffer);

	/* hex */
	ch = payload;
	for(i = 0; i < len; i++)
	{
		sprintf_s(buffer,22,"%02x ", *ch);
		strcat(packet,buffer);
		ch++;
		/* print extra space after 8th byte for visual aid */
		if (i == 7) {strcat(packet," ");}
	}
	/* print space to handle line less than 8 bytes */
	if (len < 8) {strcat(packet," ");}

	/* fill hex gap with spaces if not full line */
	if (len < 16)
	{
		gap = 16 - len;
		for (i = 0; i < gap; i++) {strcat(packet,"   ");}
	}
	strcat(packet," | ");

	/* ascii (if printable) */
	ch = payload;
	for(i = 0; i < len; i++)
	{
		if (isprint(*ch))
		{
			sprintf_s(buffer,22,"%c", *ch);
			strcat(packet,buffer);
		}
		else {strcat(packet,".");}
		ch++;
	}

	if (len < 16)
	{
		gap = 16 - len;
		for (i = 0; i < gap; i++) {strcat(packet,".");}
	}
	strcat(packet," |\n");

    return;
}


void print_payload(const u_char *payload, int len)
{
	int len_rem = len;
	int line_width = 16;			/* number of bytes per line */
	int line_len;
	int offset = 0;					/* zero-based offset counter */
	const u_char *ch = payload;
	char *packet;

	packet = (char *)MALLOC(88*((len/line_width)+1));

	strcpy(packet,"\n");

	if (len <= 0) {return;}

	/* data fits on one line */
	if (len <= line_width)
	{
		print_hex_ascii_line(ch, len, offset, packet);
		return;
	}

	/* data spans multiple lines */
	for ( ;; )
	{
		/* compute current line length */
		line_len = line_width % len_rem;
		/* print line */
		print_hex_ascii_line(ch, line_len, offset, packet);
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
			print_hex_ascii_line(ch, len_rem, offset, packet);
			break;
		}
	}

	fprintf(debug_log,"%s",packet);

	FREE(packet);

    return;
}


void setfilter(const char *filter)
{
	/* DEBUG BEGIN */
	//if(DEBUG_MODE && (fopen_s(&debug_log,"pktman.txt","a") == 0))
	//{
	//	fprintf(debug_log,"\nFILTRO: %s \n",filter);
	//	fclose(debug_log);
	//	debug_log = NULL;
	//}
	/* DEBUG END */
}


void configNMapi()
{
	NM_API_CONFIGURATION NmApiConfig;
	NmApiConfig.Size = sizeof(NM_API_CONFIGURATION);
	
	response = NmGetApiConfiguration(&NmApiConfig);
	if (response == ERROR_SUCCESS)
	{
		NmApiConfig.ThreadingMode = COINIT_MULTITHREADED;
		// maxFileSize = NmApiConfig.MaxCaptureFileSize;

		response = NmApiInitialize(&NmApiConfig);
		if (response == ERROR_SUCCESS)
		{/*printf("\nOK CONFIG API\n")*/;}
	}
}


void updateStats()
{
	NMstats.Size = sizeof(NMstats);	/* Necessary for NMstats */

	/* Get Statistics */
	response = NmGetLiveCaptureFrameCounts(inputHandle, adapterIndex, &NMstats);
	if (response == ERROR_SUCCESS)
	{
		stats.pkt_tot = (ULONG)NMstats.DriverSeenCount;
		stats.pkt_drop = (ULONG)NMstats.DriverDropCount;
		stats.pkt_dropHandle = (ULONG)NMstats.EngineDropCount;
		stats.pkt_filtered = (ULONG)NMstats.DriverFilteredCount;
	}
}


void writeBuffer(HANDLE rawFrame)
{
	AdapterInfo.Size = sizeof(AdapterInfo); /* Necessary for AdapterInfo */
	int ExtraByte = 0;
	int OffSetMac = 0;
	
	UINT index=0;
	UINT SnapLen = 0;
	ULONG datalink = 0;
	ULONG rawFrameLen = 0;
	ULONG rawFrameSnapLen = 0;
	UINT64 timestamp = 0;
	
	PBYTE buffer_data, buffer_mac;
	packet_unit *packet;
	packet_header *pkt_header;
	char *pkt_data;

	packet = (packet_unit *)MALLOC(sizeof(packet_unit));
	pkt_header = (packet_header *)MALLOC(sizeof(packet_header));

	/* Frame TimeStamp */
	response = NmGetFrameTimeStamp(rawFrame, &timestamp);
	if (response == ERROR_SUCCESS)
	{
		pkt_header->sec = (ULONG)((timestamp/10000000)-11644473600-7200);	/* 11644473600 is the seconds between [00:00:00 1/1/1601] and [00:00:00 1/1/1970] */
		pkt_header->usec = (ULONG)((timestamp%10000000)/10);				/* timestamp use decimal of microseconds (100 nanoseconds) and we need microseconds */
	}

	/* Frame Data Link Type */
	response = NmGetFrameMacType(rawFrame, &datalink);
	if (response == ERROR_SUCCESS)
	{ data_link = (int)datalink; }

	/* Frame Length */
	response = NmGetRawFrameLength(rawFrame, &rawFrameLen);	
	if (response == ERROR_SUCCESS)
	{;}

	/* Extract Frame*/
	buffer_data = (PBYTE)MALLOC(rawFrameLen);

	response = NmGetRawFrame(rawFrame, rawFrameLen, buffer_data, &rawFrameSnapLen);
	if (response == ERROR_SUCCESS)
	{
		if (datalink == 6)
		{
			OffSetMac = 36;

			if ((buffer_data[32] & 0xFF) == 0x08)
			{ ExtraByte = 50; }
			else if ((buffer_data[32] & 0xFF) == 0x88)
			{ ExtraByte = 52; }
			else
			{ ExtraByte = -12; }
		}
		else if (datalink == 8)
		{
			OffSetMac = 0;
			ExtraByte = -14;

			buffer_mac = (PBYTE)MALLOC(14);
			
			response = NmGetAdapter(inputHandle, adapterIndex, &AdapterInfo);
			if (response != ERROR_SUCCESS)
			{
				for (index = 0; index < 12 ; index++)
				{buffer_mac[index] = 0xFF;}
			}
			else
			{
				for (index = 0; index < 6 ; index++)
				{
					buffer_mac[index] = AdapterInfo.PermanentAddr[index];
					buffer_mac[index+6] = AdapterInfo.PermanentAddr[index];
				}
			}

			buffer_mac[12] = 0x08;
			buffer_mac[13] = 0x00;
		}
		else
		{
			OffSetMac = 0;
			ExtraByte = 0;
		}

		/* Frame Snap Length */
		if ( ((UINT)rawFrameLen - ExtraByte) < maxSnapLen )
		{ SnapLen = ((UINT)rawFrameLen - ExtraByte); }
		else if (ExtraByte == -12)
		{ SnapLen = 14; }
		else
		{ SnapLen = maxSnapLen; }

		/* Fill DATA */
		pkt_data = (char *)MALLOC(SnapLen);

		if (datalink != 8)
		{
			memcpy_s(pkt_data, SnapLen, buffer_data + OffSetMac, 12);
			memcpy_s(pkt_data + 12, SnapLen, buffer_data + (12 + ExtraByte), 2);
		}
		else
		{
			memcpy_s(pkt_data, SnapLen, buffer_mac, 14);
			FREE(buffer_mac);
		}
		
		memcpy_s(pkt_data + 14, SnapLen, buffer_data + (14 + ExtraByte), (SnapLen - 14));

		/* Fill HEADER*/
		pkt_header->len = ( (UINT)rawFrameLen - ExtraByte );
		pkt_header->caplen = SnapLen;

		/* Fill PACKET with HEADER and DATA */
		packet->header = pkt_header;
		packet->data = pkt_data;

		/* WRITE BUFFER */
		index = (stats.last_write+1) % num_unit;
		if (bufferTot[index] == NULL)
		{
			bufferTot[index] = packet;
			stats.last_write++;
		}
		else
		{
			stats.write_dropped++;
		}

	}

	FREE(buffer_data);
}


void __stdcall theCallback(HANDLE NMhandle, ULONG NMdevice, PVOID NMcontext, HANDLE rawFrame)
{
	if(sniff_mode >= 0)
	{
		writeBuffer(rawFrame);
	}
	else if (outputHandle != NULL)
	{
		response = NmAddFrame(outputHandle, rawFrame);
		if (response == ERROR_SUCCESS)
		{stats.last_write++;}
	}

	/* DEBUG BEGIN */
	if(DEBUG_MODE && (debug_log != NULL))
	{
		if(stats.last_write % 10 == 1)
		{
			fprintf(debug_log,"\n|Operation |Last Write|In Buffer |Last Read |Total Cap |Dropped   |Dropped En|Dropped Wr|FilteredEN|");
			fprintf(debug_log,"\n====================================================================================================");
		}

		fprintf(debug_log,"\n|  WRITE   | %08d | %08d | %08d | %08d | %08d | %08d | %08d | %08d |"
				, stats.last_write, (stats.last_write - stats.last_read), stats.last_read
				, stats.pkt_tot , stats.pkt_drop, stats.pkt_dropHandle, stats.write_dropped, stats.pkt_filtered
				);
		
		fprintf(debug_log,"\t\t[ Data Link Type: %d ]", data_link);
		
		fprintf(debug_log,"\n====================================================================================================");
	}
	/* DEBUG END */
}


int sniffer()
{
	int sniff_status=0;

	struct tm *ts;
	time_t timestamp;
	char timestamp_string[44];

    packet_header *header;
    char *data;

	UINT index=0;

	py_pkt_header = Py_None;
	py_pkt_data = Py_None;
	
	if (timeout >= 1000)
	{
		sniff_start = time(NULL);
		if (sniff_stop < sniff_start)
		{sniff_stop = sniff_start + ((time_t)(timeout/1000)) + 1;}

		sniff_status=0;
	}
	else
	{
		sniff_start = time(NULL);
		sniff_stop = sniff_start + 1;
	}

	while (time(NULL) < sniff_stop)
	{
		index = (stats.last_read+1) % num_unit;
		if ((stats.last_write > stats.last_read) && (bufferTot[index] != NULL))
		{
			header = bufferTot[index]->header;
			data = bufferTot[index]->data;

			/* DEBUG BEGIN */
			if(DEBUG_MODE && (debug_log != NULL))
			{
				timestamp = header->sec;
				ts = (struct tm *)MALLOC(sizeof(struct tm));
				localtime_s(ts,&timestamp);
				strftime(timestamp_string, sizeof(timestamp_string), "%a %Y/%m/%d %H:%M:%S", (const struct tm *) ts);
				FREE(ts);

				if(stats.last_read % 10 == 1)
				{
					fprintf(debug_log,"\n|Operation |Last Write|In Buffer |Last Read |Timestamp of the packet read    |Packet Len|Snap Len  |");
					fprintf(debug_log,"\n====================================================================================================");
				}

				fprintf(debug_log,"\n|  READ    | %08d | %08d | %08d | %s.%.6d | %08d | %08d |"
						, stats.last_write, (stats.last_write - stats.last_read), stats.last_read
						, timestamp_string, header->usec
						, header->len, header->caplen
						);

				fprintf(debug_log,"\n====================================================================================================");

				print_payload((const u_char *)data,header->caplen);

				fprintf(debug_log,"====================================================================================================");
				//fprintf(debug_log,"================================================================================");
			}
			/* DEBUG END */
			
			if (sniff_mode > 0)
			{
				py_pkt_header = PyString_FromStringAndSize((const char *)header,sizeof(*header));
				py_pkt_data = PyString_FromStringAndSize((const char *)data,(header->caplen));
				sniff_status=1;
			}

			if (pkt_stop>pkt_start && pkt_stop>0)
			{
				if (stats.last_read<pkt_start || stats.last_read>pkt_stop)
				{
					py_pkt_header = Py_None;
					py_pkt_data = Py_None;
					sniff_status=2;
				}
			}

			FREE(bufferTot[index]->header);
			bufferTot[index]->header = NULL;
			FREE(bufferTot[index]->data);
			bufferTot[index]->data = NULL;
			FREE(bufferTot[index]);
			bufferTot[index] = NULL;
			
			stats.last_read++;
			break;
		}
		else if (timeout < 1000)
		{
			sniff_status=1;
			break;
		}
	}

	return sniff_status;
}


void dumper(void)
{
	WCHAR *fileName;
	ULONG fileSize;
	size_t filenameSize = strlen(dump_file)+1;

	fileName=(WCHAR *)MALLOC(filenameSize);
	mbstowcs_s(&filenameSize,fileName,filenameSize,dump_file,filenameSize);

	response = NmCreateCaptureFile((LPCWSTR)fileName, 10*maxBufferSize /* maxFileSize */, NmCaptureFileChain, &outputHandle, &fileSize);
	if(response != ERROR_SUCCESS)
	{sprintf_s(err_str,sizeof(err_str),"Error creating output file: 0x%X",response);err_flag=-1;return;}

    /* DEBUG BEGIN */
    if(DEBUG_MODE && (fopen_s(&debug_log,"pktman.txt","a") == 0))
	{
		fprintf(debug_log,"\n[ DUMP MODE ]    [ File Name: %S ]    [ Max File Size: %u ]\n",fileName,fileSize);
		fclose(debug_log);
		debug_log = NULL;
	}
    /* DEBUG END */

	FREE(fileName);
}


UINT dot_to_int(const char *dot)
{
    UINT res;
    UINT dot1,dot2,dot3,dot4;

    if (sscanf_s(dot,"%u.%u.%u.%u", &dot1, &dot2, &dot3, &dot4) == 4)
    {
        res=(dot1*16777216)+(dot2*65536)+(dot3*256)+(dot4*1);
        return res;
    }

    return 0;
}


char *int_to_dot(UINT address, char *res)
{
    UINT i;
    UINT addr;
    UINT dot[4];
    UINT base[4] = {16777216, 65536, 256, 1};

    for(i = 0; i <= 3 ; i++)
    {
        addr = address;
        dot[i] = addr / base[i];
        address = addr % base[i];
    }
    sprintf_s(res,16,"%u.%u.%u.%u",dot[0],dot[1],dot[2],dot[3]);

	return res;
}


char *cidr_to_dot(ULONG cidr, char *mask)
{
    char *mask255 = "255.255.255.255";
	double ui_net = 0;
	UINT ui_mask=0, ui_mask255=0;
	UINT i, bits;

	bits = 32 - (UINT)cidr;
	ui_mask255 = dot_to_int(mask255);
    
	for(i = 0; i < bits ; i++)
    {ui_net += pow(2,(double)i);}

    ui_mask = ui_mask255 - (UINT)ui_net;
    mask = int_to_dot(ui_mask, mask);

    return mask;
}


UINT find_devices(void)
{
	UINT i=0, tot_dev=0;
	
	struct in_addr addr;
	char *guid, *ip, *net, *mask;

	size_t sizeBuff;

	AdapterInfo.Size = sizeof(AdapterInfo); /* Necessary for AdapterInfo */

	/* Declare and initialize variables */
    DWORD dwSize = 0;
    DWORD dwRetVal = 0;

	ULONG outBufLen = 0;
    ULONG nRetries = 0;

	ULONG flags = GAA_FLAG_INCLUDE_PREFIX;	/* Set the flags to pass to GetAdaptersAddresses */
	ULONG family = AF_UNSPEC;				/* Unspecified address family (both IPv4 and IPv6) */

	/* POINTERS */
	PIP_ADAPTER_ADDRESSES pAddresses = NULL;
	PIP_ADAPTER_ADDRESSES pCurrAddresses = NULL;
    PIP_ADAPTER_UNICAST_ADDRESS pUnicast = NULL;
    // PIP_ADAPTER_ANYCAST_ADDRESS pAnycast = NULL;
    // PIP_ADAPTER_MULTICAST_ADDRESS pMulticast = NULL;
    // IP_ADAPTER_DNS_SERVER_ADDRESS *pDnServer = NULL;
    PIP_ADAPTER_PREFIX pPrefix = NULL;

	for(i = 0; i<22; i++)
	{
		FREE(devices[i].name);  devices[i].name = NULL;
		FREE(devices[i].description);  devices[i].description = NULL;
		FREE(devices[i].mac);  devices[i].mac = NULL;
		FREE(devices[i].ip);  devices[i].ip = NULL;
		FREE(devices[i].net);  devices[i].net = NULL;
		FREE(devices[i].mask);  devices[i].mask = NULL;
	}

	/* DEBUG BEGIN */
	if(DEBUG_MODE && (fopen_s(&debug_log,"pktman.txt","a") == 0))
	{
		fprintf(debug_log,"========================================================================================[DEVICE]\n\n");
		fclose(debug_log);
		debug_log = NULL;
	}
	/* DEBUG END */

    outBufLen = 40000;	/* Allocate a 40 KB buffer to start with. */

	/* Capture Engime using NMapi */
	if(inputHandle == NULL)
	{
		response = NmOpenCaptureEngine(&inputHandle);
		if(response != ERROR_SUCCESS)
		{
			configNMapi();
			response = NmOpenCaptureEngine(&inputHandle);
			if(response != ERROR_SUCCESS)
			{sprintf_s(err_str,sizeof(err_str),"Error opening input handle: 0x%X",response);err_flag=-1;return tot_dev;}
		}
	}

	response = NmGetAdapterCount(inputHandle, &adapterCount);
	if(response != ERROR_SUCCESS)
	{sprintf_s(err_str,sizeof(err_str),"No Sniffable Device or User Without Root Permissions");err_flag=-1;return tot_dev;}

	/* DEBUG BEGIN */
	for(i = 0; i < adapterCount; i++)
	{
		response = NmGetAdapter(inputHandle, i, &AdapterInfo);
		if(response != ERROR_SUCCESS)
		{/* sprintf_s(err_str,sizeof(err_str),"Error getting adapter info: 0x%X",response);err_flag=-1;return tot_dev */;}
		else if(DEBUG_MODE && (fopen_s(&debug_log,"pktman.txt","a") == 0))
		{
			fprintf(debug_log,"\t----====[Network Monitor Device N.%02d]====----\n",i);
			fprintf(debug_log,"\tGUID : %S\n", AdapterInfo.Guid);
			fprintf(debug_log,"\tMediumType : %s [%i]\n", MediumName[AdapterInfo.MediumType], (int)AdapterInfo.MediumType);
			fprintf(debug_log,"\tPhysicalMediumType : %s [%i]\n", PhysicalMediumName[AdapterInfo.PhysicalMediumType], (int)AdapterInfo.PhysicalMediumType);
			fprintf(debug_log,"\tFriendlyName : %S\n", AdapterInfo.FriendlyName);
			fprintf(debug_log,"\tConnectionName : %S\n", AdapterInfo.ConnectionName);
			fprintf(debug_log,"\tPermanentAddr : %02X:%02X:%02X:%02X:%02X:%02X\n"
					,AdapterInfo.PermanentAddr[0],AdapterInfo.PermanentAddr[1],AdapterInfo.PermanentAddr[2]
					,AdapterInfo.PermanentAddr[3],AdapterInfo.PermanentAddr[4],AdapterInfo.PermanentAddr[5]
					);
			fprintf(debug_log,"\tCurrentAddr : %02X:%02X:%02X:%02X:%02X:%02X\n"
					,AdapterInfo.CurrentAddr[0],AdapterInfo.CurrentAddr[1],AdapterInfo.CurrentAddr[2]
					,AdapterInfo.CurrentAddr[3],AdapterInfo.CurrentAddr[4],AdapterInfo.CurrentAddr[5]
					);
			fprintf(debug_log,"\t\n");

			fclose(debug_log);
			debug_log = NULL;
		}
	}
	/* DEBUG END */
	/* -------------------------- */

	do
	{
		pAddresses = (IP_ADAPTER_ADDRESSES *) MALLOC(outBufLen);
        if (pAddresses == NULL)
		{sprintf_s(err_str,sizeof(err_str),"Memory allocation failed for IP_ADAPTER_ADDRESSES struct");err_flag=-1;return tot_dev;}

        dwRetVal = GetAdaptersAddresses(family, flags, NULL, pAddresses, &outBufLen);
		if (dwRetVal == ERROR_BUFFER_OVERFLOW)
		{
			FREE(pAddresses);
			pAddresses = NULL;
			nRetries++;
		    outBufLen += 20000;
        }
    }
	while ((dwRetVal == ERROR_BUFFER_OVERFLOW) && (nRetries < 4));

	if (dwRetVal != NO_ERROR)
	{sprintf_s(err_str,sizeof(err_str),"No Sniffable Device or User Without Root Permissions");err_flag=-1;return tot_dev;}
	else
	{
		tot_dev=0;
        pCurrAddresses = pAddresses;

		while (pCurrAddresses)
		{
			tot_dev++;

			/* Device Name */
			devices[tot_dev].name=(char *)MALLOC(strlen(pCurrAddresses->AdapterName)+1);
			memcpy(devices[tot_dev].name,pCurrAddresses->AdapterName,strlen(pCurrAddresses->AdapterName)+1);

			/* Info from NMapi */
			devices[tot_dev].index = -1;

			devices[tot_dev].mac = (char *)MALLOC(18*sizeof(char));
			if ((int)(pCurrAddresses->PhysicalAddressLength) >= 6)
			{
				sprintf_s(devices[tot_dev].mac,18,"%02X:%02X:%02X:%02X:%02X:%02X"
						,pCurrAddresses->PhysicalAddress[0],pCurrAddresses->PhysicalAddress[1],pCurrAddresses->PhysicalAddress[2]
						,pCurrAddresses->PhysicalAddress[3],pCurrAddresses->PhysicalAddress[4],pCurrAddresses->PhysicalAddress[5]
						);
			}
			else
			{
				sprintf_s(devices[tot_dev].mac,18,"--:--:--:--:--:--");
			}

			for(i = 0; i < adapterCount; i++)
			{
				response = NmGetAdapter(inputHandle, i, &AdapterInfo);
				if(response != ERROR_SUCCESS)
				{/* sprintf_s(err_str,sizeof(err_str),"Error getting adapter info: 0x%X",response);err_flag=-1;return tot_dev */;}
				else
				{
					sizeBuff = wcslen(AdapterInfo.Guid)+1;
					guid = (char *)MALLOC(sizeBuff);
					sprintf_s(guid, sizeBuff, "%S", AdapterInfo.Guid);

					if (strcmp(guid,devices[tot_dev].name)==0)
					{
						/* Device Index */
						devices[tot_dev].index = i;
						/* Device Type */
						devices[tot_dev].type = ((int)AdapterInfo.MediumType + (int)AdapterInfo.PhysicalMediumType);

						/* Device Mac Address */
						if (strcmp(devices[tot_dev].mac,"--:--:--:--:--:--")==0)
						{
							sprintf_s(devices[tot_dev].mac,18,"%02X:%02X:%02X:%02X:%02X:%02X"
									,AdapterInfo.PermanentAddr[0],AdapterInfo.PermanentAddr[1],AdapterInfo.PermanentAddr[2]
									,AdapterInfo.PermanentAddr[3],AdapterInfo.PermanentAddr[4],AdapterInfo.PermanentAddr[5]
									);
						}
						break;
					}

					FREE(guid);
					guid = NULL;
				}
			}

			/* Device Description */
			sizeBuff = wcslen(pCurrAddresses->FriendlyName)+1;
			devices[tot_dev].description=(char *)MALLOC(sizeBuff);
			sprintf_s(devices[tot_dev].description, sizeBuff, "%wS", pCurrAddresses->FriendlyName);

			/* Device IP */
			pUnicast = pCurrAddresses->FirstUnicastAddress;

			if (pUnicast != NULL)
			{
				for (i = 0; pUnicast != NULL; i++)
				{
					if (pUnicast->Address.lpSockaddr->sa_family == AF_INET)
                    {
						addr = ((struct sockaddr_in *)pUnicast->Address.lpSockaddr)->sin_addr;
						ip = inet_ntoa(addr);
						devices[tot_dev].ip=(char *)MALLOC(strlen(ip)+1);
						memcpy(devices[tot_dev].ip,ip,strlen(ip)+1);
						break;
                    }

					pUnicast = pUnicast->Next;
				}

				if (pUnicast == NULL)
				{
					devices[tot_dev].ip=(char *)MALLOC(8*sizeof(char));
					sprintf_s(devices[tot_dev].ip,8,"-.-.-.-");
				}
            }
			else
			{
				devices[tot_dev].ip=(char *)MALLOC(8*sizeof(char));
				sprintf_s(devices[tot_dev].ip,8,"-.-.-.-");
			}

			/* Device NET & MASK */
            pPrefix = pCurrAddresses->FirstPrefix;

			if (pPrefix)
			{
				for (i = 0; pPrefix != NULL; i++)
				{
					if (pPrefix->Address.lpSockaddr->sa_family == AF_INET)
                    {
						addr = ((struct sockaddr_in *)pPrefix->Address.lpSockaddr)->sin_addr;
						
						net = inet_ntoa(addr);
						devices[tot_dev].net=(char *)MALLOC(strlen(net)+1);
						memcpy(devices[tot_dev].net,net,strlen(net)+1);
						
						mask = (char *)MALLOC(16*sizeof(char));
						
						mask = cidr_to_dot(pPrefix->PrefixLength, mask);
						devices[tot_dev].mask=(char *)MALLOC(strlen(mask)+1);
						memcpy(devices[tot_dev].mask,mask,strlen(mask)+1);

						FREE(mask);
						mask = NULL;

						break;
                    }
                    pPrefix = pPrefix->Next;
				}

				if (pPrefix == NULL)
				{
					devices[tot_dev].net=(char *)MALLOC(8*sizeof(char));
					sprintf_s(devices[tot_dev].net,8,"-.-.-.-");
					devices[tot_dev].mask=(char *)MALLOC(8*sizeof(char));
					sprintf_s(devices[tot_dev].mask,8,"-.-.-.-");
				}
            }
			else
			{
				devices[tot_dev].net=(char *)MALLOC(8*sizeof(char));
				sprintf_s(devices[tot_dev].net,8,"-.-.-.-");
				devices[tot_dev].mask=(char *)MALLOC(8*sizeof(char));
				sprintf_s(devices[tot_dev].mask,8,"-.-.-.-");
			}

			if ((devices[tot_dev].index==-1) && (strcmp(devices[tot_dev].net,devices[tot_dev].mask)==0))
			{
				for(i = 0; i < adapterCount; i++)
				{
					response = NmGetAdapter(inputHandle, i, &AdapterInfo);
					if(response != ERROR_SUCCESS)
					{/* sprintf_s(err_str,sizeof(err_str),"Error getting adapter info: 0x%X",response);err_flag=-1;return tot_dev */;}
					else
					{
						sizeBuff = wcslen(AdapterInfo.FriendlyName)+1;
						guid = (char *)MALLOC(sizeBuff);
						sprintf_s(guid, sizeBuff, "%S", AdapterInfo.FriendlyName);

						if (strstr(guid,"NDISWAN")!=NULL)
						{
							/* Device Index */
							devices[tot_dev].index = i;
							/* Device Type */
							devices[tot_dev].type = ((int)AdapterInfo.MediumType + (int)AdapterInfo.PhysicalMediumType);

							/* Device Mac Address */
							if (strcmp(devices[tot_dev].mac,"--:--:--:--:--:--")==0)
							{
								sprintf_s(devices[tot_dev].mac,18,"%02X:%02X:%02X:%02X:%02X:%02X"
										,AdapterInfo.PermanentAddr[0],AdapterInfo.PermanentAddr[1],AdapterInfo.PermanentAddr[2]
										,AdapterInfo.PermanentAddr[3],AdapterInfo.PermanentAddr[4],AdapterInfo.PermanentAddr[5]
										);
							}
							break;
						}

						FREE(guid);
						guid = NULL;
					}
				}
			}

			/* DEBUG BEGIN */
			if(DEBUG_MODE && (fopen_s(&debug_log,"pktman.txt","a") == 0))
			{
				fprintf(debug_log,"\t----====[DEVICE N.%02d]====----\n",tot_dev);
				fprintf(debug_log,"\tNAME:\t%s\n",devices[tot_dev].name);
				fprintf(debug_log,"\tDESCR:\t%s\n",devices[tot_dev].description);
				fprintf(debug_log,"\tMAC:\t%s\n",devices[tot_dev].mac);
				fprintf(debug_log,"\tIP:\t%s\n",devices[tot_dev].ip);
				fprintf(debug_log,"\tNET:\t%s\n",devices[tot_dev].net);
				fprintf(debug_log,"\tMASK:\t%s\n",devices[tot_dev].mask);
				fprintf(debug_log,"\tINDEX:\t%d\n",devices[tot_dev].index);
				fprintf(debug_log,"\tMEDIUM:\t%d\n",devices[tot_dev].type);
				fprintf(debug_log,"\t\n");

				fclose(debug_log);
				debug_log = NULL;
			}
			/* DEBUG END */

			pCurrAddresses = pCurrAddresses->Next;
		}
	}

	if (pAddresses)
	{
		FREE(pAddresses);
		pAddresses = NULL;
	}

	//NmCloseHandle(inputHandle);
	//inputHandle = NULL;

	/* DEBUG BEGIN */
	if(DEBUG_MODE && (fopen_s(&debug_log,"pktman.txt","a") == 0))
	{
		fprintf(debug_log,"========================================================================================[DEVICE]\n\n");
		fclose(debug_log);
		debug_log = NULL;
	}
	/* DEBUG END */

	return tot_dev;
}


int ip_in_net(const char *ip, const char *net, const char *mask)
{
    char *mask255 = "255.255.255.255";
	char *net0 = "0.0.0.0";

    UINT ui_ip=0, ui_net=0, ui_mask=0;

    ui_ip = dot_to_int(ip);
    ui_net = dot_to_int(net);
    ui_mask = dot_to_int(mask);

    if (((ui_ip & ui_mask) == (ui_net & ui_mask)) && (ui_mask!=0))
    {return 1;}
    else if ((strcmp(mask,mask255)==0) && !(strcmp(net,net0)==0))
    {return 1;}
    else
    {return 0;}
}


UINT select_device(char *dev)
{
	UINT tot_dev=0, sel_dev=0, indice=0, IpInNet=0;

    int find[22];

    tot_dev = find_devices();

    if(err_flag != 0) {return sel_dev;}

    sel_dev=0;

	/* DEBUG BEGIN */
	if(DEBUG_MODE && (fopen_s(&debug_log,"pktman.txt","a") == 0))
	{
		fprintf(debug_log,"\nSEARCHING FOR: %s\n",dev);
		fclose(debug_log);
		debug_log = NULL;
	}
    /* DEBUG END */

    for(sel_dev=1; sel_dev<=tot_dev; sel_dev++)
    {
        IpInNet = ip_in_net(dev,devices[sel_dev].net,devices[sel_dev].mask);

        /* DEBUG BEGIN */
        if(DEBUG_MODE && (fopen_s(&debug_log,"pktman.txt","a") == 0))
        {
            fprintf(debug_log,"\nNAME: %s\nIP: %s\nNET: %s\nMASK: %s\nIpInNet: %i\n",devices[sel_dev].name,devices[sel_dev].ip,devices[sel_dev].net,devices[sel_dev].mask,IpInNet);
			fclose(debug_log);
			debug_log = NULL;
        }
        /* DEBUG END */

        if (strstr(devices[sel_dev].name,dev)!=NULL||(strcmp(dev,devices[sel_dev].name)==0)||(strcmp(dev,devices[sel_dev].ip)==0))
        {
            indice++;
            find[indice]=sel_dev;
			/* DEBUG BEGIN */
			if(DEBUG_MODE && (fopen_s(&debug_log,"pktman.txt","a") == 0))
			{
				fprintf(debug_log,"\n[%i] Trovato Device n°%i [%s]\n",indice,sel_dev,devices[sel_dev].name);
				fclose(debug_log);
				debug_log = NULL;
			}
			/* DEBUG END */
        }
    }

    sel_dev=0;

    while (indice!=0)
    {
        sel_dev=find[indice];
		/* DEBUG BEGIN */
        if(DEBUG_MODE && (fopen_s(&debug_log,"pktman.txt","a") == 0))
        {
			fprintf(debug_log,"\n[%i] Scelto Device n°%i [%s]\n",indice,sel_dev,devices[sel_dev].name);
			fclose(debug_log);
			debug_log = NULL;
		}
        /* DEBUG END */
        
        indice--;

        if (indice>0)
        {
			sel_dev=0;
			err_flag=-1;
			sprintf_s(err_str,sizeof(err_str),"Ambiguity in the choice of the device");
			return sel_dev;
        }
    }

    if (sel_dev==0)
    {sprintf_s(err_str,sizeof(err_str),"Device Not Found or Not Initialized");err_flag=-1;return sel_dev;}

	return sel_dev;
}


void initialize(char *dev, UINT promisc)
{
    UINT i=0, sel_dev=0;
	WCHAR *fileName;
	size_t filenameSize = strlen(dump_file)+1;
	HANDLE rawFrame = NULL;

	AdapterInfo.Size = sizeof(AdapterInfo); /* Necessary for AdapterInfo */

	memset(&stats,0,sizeof(struct statistics));
	
	/* BUFFER */
	if (maxBufferSize > (44*1024000))
	{maxBufferSize = (44*1024000);}

	num_unit = maxBufferSize / (maxSnapLen + 16);
	bufferTot = (packet_unit**)MALLOC(num_unit*(sizeof(packet_unit)));

	for (i = 0; i <= num_unit; i++)
	{bufferTot[i]=NULL;}
	
	/* DEBUG BEGIN */
	if(DEBUG_MODE && (fopen_s(&debug_log,"pktman.txt","a") == 0))
	{
		fprintf(debug_log,"\nNUMERO DI SLOT NEL BUFFER CICLICO : %d\n\n",num_unit);
		fclose(debug_log);
		debug_log = NULL;
	}
	/* DEBUG END */

    if (online==0)
    {
		fileName=(WCHAR *)MALLOC(strlen(dump_file)+1);
		mbstowcs_s(&filenameSize,fileName,filenameSize,dump_file,filenameSize);

		/* Open Capture File */
		response = NmOpenCaptureFile((LPCWSTR)fileName, &inputHandle);
		if(response != ERROR_SUCCESS)
		{sprintf_s(err_str,sizeof(err_str),"Error opening input file: 0x%X",response);err_flag=-1;return;}
		
		response = NmGetFrameCount(inputHandle, &(stats.pkt_tot));
		if(response != ERROR_SUCCESS)
		{sprintf_s(err_str,sizeof(err_str),"Error counting packet in file: 0x%X",response);err_flag=-1;return;}

		/* DEBUG BEGIN */
		if(DEBUG_MODE && (fopen_s(&debug_log,"pktman.txt","a") == 0))
		{
			fprintf(debug_log,"\n[ OFFLINE MODE ]    [ File Name: %S ]    [ Packet in File: %u ]\n",fileName,stats.pkt_tot);
			fclose(debug_log);
			debug_log = NULL;
		}
		/* DEBUG END */

		for(i = 0; i < stats.pkt_tot; i++)
		{
			response = NmGetFrame(inputHandle, i, &rawFrame);
			if(response != ERROR_SUCCESS)
			{sprintf_s(err_str,sizeof(err_str),"Error getting packet from file: 0x%X",response);err_flag=-1;return;}
			theCallback(inputHandle, adapterIndex, outputHandle, rawFrame);
			NmCloseHandle(rawFrame);
			rawFrame = NULL;
		}

		NmCloseHandle(inputHandle);
		inputHandle = NULL;
    }
    else
    {		
        sel_dev = select_device(dev);
        if(err_flag != 0) {return;}

		adapterIndex = devices[sel_dev].index;
		if(adapterIndex == -1)
		{sprintf_s(err_str,sizeof(err_str),"Can't find adapter in Network Monitor");err_flag=-1;return;}

		/* Get the adapter info */
		response = NmGetAdapter(inputHandle, adapterIndex, &AdapterInfo);
		if(response != ERROR_SUCCESS)
		{sprintf_s(err_str,sizeof(err_str),"Error getting adapter info: 0x%X",response);err_flag=-1;return;}

		/* Configure the adapter */
		response = NmConfigAdapter(inputHandle, adapterIndex, theCallback, outputHandle, NmReturnRemainFrames);
		if(response != ERROR_SUCCESS)
		{sprintf_s(err_str,sizeof(err_str),"Error configuring the adapter: 0x%X",response);err_flag=-1;return;}

		/* Start Capture */
		if ((promisc == 1) && (AdapterInfo.PModeEnabled))
		{
			response = NmStartCapture(inputHandle, adapterIndex, NmPromiscuous);
		}
		else
		{
			response = NmStartCapture(inputHandle, adapterIndex, NmLocalOnly);
		}
		
		if(response != ERROR_SUCCESS)
		{sprintf_s(err_str,sizeof(err_str),"Error starting capture: 0x%X",response);err_flag=-1;return;}

        /* DEBUG BEGIN */
        if(DEBUG_MODE && (fopen_s(&debug_log,"pktman.txt","a") == 0))
        {
            if(sel_dev>0)
            {
                fprintf(debug_log,"\nInitialize Device: %s\n",devices[sel_dev].description);
                fprintf(debug_log,"\nPromiscous: %i\tTimeout: %i\tMax Snap Length: %i\tMax Buffer Size: %i\n",promisc,timeout,maxSnapLen,maxBufferSize);
            }

			//fclose(debug_log);
			//debug_log = NULL;
        }
        /* DEBUG END */
    }
}




/*----Python----*/

#ifdef __cplusplus
extern "C" 
{
#endif

	static PyObject *pktman_debugmode(PyObject *self, PyObject *args)
	{
		PyArg_ParseTuple(args, "i", &DEBUG_MODE);

		/* if(DEBUG_MODE==0) {DEBUG_MODE=1;} */

		/* DEBUG BEGIN */
		if(DEBUG_MODE)
		{
			err_flag = fopen_s(&debug_log,"pktman.txt","w");
			fclose(debug_log);
			debug_log = NULL;
		}
		/* DEBUG END */

		return Py_BuildValue("i",DEBUG_MODE);
	}

	static PyObject *pktman_getdev(PyObject *self, PyObject *args)
	{
		PyObject *key, *val, *devs = PyDict_New();
		
		UINT i=0, tot_dev=0, sel_dev=0;

		char *dev=NULL;

		err_flag=0; strcpy_s(err_str,"No Error");

		PyArg_ParseTuple(args, "|z",&dev);

		if (dev!=NULL)
		{
			sel_dev = select_device(dev);
			if(err_flag != 0)
			{devs = Py_BuildValue ("{s:i,s:s}","err_flag",err_flag,"err_str",err_str);}
			else
			{devs = Py_BuildValue ("{s:i,s:s,s:i,s:i,s:s,s:s,s:s,s:s,s:s,s:s}"
									,"err_flag",err_flag,"err_str",err_str
									,"index",devices[sel_dev].index,"type",devices[sel_dev].type
									,"name",devices[sel_dev].name,"descr",devices[sel_dev].description
									,"mac",devices[sel_dev].mac,"ip",devices[sel_dev].ip
									,"net",devices[sel_dev].net,"mask",devices[sel_dev].mask
									);
			}
		}
		else
		{
			tot_dev = find_devices();
			if(err_flag != 0)
			{devs = Py_BuildValue ("{s:i,s:s}","err_flag",err_flag,"err_str",err_str);}
			else
			{
				val = Py_BuildValue("i",err_flag);
				PyDict_SetItemString(devs,"err_flag",val);
				val = Py_BuildValue("s",err_str);
				PyDict_SetItemString(devs,"err_str",val);
				val = Py_BuildValue("i",tot_dev);
				PyDict_SetItemString(devs,"tot_dev",val);

				for(i=1; i<=tot_dev; i++)
				{
					key = Py_BuildValue("i",i);
					val = Py_BuildValue ("{s:i,s:i,s:s,s:s,s:s,s:s,s:s,s:s}"
										,"index",devices[i].index,"type",devices[i].type
										,"name",devices[i].name,"descr",devices[i].description
										,"mac",devices[i].mac,"ip",devices[i].ip
										,"net",devices[i].net,"mask",devices[i].mask
										);
					PyDict_SetItem(devs,key,val);
				}
		
				if (key != Py_None)
				{Py_CLEAR(key);}
				if (val != Py_None)
				{Py_CLEAR(val);}
			}
		}

		return devs;
	}

	static PyObject *pktman_initialize(PyObject *self, PyObject *args)
	{
		int promisc=1;

		char *dev;

		err_flag=0; strcpy_s(err_str,"No Error");

		PyArg_ParseTuple(args, "s|iiiiizii", &dev, &maxBufferSize, &maxSnapLen, &timeout, &promisc, &online, &dump_file, &pkt_start, &pkt_stop);

		if (dump_file == NULL)
		{
			dump_file = (char *)MALLOC(88*sizeof(char));
			dump_file = "myDumpFile.cap";
		}

		if (err_flag == 0)
		{
			Py_BEGIN_ALLOW_THREADS;
			gil_state = PyGILState_Ensure();

			initialize(dev, promisc);

			PyGILState_Release(gil_state);
			Py_END_ALLOW_THREADS;
		}

		return Py_BuildValue("{s:i,s:s}","err_flag",err_flag,"err_str",err_str);
	}

	static PyObject *pktman_setfilter(PyObject *self, PyObject *args)
	{
		char *filter;

		err_flag=0; strcpy_s(err_str,"No Error");

		PyArg_ParseTuple(args, "s", &filter);

		//if (handle != NULL && filter != NULL)
		//{setfilter(filter);}
		//else
		//{sprintf_s(err_str,sizeof(err_str),"Couldn't Set Filter: No Hadle Active on Networks Interfaces");err_flag=-1;}

		return Py_BuildValue("{s:i,s:s}","err_flag",err_flag,"err_str",err_str);
	}

	static PyObject *pktman_push(PyObject *self, PyObject *args)
	{
		Py_BEGIN_ALLOW_THREADS;
		gil_state = PyGILState_Ensure();

		PyObject *py_pkt;

		int pkt_size=0;

		u_char *pkt_to_send;

		err_flag=0; strcpy_s(err_str,"No Error");

		PyArg_ParseTuple(args,"O",&py_pkt);

		pkt_size=(int)PyString_Size(py_pkt);

		pkt_to_send=(u_char*)PyString_AsString(py_pkt);

		// if((py_pkt->ob_refcnt)>0)
		// {Py_CLEAR(py_pkt);}

		PyGILState_Release(gil_state);
		Py_END_ALLOW_THREADS;

		return Py_BuildValue("{s:i,s:s}","err_flag",err_flag,"err_str",err_str);
	}

	static PyObject *pktman_pull(PyObject *self, PyObject *args)
	{
		int sniff_status=0;

		PyArg_ParseTuple(args, "|i", &sniff_mode);

		if (sniff_mode >= 0)
		{
			if (py_pkt_header != Py_None)
			{Py_CLEAR(py_pkt_header);}
			if (py_pkt_data != Py_None)
			{Py_CLEAR(py_pkt_data);}
			
			Py_BEGIN_ALLOW_THREADS;
			gil_state = PyGILState_Ensure();

			sniff_status = sniffer();

			PyGILState_Release(gil_state);
			Py_END_ALLOW_THREADS;

			return Py_BuildValue("{s:i,s:s,s:i,s:S,s:S}","err_flag",sniff_status,"err_str",sniff_error[sniff_status],"datalink",data_link,"py_pcap_hdr",py_pkt_header,"py_pcap_data",py_pkt_data);
		}
		else
		{
			Py_BEGIN_ALLOW_THREADS;
			gil_state = PyGILState_Ensure();

			sniff_mode = -1;

			dumper();

			PyGILState_Release(gil_state);
			Py_END_ALLOW_THREADS;

			return Py_BuildValue("{s:i,s:s,s:i,s:s}","err_flag",err_flag,"err_str",err_str,"datalink",data_link,"dumpfile",dump_file);
		}
	}

	static PyObject *pktman_close(PyObject *self)
	{
		err_flag=0; strcpy_s(err_str,"No Error");

		Py_BEGIN_ALLOW_THREADS;
		gil_state = PyGILState_Ensure();

		response = NmStopCapture(inputHandle, adapterIndex);
		if (response == ERROR_SUCCESS)
		{
			NmCloseHandle(inputHandle);
			inputHandle = NULL;
			
			NmCloseHandle(outputHandle);
			outputHandle = NULL;

			//NmApiClose();
			FREE(bufferTot);
			bufferTot = NULL;

			/* DEBUG BEGIN */
			if(DEBUG_MODE && (debug_log != NULL))
			{
				fclose(debug_log);
				debug_log = NULL;
			}
			/* DEBUG END */
		}
		else
		{sprintf_s(err_str,sizeof(err_str),"Error stopping capture: 0x%X",response);err_flag=-1;}

		PyGILState_Release(gil_state);
		Py_END_ALLOW_THREADS;

		return Py_BuildValue("{s:i,s:s}","err_flag",err_flag,"err_str",err_str);
	}

	static PyObject *pktman_getstat(PyObject *self)
	{
		char request_time[44];
		struct tm *rt;
		time_t req_time;
		ULONG proc=0, tot=0, drop=0, dropif=0;

		updateStats();
		
		if ( stats.pkt_tot != 0 )
		{
			req_time = time(NULL) + 4;
			while ( (stats.last_write < stats.pkt_tot) && (time(NULL) < req_time) )
			{Sleep(0.2);}
			updateStats();

			tot = stats.pkt_tot - stats.write_dropped;
		}
		else
		{
			tot = stats.last_write;
		}
		
		proc = stats.last_read;
		drop = (stats.pkt_drop + stats.write_dropped);
		dropif = stats.pkt_dropHandle;

		req_time=time(0);
		rt = (struct tm *)MALLOC(sizeof(struct tm));
		localtime_s(rt,&req_time);
		strftime(request_time, sizeof(request_time), "%a %Y/%m/%d %H:%M:%S", (const struct tm *) rt);
		FREE(rt);

		return Py_BuildValue("{s:s,s:l,s:l,s:l,s:l}",
							 "stat_time",request_time,"pkt_pcap_proc",proc,
							 "pkt_pcap_tot",tot,"pkt_pcap_drop",drop,"pkt_dropif",dropif);
	}

	static PyMethodDef pktman_methods[] =
	{
		{ "debugmode", (PyCFunction)pktman_debugmode, METH_VARARGS, NULL},
		{ "getdev", (PyCFunction)pktman_getdev, METH_VARARGS, NULL},
		{ "initialize", (PyCFunction)pktman_initialize, METH_VARARGS, NULL},
		{ "setfilter", (PyCFunction)pktman_setfilter, METH_VARARGS, NULL},
		{ "push", (PyCFunction)pktman_push, METH_VARARGS, NULL},
		{ "pull", (PyCFunction)pktman_pull, METH_VARARGS, NULL},
		{ "close", (PyCFunction)pktman_close, METH_NOARGS, NULL},
		{ "getstat", (PyCFunction)pktman_getstat, METH_NOARGS, NULL},
		{ NULL, NULL, 0, NULL }
	};

	PyMODINIT_FUNC initpktman(void)
	{
		Py_InitModule("pktman", pktman_methods);
	}

#ifdef __cplusplus
}
#endif
