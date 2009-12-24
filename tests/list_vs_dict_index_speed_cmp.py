import datetime
from collections import deque

## dict
l = {}
for i in range(8192):
    l[i] = i

before = datetime.datetime.now()
for i in range(10):
    a = 0
    for i in range(8192):
        a += l[i]
after = datetime.datetime.now()
#print "dict escape %d.%d sec", (after.second - before.second, after.microsecond - before.microsecond)
print("dict escape %d.%d sec", (after.second - before.second, after.microsecond - before.microsecond))

## dict
l = {}
for i in range(8192):
    l[i] = i

before = datetime.datetime.now()
for i in range(10):
    a = 0
    for i in range(8192):
        a += l[i]
after = datetime.datetime.now()
#print "dict escape %d.%d sec", (after.second - before.second, after.microsecond - before.microsecond)
print("dict escape %d.%d sec", (after.second - before.second, after.microsecond - before.microsecond))

## deque
l = deque(list(range(8192)))
before = datetime.datetime.now()
for i in range(10):
    a = 0
    for i in range(8192):
        a += l[i]

after = datetime.datetime.now()
#print "deque escape %d.%d sec", (after.second - before.second, after.microsecond - before.microsecond)
print("deque escape %d.%d sec", (after.second - before.second, after.microsecond - before.microsecond))

## deque
l = deque(list(range(8192)))
before = datetime.datetime.now()
for i in range(10):
    a = 0
    for i in range(8192):
        a += l[i]

after = datetime.datetime.now()
#print "deque escape %d.%d sec", (after.second - before.second, after.microsecond - before.microsecond)
print("deque escape %d.%d sec", (after.second - before.second, after.microsecond - before.microsecond))

## list
l = list(range(8192))

before = datetime.datetime.now()
for i in range(10):
    a = 0
    for i in range(8192):
        a += l[i]

after = datetime.datetime.now()
#print "list escape %d.%d sec", (after.second - before.second, after.microsecond - before.microsecond)
print("list escape %d.%d sec", (after.second - before.second, after.microsecond - before.microsecond))

## list
l = list(range(8192))

before = datetime.datetime.now()
for i in range(10):
    a = 0
    for i in range(8192):
        a += l[i]

after = datetime.datetime.now()
#print "list escape %d.%d sec", (after.second - before.second, after.microsecond - before.microsecond)
print("list escape %d.%d sec", (after.second - before.second, after.microsecond - before.microsecond))
