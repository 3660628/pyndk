# -*- coding: utf-8 -*-

"""
Author    : shaovie@gmail.com
Summary   : ...
"""

from errno import EINPROGRESS, EWOULDBLOCK
from socket import socket, SOL_SOCKET, SO_RCVBUF, AF_INET, SOCK_STREAM
from pyndk.event_handler import EventHandler, CONNECT_MASK, DONT_CALL, ALL_EVENTS_MASK, TIMER_MASK

class Connector(EventHandler):
    """
    Connection framework.
    """

    def __init__(self):
        """
        """
        EventHandler.__init__(self)

    def open(self, r):
        """
        """
        if not r: return False
        self.set_reactor(r)
        return True
    
    def connect(self, svc_handler, remote_addr, 
                timeout = 0, rcvbuf_size = 0, 
                local_addr = None, nonblocking = True):
        """
        """
        svc_handler.set_reactor(self.get_reactor())
        sock = self._shared_open(rcvbuf_size, local_addr)
        if not sock: 
            svc_handler.close(CONNECT_MASK)
        else:
            try:
                self._nonblock_connect(sock, svc_handler, \
                        remote_addr, timeout, nonblocking)
            except IOError as e:
                print("Pyndk-> nonblock connect : [%s]" % e)
                svc_handler.close(CONNECT_MASK)

    def _shared_open(self, rcvbuf_size, local_addr):
        """
        """
        sock = None
        try: 
            sock = socket(AF_INET, SOCK_STREAM, 0)
            if rcvbuf_size > 0:
                sock.setsockopt(SOL_SOCKET, SO_RCVBUF, rcvbuf_size)
            if local_addr:
                sock.bind(local_addr)
        except IOError as e: 
            print("Pyndk-> create socket : [%s]" % e)
            if sock:
                sock.close()
                sock = None
        return sock

    def _nonblock_connect(self, sock, sh, remote_addr, timeout, nonblocking):
        """
        """
        if timeout >= 0: sock.setblocking(False)
        err = sock.connect_ex(remote_addr)
        sh.set_peer(sock)
        r = self.get_reactor()
        if err == EINPROGRESS:
            nonb_connect = NonBlockingConnectHandler(sh, nonblocking)
            nonb_connect.set_reactor(r)
            r.lock().acquire(True)
            try:
                # Register to Reactor
                if not r.register_handler(sock.fileno(),
                                          nonb_connect,
                                          CONNECT_MASK):
                    sh.close(CONNECT_MASK)
                    return False
                # Schedule timer.
                if timeout > 0.0:
                    timerid = r.schedule_timer(nonb_connect, None, timeout)
                    if timerid == -1:
                        r.remove_handler(sock.fileno(), CONNECT_MASK)
                        sh.close(CONNECT_MASK)
                        return False
                    else:
                        nonb_connect._timer_id = timerid
            finally:
                r.lock().release()
            return True
        elif err == 0:
            if nonblocking and timeout < 0:
                sock.setblocking(False)
            if not sh.open(self):
                sh.close(CONNECT_MASK)
            return True
        else:
            sh.close(CONNECT_MASK)
        return False

class NonBlockingConnectHandler(EventHandler):
    """
    """
    def __init__(self, svc_handler, nonblocking):
        """
        """
        EventHandler.__init__(self)
        self._timer_id = -1
        self._svc_handler = svc_handler
        self._nonblocking = nonblocking

    def handle_input(self, handle):
        """
        Called by reactor when asynchronous connections fail.
        """
        ret = self.close(CONNECT_MASK)
        self._svc_handler.close(CONNECT_MASK)
        return ret

    def handle_output(self, handle):
        """
        """
        ret = self.close(CONNECT_MASK)
        if not self._nonblocking:
            self._svc_handler.get_peer().setblocking(True)
        if not self._svc_handler.open(None):
            self._svc_handler.close(CONNECT_MASK)
            self._svc_handler = None
        return ret

    def handle_timeout(self, curr_time, arg):
        """
        """
        ret = self.close(TIMER_MASK)
        self._svc_handler.close(TIMER_MASK)
        return ret
    
    def close(self, mask):
        ret = False
        try:
            if self._timer_id != -1:
                if mask != TIMER_MASK:
                    ret = self.get_reactor().cancel_timer(self._timer_id)
                    if not ret:
                        print("Pyndk-> cancel timer id [%d] failed" % self._timer_id)
                self._timer_id = -1
            else:
                print("Pyndk-> nonblocking's timerid == -1")
            ret = self.get_reactor().remove_handler(self._svc_handler.get_handle(),
                                                    ALL_EVENTS_MASK | DONT_CALL)
        except Exception as e: 
            print("Pyndk-> nonblocking object'close : [%s]" % e)
            ret = False
        return ret

