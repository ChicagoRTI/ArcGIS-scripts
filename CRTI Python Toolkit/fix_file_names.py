# -*- coding: utf-8 -*-
"""
Created on Mon Sep 17 23:03:34 2018

@author: Don
"""
# To run from Spyder iPython console:
#    runfile('D:/CRTI/python_projects/ArcGIS-scripts/CRTI Python Toolkit/fix_file_names.py', wdir='D:/CRTI/python_projects/ArcGIS-scripts/CRTI Python Toolkit', args="'C:/Users/Don/Documents/ArcGIS/scratch.gdb/tile_file_names'")

# The original files had periods in the file name which caused arcpy Describe to 
# not recognize them as shape files. Copy the bad files to the 'renamed'
# directory then run this to fix up the names

import os
import sys
import common_functions
common_functions.add_arcgis_to_sys_path()
import arcpy
import tile_file_names

dir = 'D:/CRTI/GIS data/will_county_tree_crowns_sample/test'

def log (message):
    common_functions.log(message)
    return

def fixup (tile_file_names_table):
    # Get the file file names
    fns = tile_file_names.read_file_names(tile_file_names_table)
    #loop through the name and rename
    count = 1
    for fn in fns:
        if count % ((len(fns)/100)+1) == 0:
            log('Checking file for fixup ' + str(count) + ' of ' + str(len(fns)))

        desc = arcpy.Describe(fn)        
        if '.' in desc.baseName:
            new_fn = desc.path + '/' + desc.baseName.replace('.', '_') + '.' + desc.extension
            try:
                os.rename(desc.catalogPath, new_fn)
            except:
                log ('Failed renaming ' + fn + ' to ' + new_fn)
        count += 1
        
        
if __name__ == '__main__':
    fixup(sys.argv[1])        