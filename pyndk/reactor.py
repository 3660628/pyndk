# -*- coding: utf-8 -*-

"""
Author    : shaovie@gmail.com
Summary   : ...
"""

import os, sys
from threading import Lock, RLock
from threading import Condition
try:
    from _thread import get_ident as current_thread
except:
    from thread import get_ident as current_thread

from errno import EINTR
from pyndk.event_handler import EventHandler, READ_MASK, WRITE_MASK, EXCEPT_MASK, \
                          ACCEPT_MASK, CONNECT_MASK, EDGE_MASK, ALL_EVENTS_MASK, \
                          DONT_CALL, NULL_MASK
from pyndk.timer_queue import TimerQueue
from time import time
from collections import deque

from select import select, error as select_error
if sys.platform == 'linux2':
    try:
        from select import epoll, EPOLLIN, EPOLLOUT, EPOLLPRI, EPOLLERR, EPOLLHUP
    except: 
        try:
            from select import poll, POLLIN, POLLOUT, POLLPRI, POLLERR, POLLHUP
        except: pass
elif sys.platform[:-1] == 'freebsd':
    from select import kqueue 

if sys.version_info[0] == 3:
    notify_data = b'x'
else:
    notify_data = 'x'
pipe_read  = os.read
pipe_write = os.write

##
class ReactorNotify(EventHandler):
    """
    Event handler used for unblocking the epoll_reactor from its event 
    loop.
    This event handler is used internally by the epoll_reactor as a 
    means to allow a thread other then the one running the event loop 
    to unblock the event loop.
    """
    def __init__(self):
        EventHandler.__init__(self)
        self._read_handle  = -1
        self._write_handle = -1
        self._notify_lock = Lock()

    def open(self):
        """
        """
        if sys.platform != 'win32':
            import fcntl
            self._read_handle, self._write_handle = os.pipe()
            flags = fcntl.fcntl(self._read_handle, fcntl.F_GETFL, 0)
            flags = flags | os.O_NONBLOCK
            fcntl.fcntl(self._read_handle, fcntl.F_SETFL, flags)

            flags = fcntl.fcntl(self._write_handle, fcntl.F_GETFL, 0)
            flags = flags | os.O_NONBLOCK
            fcntl.fcntl(self._write_handle, fcntl.F_SETFL, flags)

            fcntl.fcntl(self._read_handle, fcntl.F_SETFD, fcntl.FD_CLOEXEC)
            fcntl.fcntl(self._write_handle, fcntl.F_SETFD, fcntl.FD_CLOEXEC)

            self.get_handle = self._unix_get_handle
            self.handle_input = self._unix_handle_input
            self.close = self._unix_close
            self.notify = self._unix_notify
        else:
            import socket
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
                sock.bind(('', 0))
                sock.listen(5)
                port = sock.getsockname()[1]

                self._write_handle = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
                self._write_handle.connect(('127.0.0.1', port))
                self._read_handle, addr = sock.accept()
                sock.close()
                self._read_handle.setblocking(False)
                self._write_handle.setblocking(False)

                self.get_handle = self._win32_get_handle
                self.handle_input = self._win32_handle_input
                self.close = self._win32_close
                self.notify = self._win32_notify
            except Exception as e:
                print("Pyndk-> win32 socketpair: [%s]" % e)
                return False
        return True

    def _unix_get_handle(self):
        return self._read_handle

    def _win32_get_handle(self):
        return self._read_handle.fileno()

    def _unix_close(self):
        with self._notify_lock:
            os.close(self._read_handle)
            os.close(self._write_handle)
            self._read_handle, self._write_handle = -1, -1

    def _win32_close(self):
        with self._notify_lock:
            self._read_handle.close()
            self._write_handle.close()
            self._read_handle, self._write_handle = -1, -1

    def _unix_handle_input(self, handle):
        with self._notify_lock:
            pipe_read(self._read_handle, 4)
        return True

    def _win32_handle_input(self, handle):
        with self._notify_lock:
            self._read_handle.recv(4)
        return True

    def _unix_notify(self):
        with self._notify_lock:
            pipe_write(self._write_handle, notify_data)
        return True

    def _win32_notify(self):
        with self._notify_lock:
            self._write_handle.send(notify_data)
        return True

class TokenEntry(object):
    def __init__(self, lock, thr_id):
        self._thr_id = thr_id
        self._cond = Condition(lock)
    
    def wait(self):
        self._cond.wait()

    def notify(self):
        self._cond.notify()

## Token
class Token(object):
    """
    Used for reactor under multi-thread.
    """
    def __init__(self, r):
        """
        """
        self._lock = Lock()
        self._reactor = r
        self._nesting_level = 0
        self._owner = 0
        self._entry_queue = []

    def acquire(self, notify = False):
        with self._lock:
            thr_id = current_thread()
            if not self._owner:
                self._owner = thr_id
            elif thr_id == self._owner:
                self._nesting_level += 1
            else:
                if notify: self._reactor.notify()
                entry = TokenEntry(self._lock, thr_id)
                self._entry_queue.append(entry)
                while True:
                    entry.wait()
                    if self._owner == entry._thr_id:
                        break
                self._entry_queue.pop(0)

    def release(self):
        with self._lock:
            if self._nesting_level > 0:
                self._nesting_level -= 1
            elif not self._entry_queue:
                self._owner = 0
            else:
                self._owner = self._entry_queue[0]._thr_id
                self._entry_queue[0].notify()

class TokenNull(object):
    def __init__(self, r):
        pass

    def acquire(self, notify = False):
        pass

    def release(self):
        pass

_MAX_REACTOR_PROCESS_FDS_ONE_TIME = 256

ADD_MASK = 0x911
MOD_MASK = 0x912
CLR_MASK = 0x913

class Reactor(object):
    def __init__(self, select_type = 'any', thread_safe = True):
        """
        Constructor.
        """
        # init member vars.
        self._max_size = -1
        self._event_fd = None
        self._handler_rep = None
        self._notify_handler = None
        self._timer_queue = TimerQueue(self)

        self._payload = 0
        self._payload_lock = Lock()

        self._select_type = select_type
        self._thread_safe = thread_safe

        if self._thread_safe:
            self._token = Token(self)
        else:
            self._token = TokenNull(self)
        self._token_released = False

        self._activated = False

    def open(self, max_size = -1):
        """
        Initialize the EpollReactor.
        @note On Unix platforms, the <max_size> parameter should 
        be as large as the maximum number of file descriptors 
        allowed for a given process.  This is necessary since 
        a file descriptor is used to directly index the array 
        of event handlers maintained by the Reactor's handler 
        repository.  Direct indexing is used for efficiency 
        reasons.  If <max_size> parameter is <= 0, then Reactor 
        will set `ulimit -n` to <max_size>
        """
        self._token.acquire()
        try:
            self._max_size = max_size

            if self._max_size <= 0 and sys.platform != 'win32':
                self._max_size = os.sysconf('SC_OPEN_MAX')

            if self._max_size <= 0 and sys.platform != 'win32':
                return False

            self._events   = []
            self._handler_rep = [[None, 0] for i in range(self._max_size)]
            
            if self._select_type == 'any':
                if sys.platform == 'linux2':
                    try:
                        n = EPOLLIN
                        self._select_type = 'epoll'
                    except:
                        try:
                            n = POLLIN
                            self._select_type = 'poll'
                        except:
                            self._select_type = 'select'
                elif sys.platform[:-1] == 'freebsd':
                    self._select_type = 'kqueue'
                elif sys.platform == 'win32':
                    self._select_type = 'select'
                elif sys.platform == 'sunos5':
                    self._select_type = 'poll'
                else:
                    self._select_type = 'select'

            ## 
            # Special platform method.
            if self._select_type == 'epoll':
                self._event_fd = epoll(self._max_size)
                self._dispatch_io_event = self._epoll_dispatch_io_event
                self._reactor_mask_to_os_event = self._reactor_mask_to_epoll_event
                self._find_handle = self._unix_find_handle
                self._handle_is_invalid = self._unix_handle_is_invalid
                self._unbind_handle = self._unix_unbind_handle
                self._event_mask = self._unix_event_mask
                self._set_event_mask = self._set_unix_event_mask
            elif self._select_type == 'kqueue':
                self._event_fd = kqueue()
                self._dispatch_io_event = self._kqueue_dispatch_io_event
                self._reactor_mask_to_os_event = self._reactor_mask_to_kqueue_event
                self._find_handle = self._unix_find_handle
                self._handle_is_invalid = self._unix_handle_is_invalid
                self._unbind_handle = self._unix_unbind_handle
                self._event_mask = self._unix_event_mask
                self._set_event_mask = self._set_unix_event_mask
            elif self._select_type == 'poll':
                self._event_fd = poll()
                self._dispatch_io_event = self._poll_dispatch_io_event
                self._reactor_mask_to_os_event = self._reactor_mask_to_poll_event
                self._find_handle = self._unix_find_handle
                self._handle_is_invalid = self._unix_handle_is_invalid
                self._unbind_handle = self._unix_unbind_handle
                self._event_mask = self._unix_event_mask
                self._set_event_mask = self._set_unix_event_mask
            elif self._select_type == 'select' and sys.platform == 'win32':
                if self._max_size <= 0:
                    self._max_size = 512 # Python-x.x.x/Modules/selectmodule.c defined.
                self._handler_rep = {}  # {socket:[ehandler, mask]}
                self._event_fd = Selector(self._max_size)
                self._dispatch_io_event = self._select_dispatch_io_event
                self._reactor_mask_to_os_event = self._reactor_mask_to_select_event
                self._find_handle = self._win32_find_handle
                self._handle_is_invalid = self._win32_handle_is_invalid
                self._unbind_handle = self._win32_unbind_handle
                self._event_mask = self._win32_event_mask
                self._set_event_mask = self._set_win32_event_mask
            elif self._select_type == 'select' and sys.platform != 'win32':
                if self._max_size <= 0:
                    self._max_size = 1024 # Unix platform default defined.
                self._handler_rep = [[None, 0] for i in range(self._max_size)]
                self._event_fd = Selector(self._max_size)
                self._dispatch_io_event = self._select_dispatch_io_event
                self._reactor_mask_to_os_event = self._reactor_mask_to_select_event
                self._find_handle = self._unix_find_handle
                self._handle_is_invalid = self._unix_handle_is_invalid
                self._unbind_handle = self._unix_unbind_handle
                self._event_mask = self._unix_event_mask
                self._set_event_mask = self._set_unix_event_mask
            else:
                print("Pyndk-> Unsupport platform or select type [%s]!" % self._select_type)
                return False

            if not self._thread_safe:
                # Optimization
                self.handle_events = self._handle_events_unsafe
                self.register_handler = self._register_handler_unsafe
                self.remove_handler = self._remove_handler_unsafe
                self.schedule_timer = self._schedule_timer_unsafe
                self.crontab = self._crontab_unsafe
                self.reset_timer_interval = self._reset_timer_interval_unsafe
                self.cancel_timer = self._cancel_timer_unsafe
                self.payload = self._payload_unsafe
                self.deactivated = self._deactivated_unsafe
                self.activated = self._activated_unsafe

            if not self._event_fd:
                return False

            # Optimization
            self._event_poll = self._event_fd.poll
            self._event_register = self._event_fd.register
            self._event_unregister = self._event_fd.unregister
            self._event_modify = self._event_fd.modify

            # Notify
            self._notify_handler = ReactorNotify()
            self._notify_handler.open()
            if not self._register_handler_i(self._notify_handler.get_handle(), 
                                            self._notify_handler, 
                                            READ_MASK):
                self._close()
                return False
            self._activated = True
            return True
        finally:
            self._token.release()

    def close(self):
        """
        Close Reactor and release system resource.
        """
        self._token.acquire(True)
        try:
            self._close()
        finally:
            self._token.release()
    def deactivated(self, flag = False):
        """
        Activate or deactivate reactor.
        """
        self._token.acquire(True)
        try:
            self._activated = flag
        finally:
            self._token.release() 

    def activated(self):
        self._token.acquire()
        try:
            return self._activated
        finally:
            self._token.release()

    def lock(self):
        return self._token

    def reactor_event_loop(self):
        while True:
            if not self.handle_events():
                break

    def handle_events(self, timeout = -1):
        """
        <timeout> is in milliseconds (as float) which identify demultiplex 
        driver will be blocked. On -1 will block until some <fd> activated.
        """
        self._token.acquire()
        self._token_released = False
        if not self._activated: return False
        try:
            return self._handle_events_i(timeout)
        finally:
            if not self._token_released: self._token.release()
    
    # Register and remove Handlers.
    #
    def register_handler(self, handle, ehandler, event_mask):
        """
        Register handler for I/O events.
        A handler can be associated with multiple handles. A handle
        cannot be associated with multiple handlers.
        """
        try:
            ehandler.set_reactor(self)
        except: return False
        self._token.acquire(True)
        try:
            if self._payload >= self._max_size:
                return False
            return self._register_handler_i(handle, ehandler, event_mask)
        finally:
            self._token.release()

    def remove_handler(self, handle, event_mask):
        """
        Remove <event_mask> from <handle> registration.
        """
        self._token.acquire(True)
        try:
            return self._remove_handler_i(handle, event_mask)
        finally:
            self._token.release()

    # Timer management.
    #
    def schedule_timer(self, ehandler, arg, delay, interval = 0.0):
        """
        Schedule a timer.
        Return a timer id (non-negative integeron successfully, return -1 on
        failed.
        """
        try:
            ehandler.set_reactor(self)
        except: pass
        self._token.acquire(True)
        try:
            return self._timer_queue.schedule(ehandler, arg, delay, interval)
        finally:
            self._token.release()

    def crontab(self, ehandler, arg, entry):
        """
        Schedule a crontab timer.
        Return a timer id (non-negative integeron successfully, return -1 on
        failed.
        """
        try:
            ehandler.set_reactor(self)
        except: pass
        self._token.acquire(True)
        try:
            return self._timer_queue.crontab(ehandler, arg, entry)
        finally:
            self._token.release()

    def reset_timer_interval(self, timer_id, interval):
        """
        Resets the interval of the timer represented by <timer_id> to
        <interval>.
        """
        # token
        self._token.acquire(True)
        try:
            if type(timer_id) != int:
                timer_id = self._timer_queue.get_timerid_by_handler(timer_id)
            return self._timer_queue.reset_interval(timer_id, interval)
        finally:
            self._token.release()

    def cancel_timer(self, timer_id, dont_call_handle_close = True):
        """
        Cancel timer associated with <timer_id> that was returned from
        the schedule_timer() or crontab() method.
        On successful cancellation EventHandler::handle_close() will 
        be called with TIMER_MASK if <dont_call_handle_close> is False.

        <timer_id> can be EventHandler instance.
        """
        self._token.acquire(True)
        try:
            if type(timer_id) != int:
                timer_id = self._timer_queue.get_timerid_by_handler(timer_id)
            return self._timer_queue.cancel(timer_id, dont_call_handle_close)
        finally:
            self._token.release()

    ## Noitfy
    def notify(self):
        self._notify_handler.notify()

    def payload(self):
        self._token.acquire()
        try:
            return self._payload
        finally:
            self._token.acquire.release()

    #################################################################
    # Implementation methods
    # 
    #################################################################
    def _close(self):
        if self._event_fd:
            self._event_fd.close()
            self._event_fd = None
        if self._notify_handler:
            self._notify_handler.close()
            self._notify_handler = None
        self._max_size  = -1

    def _handle_events_unsafe(self, timeout = -1):
        """
        Not thread-safe.
        """
        if not self._activated: return False
        if not self._events:  # empty
            while True:
                try:
                    ret_val = self._poll_events(timeout)
                    if ret_val: break
                except OSError as e:
                    if e.args[0] == EINTR:
                        continue
                    print("Pyndk-> %s" % e)
                    err = True
                except IOError as e:
                    if e.args[0] == EINTR:
                        continue
                    print("Pyndk-> %s" % e)
                    err = True
                except Exception as e:
                    if e.args[0] == EINTR:
                        continue
                    print("Pyndk-> %s" % e)
                    err = True
            if not ret_val and err:
                return False
        # Dispatch timer handler
        self._timer_queue.expire()

        #Dispatch IO event
        self._dispatch_io_event()
        return True

    def _handle_events_i(self, timeout):
        """
        """
        if not self._events:  # empty
            while True:
                try:
                    ret_val = self._poll_events(timeout)
                    if ret_val: break
                except OSError as e:
                    if e.args[0] == EINTR:
                        continue
                    print("Pyndk-> %s" % e)
                    err = True
                except IOError as e:
                    if e.args[0] == EINTR:
                        continue
                    print("Pyndk-> %s" % e)
                    err = True
                except Exception as e:
                    if e.args[0] == EINTR:
                        continue
                    print("Pyndk-> %s" % e)
                    err = True
            if not ret_val and err:
                return False

        # Dispatch timer handler
        self._timer_queue.expire()

        #Dispatch IO event
        self._dispatch_io_event()
        self._token.release()
        self._token_released = True
        return True

    def _poll_events(self, timeout):
        wait_time = self._timer_queue.calculate_timeout(timeout)
        if (wait_time != -1 and timeout == -1) \
                or (wait_time != -1 and timeout != -1 and wait_time != timeout):
            timers_pending = True
        else:
            timers_pending = False
        #print("wait time = %f" % (wait_time))
        self._events = self._event_poll(wait_time)

        if (not self._events) and (not timers_pending): return False
        return True

    #################################################################
    # Platform special dispatcher
    #
    def _epoll_dispatch_io_event(self):
        """
        Dispatch the activated events.
        """
        result = 0
        events = self._events
        find_func = self._find_handle
        handler_rep = self._handler_rep
        remove_handler_i = self._remove_handler_i
        while events and result < _MAX_REACTOR_PROCESS_FDS_ONE_TIME:
            #event = events.popleft()
            event = events.pop(0)
            mask = event[1]
            if find_func(event[0]):
                if mask & EPOLLIN:
                    result += 1
                    mask &= (~EPOLLIN)
                    if not handler_rep[event[0]][0].handle_input(event[0]):
                        remove_handler_i(event[0], READ_MASK)
                elif mask & EPOLLOUT:
                    result += 1
                    mask &= (~EPOLLOUT)
                    if not handler_rep[event[0]][0].handle_output(event[0]):
                        remove_handler_i(event[0], WRITE_MASK)
                elif mask & EPOLLPRI:
                    result += 1
                    mask &= (~EPOLLPRI)
                    if not handler_rep[event[0]][0].handle_except(event[0]):
                        remove_handler_i(event[0], EXCEPT_MASK)
                elif mask & (EPOLLHUP | EPOLLERR):
                    result += 1
                    mask &= (~(EPOLLHUP | EPOLLERR))
                    remove_handler_i(event[0], ALL_EVENTS_MASK)
            # end of `if self._find_handle(event[0])'
            else:
                continue
            if mask != 0:
                events.append((event[0], mask))

        # end of `while self._events and result ...'

    def _poll_dispatch_io_event(self):
        """
        Dispatch the activated events.
        """
        result = 0
        events = self._events
        find_func = self._find_handle
        handler_rep = self._handler_rep
        remove_handler_i = self._remove_handler_i
        while events and result < _MAX_REACTOR_PROCESS_FDS_ONE_TIME:
            event = events.pop()
            mask = event[1]
            if find_func(event[0]):
                if mask & POLLIN:
                    result += 1
                    mask &= (~POLLIN)
                    if not handler_rep[event[0]][0].handle_input(event[0]):
                        remove_handler_i(event[0], READ_MASK)
                elif mask & POLLOUT:
                    result += 1
                    mask &= (~POLLOUT)
                    if not handler_rep[event[0]][0].handle_output(event[0]):
                        remove_handler_i(event[0], WRITE_MASK)
                elif mask & POLLPRI:
                    result += 1
                    mask &= (~POLLPRI)
                    if not handler_rep[event[0]][0].handle_except(event[0]):
                        remove_handler_i(event[0], EXCEPT_MASK)
                elif mask & (POLLHUP | POLLERR):
                    result += 1
                    mask &= (~(POLLHUP | POLLERR))
                    remove_handler_i(event[0], ALL_EVENTS_MASK)
            # end of `if self._find_handle(event[0])'
            else:
                continue
            if mask != 0:
                events.append((event[0], mask))

        # end of `while self._events and result ...'
    def _kqueue_dispatch_io_event(self):
        pass

    def _select_dispatch_io_event(self):
        """
        Dispatch the activated events.
        """
        (rd_events, wr_events, ex_events) = self._events
        find_func = self._find_handle
        handler_rep = self._handler_rep
        remove_handler_i = self._remove_handler_i
        for fd in rd_events:
            if find_func(fd):
                if not handler_rep[fd][0].handle_input(fd):
                    remove_handler_i(fd, READ_MASK)
        for fd in wr_events:
            if find_func(fd):
                if not handler_rep[fd][0].handle_output(fd):
                    remove_handler_i(fd, WRITE_MASK)
        for fd in ex_events:
            if find_func(fd):
                if not handler_rep[fd].handle_except(fd):
                    remove_handler_i(fd, EXCEPT_MASK)

        self._events = None

    def _register_handler_unsafe(self, handle, ehandler, event_mask):
        """
        Not thread-safe.
        """
        try:
            ehandler.set_reactor(self)
        except: 
            raise (ValueError, "ehandler should override 'set_reactor' method.")
        return self._register_handler_i(handle, ehandler, event_mask)
    
    def _register_handler_i(self, handle, handler, event_mask):
        if self._handle_is_invalid(handle):
            return False
        if not self._find_handle(handle):
            self._bind_handle(handle, handler, event_mask)
            events = self._reactor_mask_to_os_event(event_mask)
            try:
                self._event_register(handle, events)
            except IOError as e:
                print("Pyndk-> register : [%s]" % e)
                self._unbind_handle(handle)
                return False
            self._payload += 1
        else:
            self._mask_opt(handle, event_mask, ADD_MASK)
        return True

    def _remove_handler_unsafe(self, handle, event_mask):
        """
        Not thread-safe.
        """
        return self._remove_handler_i(handle, event_mask)

    def _remove_handler_i(self, handle, event_mask):
        if type(handle) != int:
            handle = handle.get_handle()
        eh = self._find_handle(handle)
        if not eh: 
            return False
        self._mask_opt(handle, event_mask, CLR_MASK)
        if not (event_mask & DONT_CALL):
            eh[0].handle_close(handle, event_mask)

        if self._event_mask(handle) == NULL_MASK:
            self._unbind_handle(handle)
            self._payload -= 1
        return True

    def _schedule_timer_unsafe(self, ehandler, arg, delay, interval = 0.0):
        """
        Not thread-safe.
        """
        try:
            ehandler.set_reactor(self)
        except: pass
        return self._timer_queue.schedule(ehandler, arg, delay, interval)

    def _crontab_unsafe(self, ehandler, arg, entry):
        """
        Not thread-safe.
        """
        try:
            ehandler.set_reactor(self)
        except: pass
        return self._timer_queue.crontab(ehandler, arg, entry)
    
    def _reset_timer_interval_unsafe(self, timer_id, interval):
        """
        Not thread-safe.
        """
        if type(timer_id) != int:
            timer_id = self._timer_queue.get_timerid_by_handler(timer_id)
        return self._timer_queue.reset_interval(timer_id, interval)

    def _cancel_timer_unsafe(self, timer_id, dont_call_handle_close = True):
        """
        Not thread-safe.
        """
        if type(timer_id) != int:
            timer_id = self._timer_queue.get_timerid_by_handler(timer_id)
        return self._timer_queue.cancel(timer_id, dont_call_handle_close)
    
    def _payload_unsafe(self):
        """
        Not thread-safe.
        """
        return self._payload

    def _deactivated_unsafe(self, flag = False):
        """
        Not thread-safe.
        """
        self._activated = flag

    def _activated_unsafe(self):
        """
        Not thread-safe.
        """
        return self._activated

    def _mask_opt(self, handle, mask, opt):
        new_mask = self._event_mask(handle)
        if opt == ADD_MASK:
            new_mask |= mask
        elif opt == MOD_MASK:
            new_mask = mask
        elif opt == CLR_MASK:
            new_mask &= ~mask

        self._set_event_mask(handle, new_mask)
        if new_mask == NULL_MASK:
            self._event_unregister(handle)
            return True
        else:
            new_mask = self._reactor_mask_to_os_event(new_mask)
            try:
                self._event_modify(handle, new_mask)
            except Exception as e:
                print("Pyndk-> modify : [%s]" % e)
        return True

    def _reactor_mask_to_select_event(self, mask):
        return mask

    def _reactor_mask_to_epoll_event(self, mask):
        events = NULL_MASK
        if mask & READ_MASK:
            events |= EPOLLIN
        if mask & EDGE_MASK:
            events |= EPOLLET
        if mask & ACCEPT_MASK:
            events |= EPOLLIN
        if mask & CONNECT_MASK:
            events |= EPOLLIN|EPOLLOUT
        if mask & WRITE_MASK:
            events |= EPOLLOUT
        if mask & EXCEPT_MASK:
            events |= EPOLLPRI
        return events

    def _reactor_mask_to_poll_event(self, mask):
        events = NULL_MASK
        if mask & READ_MASK:
            events |= POLLIN
        if mask & ACCEPT_MASK:
            events |= POLLIN
        if mask & CONNECT_MASK:
            events |= POLLIN|POLLOUT
        if mask & WRITE_MASK:
            events |= POLLOUT
        if mask & EXCEPT_MASK:
            events |= POLLPRI
        return events

    def _reactor_mask_to_kqueue_event(self, mask):
        pass

    def _unix_handle_is_invalid(self, handle):
        return handle < 0

    def _win32_handle_is_invalid(self, handle):
        return handle == None

    def _unix_find_handle(self, handle):
        if self._handler_rep[handle][1] == 0 or not self._handler_rep[handle][0]:
            return None
        return self._handler_rep[handle]

    def _win32_find_handle(self, handle):
        return self._handler_rep.get(handle, None)

    def _unix_event_mask(self, handle):
        return self._handler_rep[handle][1]

    def _win32_event_mask(self, handle):
        try: return self._handler_rep[handle][1]
        except: return 0

    def _set_unix_event_mask(self, handle, new_mask):
        self._handler_rep[handle][1] = new_mask

    def _set_win32_event_mask(self, handle, new_mask):
        try: self._handler_rep[handle][1] = new_mask
        except: self._handler_rep[handle] = [None, new_mask]

    def _bind_handle(self, handle, ehandler, event_mask):
        self._handler_rep[handle] = [ehandler, event_mask]

    def _unix_unbind_handle(self, handle):
        self._handler_rep[handle] = [None, 0]

    def _win32_unbind_handle(self, handle):
        try:
            del self._handler_rep[handle]
        except: pass

    def _incre_payload(self, count = 1):
        self._payload += count

    def _decre_payload(self, count = 1):
        self._payload -= count

class Selector(object):
    """
    """
    def __init__(self, size):
        self._rdlist = []
        self._wrlist = []
        self._exlist = []

    def register(self, fd, eventmask):
        if eventmask == READ_MASK:
            self._rdlist.append(fd)
        elif eventmask == ACCEPT_MASK:
            self._rdlist.append(fd)
        elif eventmask == WRITE_MASK:
            self._wrlist.append(fd)
        elif eventmask == EXCEPT_MASK:
            self._exlist.append(fd)
        elif eventmask == CONNECT_MASK:
            self._rdlist.append(fd)
            self._wrlist.append(fd)
        else:
            raise (IOError, "invalid event mask")
        
    def unregister(self, fd):
        if fd in self._rdlist:
            self._rdlist.remove(fd)
        if fd in self._wrlist:
            self._wrlist.remove(fd)
        if fd in self._exlist:
            self._exlist.remove(fd)

    def modify(self, handle, mask):
        pass

    def poll(self, timeout):
        if timeout <= -1.0: timeout = None
        result = ()
        while True:
            try:
                result = select(self._rdlist, self._wrlist, self._exlist, timeout)
            except select_error as e:
                print("Pyndk-> select : [%s]" % e)
                if e.args[0] == EINTR:
                    continue
            break    
        return result if len(result) > 0 else None

    def close(self):
        self._rdlist = None
        self._wrlist = None
        self._exlist = None
        
class KqueueAdapter(object):
    def __init__(self, size):
        pass
    def register(self, fd, eventmask):
        pass

    def unregister(self, fd):
        pass

    def modify(self, handle, mask):
        pass

    def poll(self, timeout):
        pass

    def close(self):
        pass 

