#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import argparse
import socket
import os
import sys
import struct
import time
import random
import traceback # useful for exception handling
import threading
# NOTE: Do not import any other modules - the ones above should be sufficient

def setupArgumentParser() -> argparse.Namespace:
        parser = argparse.ArgumentParser(
            description='A collection of Network Applications developed for SCC.203.')
        parser.set_defaults(func=ICMPPing, hostname='lancaster.ac.uk')
        subparsers = parser.add_subparsers(help='sub-command help')
        
        parser_p = subparsers.add_parser('ping', aliases=['p'], help='run ping')
        parser_p.set_defaults(timeout=2, count=10)
        parser_p.add_argument('hostname', type=str, help='host to ping towards')
        parser_p.add_argument('--count', '-c', nargs='?', type=int,
                              help='number of times to ping the host before stopping')
        parser_p.add_argument('--timeout', '-t', nargs='?',
                              type=int,
                              help='maximum timeout before considering request lost')
        parser_p.set_defaults(func=ICMPPing)

        parser_t = subparsers.add_parser('traceroute', aliases=['t'],
                                         help='run traceroute')
        parser_t.set_defaults(timeout=2, protocol='icmp')
        parser_t.add_argument('hostname', type=str, help='host to traceroute towards')
        parser_t.add_argument('--timeout', '-t', nargs='?', type=int,
                              help='maximum timeout before considering request lost')
        parser_t.add_argument('--protocol', '-p', nargs='?', type=str,
                              help='protocol to send request with (UDP/ICMP)')
        parser_t.set_defaults(func=Traceroute)
        
        parser_w = subparsers.add_parser('web', aliases=['w'], help='run web server')
        parser_w.set_defaults(port=8080)
        parser_w.add_argument('--port', '-p', type=int, nargs='?',
                              help='port number to start web server listening on')
        parser_w.set_defaults(func=WebServer)

        parser_x = subparsers.add_parser('proxy', aliases=['x'], help='run proxy')
        parser_x.set_defaults(port=8000)
        parser_x.add_argument('--port', '-p', type=int, nargs='?',
                              help='port number to start web server listening on')
        parser_x.set_defaults(func=Proxy)

        args = parser.parse_args()
        return args


class NetworkApplication:

    def checksum(self, dataToChecksum: bytes) -> int:
        csum = 0
        countTo = (len(dataToChecksum) // 2) * 2
        count = 0

        while count < countTo:
            thisVal = dataToChecksum[count+1] * 256 + dataToChecksum[count]
            csum = csum + thisVal
            csum = csum & 0xffffffff
            count = count + 2

        if countTo < len(dataToChecksum):
            csum = csum + dataToChecksum[len(dataToChecksum) - 1]
            csum = csum & 0xffffffff

        csum = (csum >> 16) + (csum & 0xffff)
        csum = csum + (csum >> 16)
        answer = ~csum
        answer = answer & 0xffff
        answer = answer >> 8 | (answer << 8 & 0xff00)

        answer = socket.htons(answer)

        return answer

    def printOneResult(self, destinationAddress: str, packetLength: int, time: float, seq: int, ttl: int, destinationHostname=''):
        if destinationHostname:
            print("%d bytes from %s (%s): icmp_seq=%d ttl=%d time=%.3f ms" % (packetLength, destinationHostname, destinationAddress, seq, ttl, time))
        else:
            print("%d bytes from %s: icmp_seq=%d ttl=%d time=%.3f ms" % (packetLength, destinationAddress, seq, ttl, time))

    def printAdditionalDetails(self, packetLoss=0.0, minimumDelay=0.0, averageDelay=0.0, maximumDelay=0.0):
        print("%.2f%% packet loss" % (packetLoss))
        if minimumDelay > 0 and averageDelay > 0 and maximumDelay > 0:
            print("rtt min/avg/max = %.2f/%.2f/%.2f ms" % (minimumDelay, averageDelay, maximumDelay))

    def printOneTraceRouteIteration(self, ttl: int, destinationAddress: str, measurements: list, destinationHostname=''):
        latencies = ''
        noResponse = True
        for rtt in measurements:
            if rtt is not None:
                latencies += str(round(rtt, 3))
                latencies += ' ms  '
                noResponse = False
            else:
                latencies += '* ' 

        if noResponse is False:
            print("%d %s (%s) %s" % (ttl, destinationHostname, destinationAddress, latencies))
        else:
            print("%d %s" % (ttl, latencies))

class ICMPPing(NetworkApplication):
    startTime = 0

    def receiveOnePing(self, icmpSocket, destinationAddress, ID, timeout):
        # 1. Wait for the socket to receive a reply
        timeleft = timeout
        icmpSocket.settimeout(timeleft)
        # 2. Once received, record time of receipt, otherwise, handle a timeout
        try:
            recPacket, addr = icmpSocket.recvfrom(2048)
        except socket.timeout:
            print("timeout")
            return
        receiveTime = (time.time() * 1000)
        # 3. Compare the time of receipt to time of sending, producing the total network delay
        networkDelay = receiveTime - self.startTime

        # 4. Unpack the packet header for useful information, including the ID
        
        header = struct.unpack("bbHHh", recPacket[20:28]) 

        # 5. Check that the ID matches between the request and reply
        receiveID = header[3]
        if ID != receiveID:
            print("Received ID does not equal to expected ID")
        # 6. Return total network delay
        return networkDelay
    
    
    def sendOnePing(self, icmpSocket, destinationAddress, ID):
        checksum = 0
        # 1. Build ICMP header
        icmpHeader = struct.pack("bbHHh", 8, 0, checksum, ID, 1)
        # 2. Checksum ICMP packet using given function
        checksum = NetworkApplication.checksum(self, icmpHeader)

        # 3. Insert checksum into packet
        icmpHeader = struct.pack("bbHHh", 8, 0, checksum, ID, 1)

        # 4. Send packet using socket
        packet = icmpHeader
        icmpSocket.sendto(packet, (destinationAddress, 1))
        # 5. Return time of sending
        return time.time()*1000
        

    def doOnePing(self, destinationAddress, packetID, seq_num, timeout):
        # 1. Create ICMP socket
        icmpSocket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)

        # 2. Call sendOnePing function
        self.startTime = self.sendOnePing(icmpSocket, destinationAddress, packetID)
        
        # 3. Call receiveOnePing function
        delay = self.receiveOnePing(icmpSocket, destinationAddress, packetID, timeout)

        # 4. Close ICMP socket
        icmpSocket.close()

        # 5. Print out the delay (and other relevant details) using the printOneResult method, below is just an example.
        #self.printOneResult(destinationAddress, 50, 20.0, 0, 150) # Example use of printOneResult - complete as appropriate
        self.printOneResult(destinationAddress, 50, delay, seq_num, 60)

        return delay

    def __init__(self, args):
        timeout = args.timeout
        packetID = os.getpid() & 0xFFFF  # Ensure packetID is within the valid range for a 16-bit number
        seq_num = 1  # Starting sequence number
        
        print('Ping to: %s...' % (args.hostname))

        for seq_num in range(1, (args.count or 4) + 1):
            delay = self.doOnePing(args.hostname, packetID, seq_num, timeout)
            print(f"Delay: {delay:.2f} ms")
            time.sleep(1)
            
        # 1. Look up hostname, resolving it to an IP address
        # 2. Repeat below args.count times
        # 3. Call doOnePing function, approximately every second, below is just an example
        
class Traceroute(NetworkApplication):
    MAX_HOPS = 30
    ICMP_ECHO_REQUEST = 8
    ICMP_TIME_EXCEEDED = 11
    UDP_DPORT = 33434  # destination port for UDP traceroute

    def __init__(self, args):
        self.destinationAddress = socket.gethostbyname(args.hostname)
        self.protocol = args.protocol.lower()
        self.timeout = args.timeout
        print(f'Traceroute to: {args.hostname} ({self.destinationAddress}), {self.protocol.upper()} protocol')

        icmpSocket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
        udpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) if self.protocol == "udp" else None
        
        for ttl in range(1, self.MAX_HOPS + 1):
            # Set TTL for the packets
            icmpSocket.setsockopt(socket.SOL_IP, socket.IP_TTL, ttl)
            # To store delay measurements
            delays = []
            # Take three measurements for each hop
            for _ in range(3):  
                try:
                    if self.protocol == "icmp":
                        self.icmp_echo(icmpSocket, ttl)
                    elif self.protocol == "udp":
                        udpSocket.setsockopt(socket.SOL_IP, socket.IP_TTL, ttl)
                        udpSocket.sendto(b"", (self.destinationAddress, self.UDP_DPORT))
                    start_time = time.time()
                    _, addr = icmpSocket.recvfrom(5120)
                    delays.append((time.time() - start_time) * 1000)
                except socket.timeout:
                    delays.append(None)
            
            try:
                hostname = socket.gethostbyaddr(addr[0])[0]
            except Exception:
                hostname = addr[0]
            
            self.printOneTraceRouteIteration(ttl, addr[0], delays, hostname)
            
            # Check if destination was reached
            if addr[0] == self.destinationAddress:
                break
        
        # Close sockets
        icmpSocket.close()
        if udpSocket:
            udpSocket.close()

    def icmp_echo(self, icmp_socket, ttl):
        # Process ID for identification
        pid = os.getpid() & 0xFFFF
        # Initial checksum
        checksum = 0
        header = struct.pack("bbHHh", self.ICMP_ECHO_REQUEST, 0, checksum, pid, ttl)
        # Compute checksum
        checksum = self.checksum(header)
        # Packet with checksum
        header = struct.pack("bbHHh", self.ICMP_ECHO_REQUEST, 0, checksum, pid, ttl)
        # Send packet
        icmp_socket.sendto(header, (self.destinationAddress, 1))
        
class WebServer(NetworkApplication):

    def handleRequest(tcpSocket):
        # 1. Receive request message from the client on connection socket
        # 2. Extract the path of the requested object from the message (second part of the HTTP header)
        # 3. Read the corresponding file from disk
        # 4. Store in temporary buffer
        # 5. Send the correct HTTP response error
        # 6. Send the content of the file to the socket
        # 7. Close the connection socket
        pass

    def __init__(self, args):
        print('Web Server starting on port: %i...' % (args.port))
        # 1. Create server socket
        # 2. Bind the server socket to server address and server port
        # 3. Continuously listen for connections to server socket
        # 4. When a connection is accepted, call handleRequest function, passing new connection socket (see https://docs.python.org/3/library/socket.html#socket.socket.accept)
        # 5. Close server socket

class Proxy(NetworkApplication):
    # Maximum length for HTTP request data
    MAX_REQUEST_LENGTH = 4096
    CACHE_DIR = "cache"

    def __init__(self, args):
        print('Web Proxy starting on port: %i...' % (args.port))
        # Create a TCP socket for the proxy server
        self.tcpSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Allows the socket to be reused immediately after it's closed
        self.tcpSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Bind the socket to listen to the specified port
        self.tcpSocket.bind(("", args.port))
        self.tcpSocket.listen(5)
        # Ensures the cache directory exists, create if it doesn't
        if not os.path.exists(self.CACHE_DIR):
            os.makedirs(self.CACHE_DIR)
        try:
            while True:
                clientConnect, client_addr = self.tcpSocket.accept()
                threading.Thread(target=self.handleRequest, args=(clientConnect,)).start()
        finally:
            self.tcpSocket.close()

    def handleRequest(self, clientConnect):
        # Handles incoming client connections and serves content either from cache or fetches it
        # Receive the HTTP request from the client
        request = clientConnect.recv(self.MAX_REQUEST_LENGTH).decode()
        # Extract the URL from the HTTP request
        url = self.url(request)
        hostname = self.hostname(url)
        # Extract the hostname which is used as the cache file name
        cachedFile = os.path.join(self.CACHE_DIR, hostname)

        if os.path.exists(cachedFile):
            print("Serving from cache:", cachedFile)
            with open(cachedFile, 'rb') as f:
                clientConnect.sendall(f.read())
        else:
            self.cache(clientConnect, url, cachedFile)
        # Close the connection once the response is sent
        clientConnect.close()

    def url(self, request):
        # extracts and returns the url from the first line of the HTTP
        first_line = request.split('\n')[0]
        url = first_line.split(' ')[1]
        http_pos = url.find("://")
        # Strip the protocol if (http://) from the url is present
        if http_pos != -1:
            url = url[(http_pos+3):]
        return url

    def hostname(self, url):
        portPos = url.find(":")
        webserverPos = url.find("/")
        if webserverPos == -1:
            webserverPos = len(url)
        hostname = url[:webserverPos]
        return hostname

    def cache(self, clientConnect, url, cachedFile):
        # connects to the webserver gets the content and caches it and sends to client
        webserver, port = self.port(url)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((webserver, port))
        s.sendall(("GET / HTTP/1.1\r\nHost: " + webserver + "\r\n\r\n").encode())

        with open(cachedFile, 'wb') as cache_file:
            while True:
                data = s.recv(self.MAX_REQUEST_LENGTH)
                if not data:
                    break
                cache_file.write(data)
                clientConnect.sendall(data)

    def port(self, url):
        # determining the webserver address and port from url
        portPos = url.find(":")
        webserverPos = url.find("/")
        if webserverPos == -1:
            webserverPos = len(url)
        webserver = url[:webserverPos]
        # default port for url
        port = 80
        if portPos != -1:
            port = int(url[portPos+1:webserverPos])
        return webserver, port

    
# Do not delete or modify the code below
if __name__ == "__main__":
    args = setupArgumentParser()
    args.func(args)