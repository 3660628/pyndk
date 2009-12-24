import datetime
from heapq import heappush, heappop

class __test(object):
    pass

tnow = []
for i in range(10):
    tnow.append(datetime.datetime.now())

tnow.reverse()
hq = []
[heappush(hq, n) for n in tnow]

for n in hq:
    print hq.microsecond

#print tnow.microsecond

tnow = datetime.datetime.now()

#print tnow.microsecond

