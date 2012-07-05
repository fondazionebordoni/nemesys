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

struct devices
{
	int		index;
	char	*description;
    char	*name;
	char	*mac;
    char	*ip;
    char	*net;
    char	*mask;
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
FILE *debug_log;

char *dump_file;

int err_flag=0;
char err_str[88]="No Error";

PyGILState_STATE gil_state;
PyObject *py_pkt_header, *py_pkt_data;

time_t sniff_start = 0, sniff_stop = 0;

int tot_dev=0, num_dev=0;

int sniff_mode=0, online=1;

UINT data_link=0, timeout = 1;

UINT pkt_start=0, pkt_stop=0;

/* NMapi variables START */
HANDLE inputHandle;
HANDLE outputHandle;

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

struct devices device[22];
struct statistics stats;




void print_hex_ascii_line(const u_char *payload, int len, int offset)
{
	int i;
	int gap;
	const u_char *ch;

	/* offset */
	fprintf(debug_log,"| %05d |  ", offset);

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
	fprintf(debug_log," | ");

	/* ascii (if printable) */
	ch = payload;
	for(i = 0; i < len; i++)
	{
		if (isprint(*ch)) {fprintf(debug_log,"%c", *ch);}
		else {fprintf(debug_log,".");}
		ch++;
	}

	if (len < 16)
	{
		gap = 16 - len;
		for (i = 0; i < gap; i++) {fprintf(debug_log,".");}
	}
	fprintf(debug_log," |\n");

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
	///* DEBUG BEGIN */
	//if(DEBUG_MODE)
	//{
	//	fprintf(debug_log,"\nFILTRO: %s \n",filter);
	//}
	///* DEBUG END */
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
	UINT index=0;
	UINT OffSet = 0;
	UINT SnapLen = 0;
	ULONG datalink = 0;
	ULONG rawFrameLen = 0;
	ULONG rawFrameSnapLen = 0;
	UINT64 timestamp = 0;
	
	PBYTE buffer_data;
	char *pkt_data;

	packet_header *pkt_header = (packet_header *)MALLOC(16);
	packet_unit *packet = (packet_unit *)MALLOC(maxSnapLen+16);

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
	{
		data_link = (int)datalink;
		
		if (data_link == 6)
		{ OffSet = 50; }
		else
		{ OffSet = 0; }
	}

	/* Frame Length */
	response = NmGetRawFrameLength(rawFrame, &rawFrameLen);	
	if (response == ERROR_SUCCESS)
	{pkt_header->len = (UINT)rawFrameLen - OffSet;}

	/* Frame Snap Length */
	if ( (UINT)rawFrameLen < (maxSnapLen + OffSet) )
	{SnapLen = (UINT)rawFrameLen;}
	else
	{SnapLen = (maxSnapLen + OffSet);}

	/* Extract Frame*/
	buffer_data = (PBYTE)MALLOC(SnapLen);
	pkt_data = (char *)MALLOC(SnapLen);

	response = NmGetPartialRawFrame(rawFrame, 0, SnapLen, buffer_data, &rawFrameSnapLen);
	if (response == ERROR_SUCCESS)
	{
		pkt_header->caplen = ( (UINT)rawFrameSnapLen - OffSet );

		if (datalink == 6)
		{
			memcpy_s(pkt_data, SnapLen, buffer_data + 36, 12);
			
			if ((buffer_data[32] & 0xFF) != 8)
			{
				memcpy_s(pkt_data + 12, SnapLen, buffer_data, 2);
				pkt_header->caplen = 14;
			}
			else
			{
				memcpy_s(pkt_data + 12, SnapLen, buffer_data + 62, SnapLen - 12);
			}
		}
		else
		{
			memcpy_s(pkt_data, SnapLen, buffer_data, SnapLen);
		}

		/* HEADER and DATA */
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
	if(DEBUG_MODE)
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
		fprintf(debug_log,"\n====================================================================================================");
	}
	/* DEBUG END */
}


void sniffer()
{
	struct tm *ts;
	time_t timestamp;
	char timestamp_string[44];

    struct packet_header *header;
    char *data;

	UINT index=0;

	py_pkt_header = Py_None;
	py_pkt_data = Py_None;
	
	if (timeout >= 1000)
	{
		sprintf_s(err_str,sizeof(err_str),"Timeout was reached during packet receive");
		err_flag=0;

		sniff_start = time(NULL);
		if (sniff_stop < sniff_start)
		{sniff_stop = sniff_start + ((time_t)(timeout/1000)) + 1;}	
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
			if(DEBUG_MODE)
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

				//fprintf(debug_log,"================================================================================");
				print_payload((const u_char *)data,header->caplen);
			}
			/* DEBUG END */
			
			FREE(bufferTot[index]);
			bufferTot[index] = NULL;
			stats.last_read++;

			if (sniff_mode > 0)
			{
				py_pkt_header = PyString_FromStringAndSize((const char *)header,sizeof(*header));
				py_pkt_data = PyString_FromStringAndSize((const char *)data,(header->caplen));
				err_flag=1;
			}

			if (pkt_stop>pkt_start && pkt_stop>0)
			{
				if (stats.last_read<pkt_start || stats.last_read>pkt_stop)
				{
					py_pkt_header = Py_None;
					py_pkt_data = Py_None;
					err_flag=2;
				}
			}

			sprintf_s(err_str,sizeof(err_str),"One packet pulled");
			break;
		}
		else if (timeout < 1000)
		{
			sprintf_s(err_str,sizeof(err_str),"One packet pulled");
			err_flag=1;
			break;
		}
	}
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
	{sprintf_s(err_str,sizeof(err_str),"Error creating output file: 0x%X\n",response);err_flag=-1;return;}

    /* DEBUG BEGIN */
    if(DEBUG_MODE)
	{fprintf(debug_log,"\n[ DUMP MODE ]    [ File Name: %S ]    [ Max File Size: %u ]\n",fileName,fileSize);}
    /* DEBUG END */
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


void find_devices(void)
{
	UINT i = 0;
	
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

	/* DEBUG BEGIN */
	if(DEBUG_MODE)
	{fprintf(debug_log,"========================================================================================[DEVICE]\n\n");}
	/* DEBUG END */

    outBufLen = 40000;	/* Allocate a 40 KB buffer to start with. */

	/* Capture Engime using NMapi */
	response = NmOpenCaptureEngine(&inputHandle);
	if(response != ERROR_SUCCESS)
	{
		configNMapi();
		response = NmOpenCaptureEngine(&inputHandle);
		if(response != ERROR_SUCCESS)
		{sprintf_s(err_str,sizeof(err_str),"Error opening input handle: 0x%X\n",response);err_flag=-1;return;}
	}

	response = NmGetAdapterCount(inputHandle, &adapterCount);
	if(response != ERROR_SUCCESS)
	{sprintf_s(err_str,sizeof(err_str),"No Sniffable Device or User Without Root Permissions");err_flag=-1;return;}
	/* -------------------------- */

	do
	{
		pAddresses = (IP_ADAPTER_ADDRESSES *) MALLOC(outBufLen);
        if (pAddresses == NULL)
		{sprintf_s(err_str,sizeof(err_str),"Memory allocation failed for IP_ADAPTER_ADDRESSES struct");err_flag=-1;return;}

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
	{sprintf_s(err_str,sizeof(err_str),"No Sniffable Device or User Without Root Permissions");err_flag=-1;return;}
	else
	{
		tot_dev=0;
        pCurrAddresses = pAddresses;

		while (pCurrAddresses)
		{
			tot_dev++;

			/* Device Name */
			device[tot_dev].name=(char *)MALLOC(strlen(pCurrAddresses->AdapterName)+1);
			memcpy(device[tot_dev].name,pCurrAddresses->AdapterName,strlen(pCurrAddresses->AdapterName)+1);

			/* Info from NMapi */
			device[tot_dev].index = -1;

			device[tot_dev].mac = (char *)MALLOC(18*sizeof(char));
			sprintf_s(device[tot_dev].mac,18,"00:00:00:00:00:00");

			for(i = 0; i < adapterCount; i++)
			{
				response = NmGetAdapter(inputHandle, i, &AdapterInfo);
				if(response != ERROR_SUCCESS)
				{sprintf_s(err_str,sizeof(err_str),"Error getting adapter info: 0x%X\n",response);err_flag=-1;return;}
				
				sizeBuff = wcslen(AdapterInfo.Guid)+1;
				guid = (char *)MALLOC(sizeBuff);
				sprintf_s(guid, sizeBuff, "%S", AdapterInfo.Guid);

				if (strcmp(guid,device[tot_dev].name)==0)
				{
					/* Device Index */
					device[tot_dev].index = i;

					/* Device Mac Address */
					sprintf_s(device[tot_dev].mac,18,"%02X:%02X:%02X:%02X:%02X:%02X"
							,AdapterInfo.PermanentAddr[0],AdapterInfo.PermanentAddr[1],AdapterInfo.PermanentAddr[2]
							,AdapterInfo.PermanentAddr[3],AdapterInfo.PermanentAddr[4],AdapterInfo.PermanentAddr[5]
							);
					break;
				}

				FREE(guid);
			}

			/* Device Description */
			sizeBuff = wcslen(pCurrAddresses->Description)+1;
			device[tot_dev].description=(char *)MALLOC(sizeBuff);
			sprintf_s(device[tot_dev].description, sizeBuff, "%wS", pCurrAddresses->Description);

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
						device[tot_dev].ip=(char *)MALLOC(strlen(ip)+1);
						memcpy(device[tot_dev].ip,ip,strlen(ip)+1);
						break;
                    }

					pUnicast = pUnicast->Next;
				}

				if (pUnicast == NULL)
				{device[tot_dev].ip="0.0.0.0";}
            }
			else
			{
				device[tot_dev].ip="0.0.0.0";
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
						device[tot_dev].net=(char *)MALLOC(strlen(net)+1);
						memcpy(device[tot_dev].net,net,strlen(net)+1);
						
						mask = (char *)MALLOC(16*sizeof(char));
						
						mask = cidr_to_dot(pPrefix->PrefixLength, mask);
						device[tot_dev].mask=(char *)MALLOC(strlen(mask)+1);
						memcpy(device[tot_dev].mask,mask,strlen(mask)+1);

						FREE(mask);

						break;
                    }
                    pPrefix = pPrefix->Next;
				}

				if (pPrefix == NULL)
				{
					device[tot_dev].net="0.0.0.0";
					device[tot_dev].mask="255.255.255.255";
				}
            }
			else
			{
				device[tot_dev].net="0.0.0.0";
				device[tot_dev].mask="255.255.255.255";
			}

			if ((device[tot_dev].index==-1) && (strcmp(device[tot_dev].net,device[tot_dev].mask)==0))
			{
				for(i = 0; i < adapterCount; i++)
				{
					response = NmGetAdapter(inputHandle, i, &AdapterInfo);
					if(response != ERROR_SUCCESS)
					{sprintf_s(err_str,sizeof(err_str),"Error getting adapter info: 0x%X\n",response);err_flag=-1;return;}
				
					sizeBuff = wcslen(AdapterInfo.FriendlyName)+1;
					guid = (char *)MALLOC(sizeBuff);
					sprintf_s(guid, sizeBuff, "%S", AdapterInfo.FriendlyName);

					if (strstr(guid,"NDISWAN")!=NULL)
					{
						/* Device Index */
						device[tot_dev].index = i;

						/* Device Mac Address */
						sprintf_s(device[tot_dev].mac,18,"%02X:%02X:%02X:%02X:%02X:%02X"
								,AdapterInfo.PermanentAddr[0],AdapterInfo.PermanentAddr[1],AdapterInfo.PermanentAddr[2]
								,AdapterInfo.PermanentAddr[3],AdapterInfo.PermanentAddr[4],AdapterInfo.PermanentAddr[5]
								);
						break;
					}

					FREE(guid);
				}
			}

			/* DEBUG BEGIN */
			if(DEBUG_MODE)
			{
				fprintf(debug_log,"\t----====[DEVICE N.%02d]====----\n",tot_dev);
				fprintf(debug_log,"\tINDEX:\t%d\n",device[tot_dev].index);
				fprintf(debug_log,"\tNAME:\t%s\n",device[tot_dev].name);
				fprintf(debug_log,"\tDESCR:\t%s\n",device[tot_dev].description);
				fprintf(debug_log,"\tMAC:\t%s\n",device[tot_dev].mac);
				fprintf(debug_log,"\tIP:\t%s\n",device[tot_dev].ip);
				fprintf(debug_log,"\tNET:\t%s\n",device[tot_dev].net);
				fprintf(debug_log,"\tMASK:\t%s\n",device[tot_dev].mask);
				fprintf(debug_log,"\t\n",tot_dev);
			}
			/* DEBUG END */

			pCurrAddresses = pCurrAddresses->Next;
		}
	}

	if (pAddresses)
	{FREE(pAddresses);}

	//NmCloseHandle(inputHandle);
	//inputHandle = NULL;

	/* DEBUG BEGIN */
	if(DEBUG_MODE)
	{fprintf(debug_log,"========================================================================================[DEVICE]\n\n");}
	/* DEBUG END */
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


void select_device(char *dev)
{
	UINT indice=0, IpInNet=0;

    int find[22];

    find_devices();
    if(err_flag != 0) {return;}

    num_dev=0;

	/* DEBUG BEGIN */
	if(DEBUG_MODE)
	{fprintf(debug_log,"\nSEARCHING FOR: %s\n",dev);}
    /* DEBUG END */

    for(num_dev=1; num_dev<=tot_dev; num_dev++)
    {
        IpInNet = ip_in_net(dev,device[num_dev].net,device[num_dev].mask);

        /* DEBUG BEGIN */
        if(DEBUG_MODE)
        {
            fprintf(debug_log,"\nNAME: %s\nIP: %s\nNET: %s\nMASK: %s\nIpInNet: %i\n",device[num_dev].name,device[num_dev].ip,device[num_dev].net,device[num_dev].mask,IpInNet);
        }
        /* DEBUG END */

        if (strstr(device[num_dev].name,dev)!=NULL||(strcmp(dev,device[num_dev].name)==0)||(strcmp(dev,device[num_dev].ip)==0))
        {
            indice++;
            find[indice]=num_dev;
			/* DEBUG BEGIN */
			if(DEBUG_MODE)
			{fprintf(debug_log,"\n[%i] Trovato Device n°%i [%s]\n",indice,num_dev,device[num_dev].name);}
			/* DEBUG END */
        }
    }

    num_dev=0;

    while (indice!=0)
    {
        num_dev=find[indice];
		/* DEBUG BEGIN */
        if(DEBUG_MODE)
        {fprintf(debug_log,"\n[%i] Scelto Device n°%i [%s]\n",indice,num_dev,device[num_dev].name);}
        /* DEBUG END */
        
        indice--;

        if (indice>0)
        {
			{sprintf_s(err_str,sizeof(err_str),"Ambiguity in the choice of the device");err_flag=-1;return;}
        }
    }

    if (num_dev==0)
    {sprintf_s(err_str,sizeof(err_str),"Device Not Found or Not Initialized");err_flag=-1;return;}
}


void initialize(char *dev, UINT promisc)
{
    UINT i = 0;
	WCHAR *fileName;
	size_t filenameSize = strlen(dump_file)+1;
	HANDLE rawFrame = NULL;

	AdapterInfo.Size = sizeof(AdapterInfo); /* Necessary for AdapterInfo */

	memset(&stats,0,sizeof(struct statistics));
	
	/* BUFFER */
	if (maxBufferSize > (44*1024000))
	{maxBufferSize = (44*1024000);}

	num_unit = maxBufferSize / (maxSnapLen + 16);
	bufferTot = (packet_unit**)MALLOC(num_unit*(maxSnapLen + 16));

	for (i = 0; i <= num_unit; i++)
	{bufferTot[i]=NULL;}
	
	/* DEBUG BEGIN */
	if(DEBUG_MODE)
	{fprintf(debug_log,"\nNUMERO DI SLOT NEL BUFFER CICLICO : %d\n\n",num_unit);}
	/* DEBUG END */

    if (online==0)
    {
		fileName=(WCHAR *)MALLOC(strlen(dump_file)+1);
		mbstowcs_s(&filenameSize,fileName,filenameSize,dump_file,filenameSize);

		/* Open Capture File */
		response = NmOpenCaptureFile((LPCWSTR)fileName, &inputHandle);
		if(response != ERROR_SUCCESS)
		{sprintf_s(err_str,sizeof(err_str),"Error opening input file: 0x%X\n",response);err_flag=-1;return;}
		
		response = NmGetFrameCount(inputHandle, &(stats.pkt_tot));
		if(response != ERROR_SUCCESS)
		{sprintf_s(err_str,sizeof(err_str),"Error counting packet in file: 0x%X\n",response);err_flag=-1;return;}

		/* DEBUG BEGIN */
		if(DEBUG_MODE)
		{fprintf(debug_log,"\n[ OFFLINE MODE ]    [ File Name: %S ]    [ Packet in File: %u ]\n",fileName,stats.pkt_tot);}
		/* DEBUG END */

		for(i = 0; i < stats.pkt_tot; i++)
		{
			response = NmGetFrame(inputHandle, i, &rawFrame);
			if(response != ERROR_SUCCESS)
			{sprintf_s(err_str,sizeof(err_str),"Error getting packet from file: 0x%X\n",response);err_flag=-1;return;}
			theCallback(inputHandle, adapterIndex, outputHandle, rawFrame);
			NmCloseHandle(rawFrame);
			rawFrame = NULL;
		}

		NmCloseHandle(inputHandle);
		inputHandle = NULL;
    }
    else
    {		
        select_device(dev);
        if(err_flag != 0) {return;}

		adapterIndex = device[num_dev].index;

		/* Get the adapter info */
		response = NmGetAdapter(inputHandle, adapterIndex, &AdapterInfo);
		if(response != ERROR_SUCCESS)
		{sprintf_s(err_str,sizeof(err_str),"Error getting adapter info: 0x%X\n",response);err_flag=-1;return;}

		/* Configure the adapter */
		response = NmConfigAdapter(inputHandle, adapterIndex, theCallback, outputHandle, NmReturnRemainFrames);
		if(response != ERROR_SUCCESS)
		{sprintf_s(err_str,sizeof(err_str),"Error configuring the adapter: 0x%X\n",response);err_flag=-1;return;}

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
		{sprintf_s(err_str,sizeof(err_str),"Error starting capture: 0x%X\n",response);err_flag=-1;return;}

        /* DEBUG BEGIN */
        if(DEBUG_MODE)
        {
            if(num_dev>0)
            {
                fprintf(debug_log,"\nInitialize Device: %s\n",device[num_dev].description);
                fprintf(debug_log,"\nPromiscous: %i\tTimeout: %i\tMax Snap Length: %i\tMax Buffer Size: %i\n",promisc,timeout,maxSnapLen,maxBufferSize);
            }
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

		/* DEBUG BEGIN */
		if(DEBUG_MODE) {err_flag = fopen_s(&debug_log,"pktman.txt","w");}
		/* DEBUG END */

		return Py_BuildValue("i",DEBUG_MODE);
	}

	static PyObject *pktman_getdev(PyObject *self, PyObject *args)
	{
		int i=0;

		char build_string[202];

		char *dev=NULL;

		err_flag=0; strcpy_s(err_str,"No Error");

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

		strcpy_s(build_string,"{s:i,s:s,s:i");

		for(i=1; i<=tot_dev; i++)
		{
			strcat_s(build_string,",s:s,s:s");
		}

		strcat_s(build_string,"}");

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
		err_flag=0; strcpy_s(err_str,"No Error");

		PyArg_ParseTuple(args, "|i", &sniff_mode);

		if (sniff_mode >= 0)
		{
			Py_BEGIN_ALLOW_THREADS;
			gil_state = PyGILState_Ensure();

			sniffer();

			PyGILState_Release(gil_state);
			Py_END_ALLOW_THREADS;

			return Py_BuildValue("{s:i,s:s,s:i,s:S,s:S}","err_flag",err_flag,"err_str",err_str,"datalink",data_link,"py_pcap_hdr",py_pkt_header,"py_pcap_data",py_pkt_data);
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

	static PyObject *pktman_clear(PyObject *self)
	{
		err_flag=0; strcpy_s(err_str,"No Error");

		if (py_pkt_header != Py_None)
		{Py_CLEAR(py_pkt_header);}
		if (py_pkt_data != Py_None)
		{Py_CLEAR(py_pkt_data);}

		return Py_BuildValue("{s:i,s:s}","err_flag",err_flag,"err_str",err_str);
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

			/* DEBUG BEGIN */
			if(DEBUG_MODE) {fclose(debug_log);}
			/* DEBUG END */
		}
		else
		{sprintf_s(err_str,sizeof(err_str),"Error stopping capture: 0x%X\n",response);err_flag=-1;}

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
		{ "clear", (PyCFunction)pktman_clear, METH_NOARGS, NULL},
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
