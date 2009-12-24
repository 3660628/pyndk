import datetime

l = [x%2 for x in range(1000000)]

before = datetime.datetime.now()
for j in range(10):
    for i in l:
        if i: pass

after = datetime.datetime.now()
#print "int escape %d.%d sec", (after.second - before.second, after.microsecond - before.microsecond)
print("list escape %d.%d sec", (after.second - before.second, after.microsecond - before.microsecond))

l = [(x%2 == 0 and True or False) for x in range(1000000)]

before = datetime.datetime.now()
for j in range(10):
    for i in l:
        if i: pass
after = datetime.datetime.now()
#print "dict escape %d.%d sec", (after.second - before.second, after.microsecond - before.microsecond)
print("dict escape %d.%d sec", (after.second - before.second, after.microsecond - before.microsecond))
