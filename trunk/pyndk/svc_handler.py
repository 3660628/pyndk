# -*- coding: utf-8 -*-

"""
Author    : shaovie@gmail.com
Summary   : ...
"""
try:
    from socket import AF_INET, fromfd
except:
    from socket import AF_INET
from pyndk.event_handler import EventHandler, READ_MASK, DONT_CALL, ALL_EVENTS_MASK

class SvcHandler(EventHandler):
    """
    This class provides a well-defined interface that the Acceptor and 
    Connector pattern factories use as their target. Typically, client 
    applications will subclass SvcHandler and do all the interesting 
    work in the subclass.
    """
    def __init__(self):
        """
        """
        EventHandler.__init__(self)
        self._peer = None

    def open(self, arg):
        """
        """
        try:
            return self.get_reactor().register_handler(self.get_handle(),
                                                       self,
                                                       READ_MASK)
        except Exception as e:
            print("Pyndk-> svc handler::open : [%s]" % e)
            return False
        return True

    def close(self, mask):
        return self.handle_close(None, mask)

    def set_remote_addr(self, addr):
        """
        Called by Acceptor framework when accept a new passive connection and pass
        "remote addr" to <addr>, so subclass should implement this interface to 
        store <addr>.
        """
        pass

    def get_remote_addr(self):
        """
        Just an interface.
        """
        pass

    def set_peer(self, peer):
        """
        <peer> is a socket object.
        """
        self._peer = peer

    def get_peer(self):
        return self._peer

    def handle_close(self, handle, mask):
        """
        Remove all of events that be related on this <SvcHandler> 
        from Reactor.
        """
        r = self.get_reactor()
        peer = self.get_peer()
        if r and peer:
            r.remove_handler(self.get_handle(), ALL_EVENTS_MASK | DONT_CALL)
            r.cancel_timer(self)

        try: peer.close()
        except: pass

        return True

    def get_handle(self):
        try: return self.get_peer().fileno()
        except: return None

    def set_handle(self, handle):
        try: 
            self.set_peer(fromfd(handle, AF_INET))
        except Exception as e: 
            print("Pyndk-> set handle [%s]" % e)


