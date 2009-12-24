import datetime
from collections import deque

## list
before = datetime.datetime.now()
for i in range(10000):
    l = []
    for i in range(256):
        l.append(i)
    for i in range(256):
        l.pop()

after = datetime.datetime.now()
print("list escape %d.%d sec", (after.second - before.second, after.microsecond - before.microsecond))

## list
before = datetime.datetime.now()
for i in range(10000):
    l = []
    for i in range(256):
        l.append(i)
    for i in range(256):
        l.pop(0)

after = datetime.datetime.now()
print("list escape %d.%d sec", (after.second - before.second, after.microsecond - before.microsecond))
## list
before = datetime.datetime.now()
for i in range(10000):
    for i in range(256):
        l.append(i)
    l = deque(l)
    if type(l) != list:
        for i in range(256):
                l.popleft()

after = datetime.datetime.now()
print("list escape %d.%d sec", (after.second - before.second, after.microsecond - before.microsecond))

