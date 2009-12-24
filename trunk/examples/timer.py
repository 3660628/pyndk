#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
sys.path.append("../")
from pyndk.reactor import Reactor
from pyndk.event_handler import EventHandler
from datetime import datetime
import time

class TimerTest(EventHandler):
    def __init__(self):
        EventHandler.__init__(self)
        self._count = 0
        self._reset = False

    def handle_timeout(self, current_time, arg):
        self._count += 1
        print("%s called in %s : %f" % (arg[0], time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(current_time)), current_time))
        if arg[1] == 'once':
            return False
        if self._count > 5 and arg[1] == 'reset' and not self._reset:
            if g_reactor.reset_timer_interval(self, 6):
                self._reset = True
                print("%s reset interval to %d" % (arg[0], 6))
        if self._count > 5 and arg[1] == 'cancel':
            if g_reactor.cancel_timer(self, False):
                print("%s canceled" % arg[0])
        return True

    def handle_close(self, arg, flag):
        print("%s closed" % arg[0])

if __name__ == '__main__':

    g_reactor = Reactor(thread_safe = False)
    if not g_reactor.open():
        print("reactor open failed")

    timerid = g_reactor.schedule_timer(TimerTest(), ('loop-20-0.2', 'loop'), 20, 0.2)
    if timerid < 0:
        print("schedule timer failed") 
    else:
        print("schedule %s in [%s] ok" % ('loop-20-0.2', datetime.now()))

    timerid = g_reactor.schedule_timer(TimerTest(), ('loop-4.5-2', 'loop'), 4.5, 2)
    if timerid < 0:
        print("schedule timer failed") 
    else:
        print("schedule %s in [%s] ok" % ('loop-4.5-2', datetime.now()))

    cancel_timerid = g_reactor.schedule_timer(TimerTest(), ('cancel-4.5-2', 'cancel'), 4.5, 2)
    if cancel_timerid < 0:
        print("schedule timer failed") 
    else:
        print("schedule %s in [%s] ok" % ('cancel-4.5-2', datetime.now()))

    timerid = g_reactor.schedule_timer(TimerTest(), ('once-4-2', 'once'), 4, 2)
    if timerid < 0:
        print("schedule timer failed") 
    else:
        print("schedule %s in [%s] ok" % ('once-4-2', datetime.now()))

    timerid = g_reactor.schedule_timer(TimerTest(), ('once-4', 'delay'), 4)
    if timerid < 0:
        print("schedule timer failed") 
    else:
        print("schedule %s in [%s] ok" % ('once-4', datetime.now()))

    reset_timerid = g_reactor.schedule_timer(TimerTest(), ('loop-reset-3-3', 'reset'), 3, 3)
    if reset_timerid < 0:
        print("schedule timer failed") 
    else:
        print("schedule %s in [%s] ok" % ('loop-reset-3-3', datetime.now()))

    count = 0
    reset = 0
    canceled  = 0
    import sys
    while True:
        if not g_reactor.handle_events(): 
            sys.exit(0)
