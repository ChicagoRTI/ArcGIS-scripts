import time
import numpy
cimport numpy


ctypedef numpy.int_t DTYPE_t


def do_calc_2(numpy.ndarray[DTYPE_t, ndim=1] arr):
    cdef int maxval
    cdef unsigned long long int total
    cdef int k
    cdef double t1, t2, t
    cdef int arr_shape = arr.shape[0]
    t1=time.time()
#    for k in arr:
#        total = total + k
    for k in range(arr_shape):
        total = total + arr[k]
    print ("Total =", total)
    
    t2=time.time()
    t = t2-t1
    print("%.20f" % t)


def do_calc_1(numpy.ndarray[DTYPE_t, ndim=1] arr):
    cdef int maxval
    cdef unsigned long long int total
    cdef int k
    cdef double t1, t2, t
    
    t1 = time.time()
    for k in arr:
        total = total + k
    print ("Total = ", total)
    
    t2 = time.time()
    t = t2 - t1
    print("%.20f" % t)


def run():
    
    
    # .0937
    arr = numpy.arange(100000000, dtype=numpy.int)
    do_calc_2(arr)    
    
    # # 12.31
    # arr = numpy.arange(100000000, dtype=numpy.int)
    # do_calc_1(arr)
    
    

    # # 11.93
    # cdef unsigned long long int maxval
    # cdef unsigned long long int total
    # cdef int k
    # cdef double t1, t2, t
    # cdef numpy.ndarray arr
    # maxval = 100000000
    # arr = numpy.arange(maxval)
    # t1 = time.time()
    # for k in arr:
    #     total = total + k
    # print ("Total =", total)
    # t2 = time.time()
    # t = t2 - t1
    # print("%.20f" % t)

    
    
    # # 26.56
    # total = 0
    # arr = numpy.arange(100000000)
    # t1 = time.time()
    # for k in arr:
    #     total = total + k
    # t2 = time.time()
    # print("Total = ", total)
    # print("start = %s" % str(t1))
    # print("end   = %s" % str(t2))
    # t = t2 - t1
    # print("%.20f" % t)
    # print("End")
    
    
    
    # cdef unsigned long long int maxval
    # cdef unsigned long long int total
    # cdef int k
    # cdef double t1, t2, t
    # cdef numpy.ndarray arr
    # maxval = 10000
    # arr = numpy.arange(maxval)
    # t1 = time.time()
    # for k in arr:
    #     total = total + k
    # print "Total =", total
    # t2 = time.time()
    # t = t2 - t1
    # print("%.20f" % t)
     
 
    
    
    
    
if __name__ == '__main__':
     run()
        