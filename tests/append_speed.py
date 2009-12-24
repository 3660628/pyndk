import datetime
from collections import deque

## list
before = datetime.datetime.now()
for i in range(10):
    l = []
    for i in range(2000):
        l.append(i)
    for i in range(2000):
        l.pop(0)

after = datetime.datetime.now()
#print "list escape %d.%d sec", (after.second - before.second, after.microsecond - before.microsecond)
print("list escape %d.%d sec", (after.second - before.second, after.microsecond - before.microsecond))

## deque
before = datetime.datetime.now()
for i in range(10):
    l = deque()#maxlen = 2000)
    for i in range(2000):
        l.append(i)
    for i in range(2000):
        l.popleft()

after = datetime.datetime.now()
#print "deque escape %d.%d sec", (after.second - before.second, after.microsecond - before.microsecond)
print("deque escape %d.%d sec", (after.second - before.second, after.microsecond - before.microsecond))
