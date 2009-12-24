#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
sys.path.append("../")
from pyndk.reactor import Reactor
from pyndk.event_handler import EventHandler, CONNECT_MASK, READ_MASK, ALL_EVENTS_MASK, TIMER_MASK
from pyndk.connector import Connector
from pyndk.svc_handler import SvcHandler
import threading
try:
    from queue import Queue
except:
    from Queue import Queue
from urllib.parse import urlparse
import time

g_total_count = 0
statist_lock = threading.Lock() 
begin_time = 0
ok_count = 0
err_count = 0
class HttpConnection(SvcHandler):
    def __init__(self, task):
        SvcHandler.__init__(self)
        self._sock = None
        self._task = task
        self._ok = False

    def open(self, arg):
        self._ok = True
        self._sock = self.get_peer()
        #self._sock.setblocking(False)
        if self.get_reactor().register_handler(self.get_handle(), self, READ_MASK):
            self._task.put(self)
            return True
        return False

    def handle_input(self, handle):
        data = self._sock.recv(1024)
        #if len(data) == 0:
        #    return False
        return False

    def handle_close(self, handle, mask):
        self.get_peer().close()
        global ok_count, err_count, g_total_count
        if mask == TIMER_MASK: 
            print("timer close %d" % id(self))
            return True
        with statist_lock:
            if self._ok:
                ok_count += 1
            else:
                err_count += 1
            if ok_count + err_count >= g_total_count:
                print("%d request ok!" % ok_count)
                print("%d request failed!" % err_count)
                print("speed = %f reqs/sec" % (ok_count / (time.time() - begin_time)))
        return True

class AsyncIO(threading.Thread):
    def __init__(self, c, r):
        threading.Thread.__init__(self)
        self._reactor = r
        self._msg_queue = Queue()
        self._connector = c

    def run(self):
        while True:
            item = self._msg_queue.get()
            if type(item) == tuple:
                self._connector.connect(HttpConnection(self), item, 5)
            else:
                try:
                    item.get_peer().send(b"GET / HTTP/1.1\r\nHost: 192.168.1.100:8000\r\n\r\n")
                except Exception as e:
                    print("send failed: %s" % e)
                    self._reactor.remove_handler(item, ALL_EVENTS_MASK)
    def put(self, item):
        self._msg_queue.put(item)

class Scheduler(threading.Thread):
    def __init__(self, tasks, threads):
        threading.Thread.__init__(self)
        self._tasks = tasks
        self._threads = threads
        global g_total_count
        self._requests = g_total_count

    def run(self):
        u = urlparse(sys.argv[3])
        itor = 0
        count = int(self._requests/self._threads)
        c, n = 0, 0
        for task in self._tasks:
            c += 1
            end = itor + count
            if c == self._threads: 
                end = self._requests
            for i in range(itor, end):
                task.put((u.hostname, u.port))
                n += 1
                if n > self._requests: 
                    return None
            itor += count
        print("post %d jobs" % n)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("ab.py 10(concurrency) 10000(requests) http://127.0.0.1:8000/")
        sys.exit(0)
    g_reactor = Reactor()
    if not g_reactor.open(): 
        print("reactor open failed") 
    g_connector = Connector()
    g_connector.open(g_reactor)

    threads = int(sys.argv[1])
    g_total_count = int(sys.argv[2])
    tasks = []
    for i in range(threads):
        task = AsyncIO(g_connector, g_reactor)
        task.start()
        tasks.append(task)
    begin_time = time.time()
    s  = Scheduler(tasks, threads)
    s.start()
    while True:
        if not g_reactor.handle_events():
            print("reactor error")
