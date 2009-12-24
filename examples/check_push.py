#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os, socket
from time import time
sys.path.append("../")
from pyndk.reactor import Reactor
from pyndk.event_handler import EventHandler, CONNECT_MASK, READ_MASK, ALL_EVENTS_MASK, TIMER_MASK
from pyndk.connector import Connector
from pyndk.svc_handler import SvcHandler
try:
    from urllib.parse import urlparse
except:
    from urlparse import urlparse

logger = open("result.log", "wt")
def error(msg):
    global logger
    logger.write("[ERROR]" + msg + os.linesep)
    print("[ERROR]" + msg)

def rinfo(msg):
    global logger
    logger.write("[RINFO]" + msg + os.linesep)
    print("[RINFO]" + msg)

class RPCObject(SvcHandler):
    def __init__(self, fileid, addr, url):
        SvcHandler.__init__(self)
        self._sock = None
        self._connect_ok = False
        self._msg_buffer = None
        self._location = None
        self._recv_msg_ok = False
        self._addr = addr
        self._url = url
        self._fileid = fileid
        self._handle_ok = False
        self._recv_stream_bytes = 0
        self._to_recv_bytes = 0
        self._file_size = 0
        self._begin_time = time()

    def open(self, arg):
        self._connect_ok = True
        self._sock = self.get_peer()
        if not self.get_reactor().register_handler(self.get_handle(), 
                self, 
                READ_MASK):
            error("register [%d] failed!" % self.get_handle())
            return False
        self.get_reactor().schedule_timer(self, None, 10, 0)
        return self.send_request()

    def send_request(self):
        ret = urlparse(self._url)
        uri = ret.path
        if ret.query:
            uri += "?" + ret.query
        msg = "\r\n".join(["GET %s HTTP/1.0" % uri,
                "User-Agent: pyndk",
                "Connection: Keep-Alive",
                "\r\n"])
        try:
            self.get_peer().send(msg)
        except Exception as e:
            error("[%s] send message to [%s:%d] failed!" % (self.__class__.__name__,
                self._addr[0], self._addr[1]))
            return False
        return True

    def handle_timeout(self, current_time, arg):
        return self._handle_ok
    
    def handle_input(self, h):
        try:
            data = self._sock.recv(2048)
            if len(data) == 0:
                return False
            
        except socket.error as e:
            if e.args[0] == errno.EWOULDBLOCK:
                return True
            return False
        return self.handle_response(data)

    def handle_response(self, data):
        try:
            if not self._msg_buffer:
                self._msg_buffer = data
            else:
                self._msg_buffer += data

            pos = self._msg_buffer.find("\r\n\r\n")
            if pos == -1:
                return True
            self._recv_msg_ok = True
            if self.__class__.__name__ == "SCSInterface":
                if self._msg_buffer[9:12] != "200":
                    error("[%s][%s:%d] response code is not 200! [result = %s]" %
                            (self.__class__.__name__,
                                self._addr[0], 
                                self._addr[1],
                                self._msg_buffer[9:12]
                                )
                            )
                    return False
                self._recv_stream_bytes = len(self._msg_buffer) - pos - 4
                pos = self._msg_buffer.find("Content-Length")
                end = self._msg_buffer.find("\r\n", pos)
                pos += len("Content-Length: ")
                self._file_size = int(self._msg_buffer[pos:end])
                self._to_recv_bytes = self._file_size
                global g_recv_bytes
                if g_recv_bytes == 0:
                    self._to_recv_bytes = 8192*2

                self._handle_ok = True
                return True
            else:
                if self._msg_buffer[9:12] != "302":
                    error("[%s][%s:%d] response code is not 302! [result = %s]" % 
                            (self.__class__.__name__,
                                self._addr[0], 
                                self._addr[1],
                                self._msg_buffer[9:12]
                                )
                            )
                    return False
                location = self._msg_buffer.find("Location")
                if location == -1:
                    error("[%s][%s] not reurn location [%s]" % 
                            (self.__class__.__name__,
                                self._addr[0],
                                self._addr[1],
                                self._msg_buffer
                                )
                            )
                    return False
                self._handle_ok = True
                end = self._msg_buffer.find("\r\n", location)
                location += len("Location: ")
                self._location = self._msg_buffer[location:end]
            self.do_action()
        except Exception as e:
            error(str(e))
        return False

    def do_action(self):
        pass

    def handle_close(self, h, m):
        super(RPCObject, self).handle_close(h, m)
        done = False
        if not self._connect_ok:
            error("[%s][%s:%d] connect failed!" % 
                    (self.__class__.__name__,
                        self._addr[0],
                        self._addr[1]
                        )
                    )
            done = True
        elif not self._recv_msg_ok:
            error("[%s][%s:%d] response timeout!" % 
                    (self.__class__.__name__,
                        self._addr[0],
                        self._addr[1]
                        )
                    )
            done = True
        if self.__class__.__name__ == "SCSInterface":
            done = True
        elif not self._handle_ok:
            done = True
        if done:
            global g_done_task_num
            global g_active_task_num
            g_active_task_num -= 1
            g_done_task_num += 1
            if g_done_task_num == g_task_num:
                sys.exit(0)
                global logger
                logger.close()
            if g_active_task_num < 40:
                dispatch_task()
        return True
    
def parse_addr(url):
    ret = urlparse(url)
    if not ret.port: 
        return (ret.hostname, 80)
    return (ret.hostname, ret.port)

class PHPInterface(RPCObject):
    def __init__(self, fileid, addr, url):
        RPCObject.__init__(self, fileid, addr, url)

    def do_action(self):
        addr = parse_addr(self._location)
        con = SBSInterface(self._fileid, addr, self._location)
        g_connector.connect(con, addr, 4)
        return True

class SBSInterface(RPCObject):
    def __init__(self, fileid, addr, url):
        RPCObject.__init__(self, fileid, addr, url)

    def do_action(self):
        addr = parse_addr(self._location)
        con = SCSInterface(self._fileid, addr, self._location)
        g_connector.connect(con, addr, 4)
        return True

class SCSInterface(RPCObject):
    def __init__(self, fileid, addr, url):
        RPCObject.__init__(self, fileid, addr, url)

    def do_action(self):
        return True

    def handle_input(self, h):
        try:
            if self._recv_msg_ok:
                data = self._sock.recv(8192)
                if len(data) == 0:
                    return False
                self._recv_stream_bytes += len(data)
                if self._recv_stream_bytes >= self._to_recv_bytes:
                    rinfo("[%s] download ok from [%s:%d]! filesize [%d] escape %dsec" % 
                            (self._fileid, 
                                self._addr[0], 
                                self._addr[1], 
                                self._file_size,
                                time() - self._begin_time
                                )
                            )
                    return False
                return True
            else:
                data = self._sock.recv(2048)
                if len(data) == 0:
                    return False
                return self.handle_response(data)
            
        except socket.error as e:
            if e.args[0] == errno.EWOULDBLOCK:
                return True
            return False

g_active_task_num = 0
g_task_num = 0
g_done_task_num = 0
g_filelist = []
g_recv_bytes = 0
php_interface = ""

def dispatch_task():
    global g_active_task_num
    for i in range(10):
        try: fileid = g_filelist.pop(0)
        except: break
        #url = php_interface + "?url=" + fileid
        url = php_interface + "?" + fileid
        addr = parse_addr(php_interface)
        con = PHPInterface(fileid, addr, url)
        g_connector.connect(con, addr, 4)
        g_active_task_num += 1

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("check_push.py phpinterface filelist recvbytes(default is filesize)")
        sys.exit(1)
    
    php_interface = sys.argv[1]
    g_reactor = Reactor("any", False)
    if not g_reactor.open():
        print("reactor open failed")

    for line in open(sys.argv[2], "rt"):
        s = line.strip()
        if len(s) > 0: g_filelist.append(s);
    if len(sys.argv) == 4:
        g_recv_bytes = int(sys.argv[3])
    g_task_num = len(g_filelist)
    g_connector = Connector()
    g_connector.open(g_reactor)
    dispatch_task()
    while True:
        if not g_reactor.handle_events():
            print("reactor error")
            sys.exit(0)
