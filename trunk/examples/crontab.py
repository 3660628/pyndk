#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
sys.path.append("../")
from pyndk.reactor import Reactor
from pyndk.event_handler import EventHandler
from datetime import datetime

class Crontab(EventHandler):
    def __init__(self):
        EventHandler.__init__(self)

    def handle_timeout(self, current_time, arg):
        print("%s called in %s" % (arg, current_time))
        return True

    def handle_close(self, arg, flag):
        print("%s closed" % arg)

if __name__ == '__main__':

    g_reactor = Reactor()
    if not g_reactor.open():
        print("reactor open failed")

    # crontab
    entry = "2-10 2-10 23-7/2 * mon-/2"
    print("%s" % entry)
    print("%s timerid = %d" % ('=' * 30, g_reactor.crontab(Crontab(), entry, entry)))

    entry = "45-10/2 * 23-7/2 * mon-/2"
    print("%s" % entry)
    print("%s timerid = %d" % ('=' * 30, g_reactor.crontab(Crontab(), entry, entry)))

    entry = "12/2 */2 23-30/2 4-10/2,11/2,12- 2,4,7"
    print("%s" % entry)
    print("%s timerid = %d" % ('=' * 30, g_reactor.crontab(Crontab(), entry, entry)))

    entry = "30-10/2 * * * *"
    print("%s" % entry)
    print("%s timerid = %d" % ('=' * 30, g_reactor.crontab(Crontab(), entry, entry)))

    entry = "*/2 */2 * * *"
    print("%s" % entry)
    print("%s timerid = %d" % ('=' * 30, g_reactor.crontab(Crontab(), entry, entry)))

    entry = "* * * * *"
    print("%s" % entry)
    print("%s timerid = %d" % ('=' * 30, g_reactor.crontab(Crontab(), entry, entry)))

    entry = "0 4-6 * * sun"
    print("%s" % entry)
    print("%s timerid = %d" % ('=' * 30, g_reactor.crontab(Crontab(), entry, entry)))
    while True:
        if not g_reactor.handle_events(): 
            sys.exit(0)
