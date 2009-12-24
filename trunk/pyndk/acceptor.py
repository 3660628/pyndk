# -*- coding: utf-8 -*-

"""
Author    : shaovie@gmail.com
Summary   : ...
"""

from pyndk.event_handler import EventHandler, ACCEPT_MASK, READ_MASK
import socket

class  Acceptor(EventHandler):
    """
    Asynchronize accept passive connection framework.
    """
    def __init__(self, svc_handler):
        """
        """
        EventHandler.__init__(self)
        self._svc_handler = svc_handler
        self._socket = None
        self._nonblocking = True

    def open(self, address, reactor, reuse_addr = True, rcvbuf_size = 0, 
             backlog = 1024, nonblocking = True):
        """
        """
        if not reactor or type(address) != tuple:
            return False

        self.set_reactor(reactor)
        self._nonblocking = nonblocking
        try:
            # Create new socket object.
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            self._socket.setblocking(False)

            # Set options
            if reuse_addr:
                self._socket.setsockopt(socket.SOL_SOCKET,
                                        socket.SO_REUSEADDR,
                                        1)
            if rcvbuf_size > 0:
                self._socket.setsockopt(socket.SOL_SOCKET, 
                                        socket.SO_RCVBUF, 
                                        rcvbuf_size)

            # Bind local address
            self._socket.bind(address)

            # Listen
            self._socket.listen(backlog)
        except IOError as e:
            print("Pyndk-> %s" % e)
            return False

        return reactor.register_handler(self.get_handle(),
                                        self,
                                        ACCEPT_MASK)

    def close(self):
        return self.handle_close(None, 0)

    def get_handle(self):
        return self._socket.fileno()

    # private method
    #
    def handle_input(self, handle = None):
        """
        Listen handle is readable. Acceptor create a new <svc_handler> 
        object and activate it. The method will accept new socket as 
        more as in once callback.
        """
        while True:
            # Create new object
            try:
                (new_sock, addr) = self._socket.accept()
            except:
                return True
            sh = self._svc_handler()
            sh.set_reactor(self._reactor)
            if self._nonblocking:
                new_sock.setblocking(False)
            sh.set_peer(new_sock)
            sh.set_remote_addr(addr)
            if not sh.open(self): sh.close(READ_MASK)
        return True

    def handle_close(self, handle, event_mask):
        """
        """
        r = self.get_reactor()
        if r and peer:
            r.remove_handler(self.get_handle(), ALL_EVENTS_MASK | DONT_CALL)
        self._socket.close()
        return True

