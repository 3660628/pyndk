#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
sys.path.append("../")
from pyndk.reactor import Reactor
from pyndk.event_handler import EventHandler, CONNECT_MASK, READ_MASK, ALL_EVENTS_MASK, TIMER_MASK
from pyndk.connector import Connector
from pyndk.acceptor import Acceptor
from pyndk.svc_handler import SvcHandler
import threading
import socket
import errno

class Echo(SvcHandler):
    def __init__(self, type = 'server'):
        SvcHandler.__init__(self)
        self._sock = None
        self._bytes_to_send = 0
        self._send_bytes = 0
        self._buffer = None
        self._type = type
   
    def open(self, arg):
        self._sock = self.get_peer()
        if not self.get_reactor().register_handler(self.get_handle(), self, READ_MASK):
            print("register read mask failed")
            return False
        if self._type == 'client' and self.get_reactor().schedule_timer(self, None, 3, 3) == -1:
            print("schedule timer failed")
            return False
        return True

    def handle_input(self, handle):
        while True:
            try:
                data = self._sock.recv(32*1024)
                if not data:
                    print("peer closed")
                    return False
                if not self._buffer:
                    self._buffer = data
                else:
                    self._buffer += data 
            except socket.error as e:
                if e[0] == errno.EWOULDBLOCK:
                    break
                return False
        if self._type == 'server' and len(self._buffer) == 32*1024:
            self._send_bytes = 0
            while True:
                try:
                    self._send_bytes += self._sock.send(self._buffer)
                    if self._send_bytes == 1024*32:
                        self._buffer = None
                        self._send_bytes = 0
                        break
                except socket.error as e:
                    if e[0] == errno.EWOULDBLOCK:
                        self.get_reactor().register_handler(self.get_handle(), self, WRITE_MASK)
                    else:
                        print(e)
                        return False
        return True

    def handle_timeout(self, current_time, arg):
        if not self._buffer:
            self._buffer = 'x' * (32*1024)
            self._send_bytes = 0
        else:
            print("echo : %s", self._buffer[:16])
        while True:
            try:
                self._send_bytes += self._sock.send(self._buffer[self._send_bytes:])
                if self._send_bytes == len(self._buffer):
                    self._buffer = None
                    self._send_bytes = 0
                    break 
            except socket.error as e:
                if e[0] == errno.EWOULDBLOCK:
                    self.get_reactor().register_handler(self.get_handle(), self, WRITE_MASK)
                    return True
                break
        return True

    def handle_output(self, handle):
        while True:
            try:
                self._send_bytes += self._sock.send(self._buffer[self._send_bytes:])
                if self._send_bytes == len(self._buffer):
                    break
            except socket.error as e:
                if e[0] == errno.EWOULDBLOCK:
                    return True
                print(e)
                break
        self._buffer = None
        self._send_bytes = 0
        return False

    def handle_close(self, handle, mask):
        print("handle close")
        super(Echo, self).handle_close(handle, mask)

if __name__ == '__main__':
    g_reactor = Reactor()
    if not g_reactor.open():
        print("reactor open failed")
    
    if sys.argv[1] == 'server':
        g_acceptor = Acceptor(Echo)
        g_acceptor.open(("127.0.0.1", 8008), g_reactor)
    elif sys.argv[1] == 'client':
        g_connector = Connector()
        g_connector.open(g_reactor)
        g_connector.connect(Echo('client'), ("127.0.0.1", 8008), 5)

    g_reactor.reactor_event_loop()
