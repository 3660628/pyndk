
class Test(object):
    def __init__(self, n):
        self.number = n
    def clone(self, n):
        return self.__class__(n)

def func(cls):
    return cls.__class__(10)

o = func(Test(0))
print o.number, id(o)

t = Test(11)
print 't id = %d', id(t)
o = t.clone(20)
print 'o id = %d', id(o)
o = t.clone(20)
print 'o id = %d', id(o)
print o.number
