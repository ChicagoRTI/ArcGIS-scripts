# -*- coding: utf-8 -*-
"""
Created on Tue Oct 02 17:29:41 2018

@author: Don
"""

import multiprocessing
import time

GLOBALLOCK = multiprocessing.Lock()

data = (
    ['a', '2'], ['b', '4'], ['c', '6'], ['d', '8'],
    ['e', '1'], ['f', '3'], ['g', '5'], ['h', '7']
)

def mp_worker((inputs, the_time)):
    GLOBALLOCK.acquire()
    print " Processs %s\tWaiting %s seconds" % (inputs, the_time)
    GLOBALLOCK.release()
    time.sleep(int(the_time))
    print " Process %s\tDONE" % inputs

def mp_handler():
    print "I Made it here"
    p = multiprocessing.Pool(8)
    p.map(mp_worker, data)
    p.close()

if __name__ == '__main__':
    mp_handler()