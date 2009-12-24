
class Base(object):
    def __init__(self):
        print "base"

    def output(self):
        print id(self)

class Child(Base):
    def __init__(self):
        print "child"

    def output(self):
        print id(self)

def func(t):
    try:

        var = t()
        var.output()
        return True
    finally:
        print("finally")

func(Child)

import sys
sys.exit(0)

if hasattr(c, 'output'):
    print 'ok'

a = func
import types

if type(a) == types.FunctionType:
    print 'is function'

if issubclass(Child, Base):
    print "is subclass"

if type(Child) == object:
    print "is object"

if callable(c):
    print 'instance callable'

if callable(Base):
    print 'object callable'

if callable(a):
    print 'func callable'
