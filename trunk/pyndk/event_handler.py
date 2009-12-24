# -*- coding: utf-8 -*-

"""
Author    : shaovie@gmail.com
Summary   : ...
"""

# event mask
NULL_MASK       = 0 << 0
READ_MASK       = 1 << 1
WRITE_MASK      = 1 << 2
EXCEPT_MASK     = 1 << 3
ACCEPT_MASK     = 1 << 4
CONNECT_MASK    = 1 << 5
TIMER_MASK      = 1 << 6

# For epoll
EDGE_MASK       = 1 << 20

ALL_EVENTS_MASK =        \
        READ_MASK       |\
        WRITE_MASK      |\
        EXCEPT_MASK     |\
        ACCEPT_MASK     |\
        CONNECT_MASK    |\
        TIMER_MASK      |\
        EDGE_MASK

DONT_CALL       = 1 << 31

class EventHandler(object):
    """
    Base class of event handler.
    """

    def __init__(self):
        """
        Must be construct.
        """
        self._reactor = None

    def handle_input(self, handle = None):
        """
        Called by Reactor when <handle> is readable.
        """
        return False

    def handle_ouput(self, handle = None):
        """
        Called by Reactor when <handle> is writeable.
        """
        return False

    def handle_exception(self, handle = None):
        """
        Called by Reactor when <handle> is exceptable.
        """
        return False

    def handle_timeout(self, curr_time, arg = None):
        """
        Called by Reactor when timer expires.
        <arg> was passed in when <schedule_timer> was invoked.
        Reactor will cancel this timer when return False, and 
        handle_close will be called after that.
        """
        return False

    def handle_close(self, handle = None, close_mask = 0):
        """
        Called when a <handle_*()> method returns False or when the
        <remove_handler> method is called on Reactor. The <close_mask> 
        indicates which event has triggered the <handle_close> method 
        callback on a particular <handle>.
        If <close_mask> equals TIMER_MASK then <handle> is 'arg' which 
        was passwd in when <schedule_timer> was invoked.
        """
        return True

    def get_reactor(self):
        """
        Return Reactor.
        """
        return self._reactor
    def set_reactor(self, reactor):
        """
        Set Reactor.
        """
        self._reactor = reactor

    def get_handle(self):
        """
        Return HANDLE
        Should be overwrote.
        """
        return None

    def set_handle(self, h):
        """
        Reset HANDLE
        Should be overwrote.
        """
        pass

    # endof `class EventHandler(object)'

