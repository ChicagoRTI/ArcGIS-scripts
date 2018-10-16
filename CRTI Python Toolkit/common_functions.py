# -*- coding: utf-8 -*-



import time
import os
import sys

__arc_gis_dir = "C:\\Program Files (x86)\\ArcGIS\\Desktop10.6\\"
__arc_gis_path = [__arc_gis_dir + "bin",
                __arc_gis_dir + "ArcPy",
                __arc_gis_dir + "ArcToolBox\Scripts"]
for p in __arc_gis_path: 
    if p not in sys.path: sys.path += [p]


def add_arcgis_to_sys_path ():
    __arc_gis_dir = "C:\\Program Files (x86)\\ArcGIS\\Desktop10.6\\"
    __arc_gis_path = [__arc_gis_dir + "bin",
                    __arc_gis_dir + "ArcPy",
                    __arc_gis_dir + "ArcToolBox\Scripts"]
    for p in __arc_gis_path: 
        if p not in sys.path: sys.path += [p]

import arcpy

def log (message):
    message = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ": " + str(os.getpid()) + ": " + message
    print (message)
    sys.stdout.flush()
    arcpy.AddMessage(message)
    
def log_mp (log_file, message):
    # Log the message to both a file and stdout.  Note that collisions may occur when logging to a
    # file from multiple processes and logging to stdout when running from a spawned processor
    # does not work on windows
    message = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ": " + str(os.getpid()) + ": " + message
    log_file = open(log_file, "a+", 0)
    log_file.write(message + '\n')
    log_file.close()
 #   print (message)
 #   sys.stdout.flush()
    arcpy.AddMessage(message)
    
    
def get_install_path():
    return sys.exec_prefix  

def step_header (step_count, step_total, message, inputs, outputs):
    log('')
    log('')
    log('==================================================')
    log('')
    log(message)
    log('')
    for m in inputs:
        log('Input : ' + m)
    for m in outputs:
        log('Output: ' + m)
    log('')
    log('Step ' + str(step_count) + ' of ' + str(step_total))
    log('--------------------------------------------------')
