
import sys

def round(X, Y):
    #return (((X) +((Y) - 1)) & (~((Y) - 1)))
    return X + (Y - X%Y)

print round(int(sys.argv[1]), int(sys.argv[2]))
