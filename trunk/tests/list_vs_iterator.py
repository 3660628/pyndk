import datetime

l = [(i, i) for i in range(1000000)]

before = datetime.datetime.now()
for j in range(1):
    for i in range(1000000):
        a = l.pop()
        
    l = []

if not l:
    print('ok')
after = datetime.datetime.now()
#print "int escape %d.%d sec", (after.second - before.second, after.microsecond - before.microsecond)
#print("list escape %d.%d sec", (after.second - before.second, after.microsecond - before.microsecond))
print("list escape %d.%d sec", ((after - before).seconds, (after - before).microseconds))#.second, (after - before).microsecond))

l = [(i, i) for i in range(1000000)]

it = iter(l)
before = datetime.datetime.now()
for j in range(1):
    for i in range(1000000):
        a = next(it)
    l = []
after = datetime.datetime.now()
#print "dict escape %d.%d sec", (after.second - before.second, after.microsecond - before.microsecond)
print("dict escape %d.%d sec", (after.second - before.second, after.microsecond - before.microsecond))
