

import sys
import multiprocessing


import fs.logger
logger = fs.logger.get('fs_log')

_threads = multiprocessing.cpu_count()


import arcpy


def log (message):
    logger.info(message)


def log_progress (message, max_range, step_count, threads=1):
    arcpy.SetProgressorPosition()
    if step_count % (((max_range*_threads)/100)+1) == 0:
        log (message + ' (' + str(step_count) + ' of ' + str(max_range) + ')')    

    
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
        if arcpy.Exists(m) and (arcpy.Describe(m).dataType == 'ShapeFile' or arcpy.Describe(m).dataType == 'Table' or arcpy.Describe(m).dataType == 'FeatureClass'):
            m += ' (' + str(arcpy.GetCount_management(m)) + ' records)'
        log('Input : ' + str(m))
    for m in outputs:
        log('Output: ' + str(m))
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

def create_index (fn, fields, index_name):
    if (isOptimizable(fn)):
        if index_name not in [index.name for index in arcpy.ListIndexes(fn)]:
            log('Creating index ' + index_name + ' in ' + fn)  
            arcpy.AddIndex_management(fn, fields, index_name, 'UNIQUE', 'ASCENDING')
    return 