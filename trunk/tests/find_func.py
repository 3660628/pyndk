import sys
import datetime

before = datetime.datetime.now()
for i in range(10000000):
    s = sys.platform
after = datetime.datetime.now()
print("obj.func %d.%d sec", (after.second - before.second, after.microsecond - before.microsecond))

platform = sys.platform
before = datetime.datetime.now()
for i in range(10000000):
    s = platform
after = datetime.datetime.now()
print("func %d.%d sec", (after.second - before.second, after.microsecond - before.microsecond))

before = datetime.datetime.now()
for i in range(10000000):
    s = sys.platform
after = datetime.datetime.now()
print("obj.func %d.%d sec", (after.second - before.second, after.microsecond - before.microsecond))

platform = sys.platform
before = datetime.datetime.now()
for i in range(10000000):
    s = platform
after = datetime.datetime.now()
print("func %d.%d sec", (after.second - before.second, after.microsecond - before.microsecond))

