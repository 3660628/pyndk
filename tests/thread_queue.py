import threading
import time

class Consumer(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)
        self._queue = []

    def run(self):
        while True:
            with self._lock:
                self._cond.wait()
                print("consume one %d" % self._queue.pop(0))
    def put(self, n):
        with self._lock:
            self._queue.append(n)
            self._cond.notify()
            print("product one %d" % n)

g_consumer = Consumer()
g_consumer.start()
class Producter(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(sefl):
        n = 1
        while True:
            time.sleep(1)
            g_consumer.put(n)
            n += 1

p = Producter()
p.start()
time.sleep(10000000)
