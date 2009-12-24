#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
sys.path.append("../")
from pyndk.reactor import Reactor
from pyndk.event_handler import EventHandler, CONNECT_MASK, READ_MASK
from pyndk.connector import Connector
from pyndk.svc_handler import SvcHandler
import time

opened_port = []
closed_port = []
count = 0
class HttpConnection(SvcHandler):
    def __init__(self, addr):
        SvcHandler.__init__(self)
        self._addr = addr
        self._ok = False
        self._sock = None

    def open(self, arg):
        opened_port.append(self._addr)
        self._ok = True
        self._sock = self.get_peer()
        #self._sock.setblocking(False)
        self.get_reactor().register_handler(self.get_handle(), self, READ_MASK)
        try:
            self._sock.send("GET /xxx HTTP/1.1\r\nHost: 192.168.1.100:8000\r\n\r\n")
        except: pass
        return True

    def handle_input(self, handle):
        data = self._sock.recv(1024)
        print(data)
        return False

    def handle_close(self, handle, mask):
        if not self._ok:
            closed_port.append(self._addr)
        if len(closed_port) + len(opened_port) == count:
            print("opened port : %s" % opened_port)
            #print("closed port : %s" % closed_port)
            sys.exit(0)
import threading
class AsyncConnect(threading.Thread):
    def __init__(self, ip, ports):
        threading.Thread.__init__(self)
        self._ip = ip
        self._ports = ports

    def run(self):
        time.sleep(1)
        for p in self._ports:
            g_connector.connect(HttpConnection((self._ip, p)), (self._ip, p), 3)
if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("./port_scanner.py ip port_range(1024-65535)")
        sys.exit(0)
    g_connector = Connector()

    g_reactor = Reactor()
    #g_reactor = Reactor('select')
    if not g_reactor.open():
        print("reactor open failed")

    g_connector.open(g_reactor)

    (p1, p2) = sys.argv[2].split('-')
    count = int(p2) - int(p1) + 1
    #for p in list(range(int(p1), int(p2) + 1)):
    #    g_connector.connect(HttpConnection((sys.argv[1], p)), (sys.argv[1], p), 5)
    ports = list(range(int(p1), int(p2) + 1))
    ac = AsyncConnect(sys.argv[1], ports[:int(len(ports)/2)])
    ac.start()
    ac = AsyncConnect(sys.argv[1], ports[int(len(ports)/2):])
    ac.start()
    import sys
    while True:
        if not g_reactor.handle_events():
            print("reactor error")
            sys.exit(0)
