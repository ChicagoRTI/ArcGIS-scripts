# -*- coding: utf-8 -*-



import time
import os
import sys
import multiprocessing

_threads = multiprocessing.cpu_count()

def add_arcgis_to_sys_path ():
    __arc_gis_dir = "C:\\Program Files (x86)\\ArcGIS\\Desktop10.6\\"
    __arc_gis_path = [__arc_gis_dir + "bin",
                    __arc_gis_dir + "ArcPy",
                    __arc_gis_dir + "ArcToolBox\Scripts"]
    for p in __arc_gis_path: 
        if p not in sys.path: sys.path += [p]

add_arcgis_to_sys_path()

import arcpy

def log (message):
    message = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ": " + str(os.getpid()) + ": " + message
    # Log to a file in the scratch folder
    log_file = os.path.join(os.path.normpath(arcpy.env.scratchFolder), 'log.txt')
    log_file = open(log_file, "a+", 0)
    log_file.write(message + '\n')
    log_file.close()
    # Log to stdout (this is a hack to get output to the iPython console)
    if r'\ArcGIS' not in sys.executable:
        print (message)
        sys.stdout.flush()
    # Log to arcGIS
    arcpy.AddMessage(message)
    
def log_mp (log_file, message):
    # Log the message to both a file and arcGIS.  Note that collisions may occur when logging
    # from multiple processes. Logging to stdout when running from a spawned processor
    # does not work on windows
    message = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ": " + str(os.getpid()) + ": " + message 
    log_file = open(log_file, "a+", 0)
    log_file.write(message + '\n')
    log_file.close()
 #   print (message)
 #   sys.stdout.flush()
    arcpy.AddMessage(message)

def log_progress (message, max_range, step_count):
    if step_count % ((max_range/100)+1) == 0:
        log (message + ' (' + str(step_count) + ' of ' + str(max_range) + ')')

def log_progress_mp (log_file, message, max_range, step_count):
    if step_count % ((max_range/(100/_threads))+1) == 0:
        log_mp (log_file, message + ' (' + str(step_count) + ' of ' + str(max_range) + ')')

    
def get_install_path():
    return sys.exec_prefix  

def step_header (step_count, step_total, message, inputs, outputs):
    log('')
    log('')
    log('==================================================')
    log('Step ' + str(step_count) + ' of ' + str(step_total))
    log('')
    log(message)
    log('')
    for m in inputs:
        log('Input : ' + m)
    for m in outputs:
        log('Output: ' + m)
    log('')
    log('--------------------------------------------------')


def isOptimizable (fn):
    desc = arcpy.Describe(fn)
    return (desc.dataType == 'ShapeFile' or desc.dataType == 'Table' or desc.dataType == 'FeatureClass') and not desc.name.startswith('in_memory\\')
        

def move_to_in_memory (fn, temporary_assets):
    if (isOptimizable(fn)):
        log('Importing into in-memory shape file: ' + fn)
        in_mem_file = 'in_memory\\' + arcpy.Describe(fn).baseName
        if arcpy.Describe(fn).dataType == 'Table':
            arcpy.CopyRows_management(fn, in_mem_file)
        else:    
            arcpy.CopyFeatures_management(fn, in_mem_file)
        temporary_assets.append(in_mem_file)
        return in_mem_file
    else:
        return fn