#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
sys.path.append("../")
from pyndk.reactor import Reactor
from pyndk.event_handler import EventHandler, READ_MASK
from pyndk.acceptor import Acceptor
from pyndk.svc_handler import SvcHandler
import socket
import errno
import datetime

class HttpConnection(SvcHandler):
    def __init__(self):
        SvcHandler.__init__(self)
        self._sock = None

    def open(self, arg):
        # 
        #print("new connection %s:%d" % (self._remote_addr[0], self._remote_addr[1]))

        self._sock = self.get_peer()
        self.get_reactor().register_handler(self.get_handle(), self, READ_MASK)
        return True

    def set_remote_addr(self, addr):
        self._remote_addr = addr

    def get_remote_addr(self):
        return self._remote_addr;

    def handle_input(self, handle):
        try:
            data = self._sock.recv(1024)
            if len(data) == 0:
                return False
            self._sock.send(b"HTTP/1.1 200 Ok\r\nDate: Wed, 09 Sep 2009 07:12:12 GMT\r\nServer: pyndk\r\nConnection: close\r\n\r\n")
        except socket.error as e:
            if e.args[0] == errno.EWOULDBLOCK:
                return True
            return False
        return False
    
class PrintTimer(EventHandler):
    def __init__(self):
        EventHandler.__init__(self)

    def handle_timeout(self, current_time, arg):
        print("now is %s" % datetime.datetime.now())
        print("expired time is %s" % current_time)
        return True

g_acceptor = Acceptor(HttpConnection)

g_reactor = Reactor(thread_safe = False)
if not g_reactor.open():
    print("reactor open failed")
g_acceptor.open(("127.0.0.1", 8000), g_reactor)

import threading
class AnotherReactor(threading.Thread):
    def __init__(self, port, type):
        threading.Thread.__init__(self)
        self._acceptor = Acceptor(HttpConnection)
        self._reactor = Reactor(select_type = type)
        if not self._reactor.open():
            print("reactor open failed")
        self._acceptor.open(("127.0.0.1", port), self._reactor)

    def run(self):
        while True:
            if not self._reactor.handle_events():
                break
        print("another reactor exit")

#if g_reactor.schedule_timer(PrintTimer(), None, 4.5, 2) < 0:
#    print("schedule timer failed")

#another = AnotherReactor(8001, 'poll')
#another.start()

#another = AnotherReactor(8002, 'select')
#another.start()
count = 0
import sys
while True:
    if not g_reactor.handle_events():
        sys.exit(0)
#    count += 1
#    if count > 200:
#       sys.exit(0)
