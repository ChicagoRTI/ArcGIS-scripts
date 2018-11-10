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


def log (message):
    common_functions.log(message)
    return

def fixup (tile_file_names_table):
    # Get the file file names
    fns = [fn[0] for fn in tile_file_names.read_file_names(tile_file_names_table)]
    fns_fixed = list()
    #loop through the name and rename
    count = 1
    arcpy.SetProgressor("step", "Checking files...", 0, len(fns), 1)
    for fn in fns:
        common_functions.log_progress ('Checking file for fixup', len(fns), count)    

        desc = arcpy.Describe(fn)        
        if '.' in desc.baseName:
            new_fn = desc.path + '/' + desc.baseName.replace('.', '_') + '.' + desc.extension
            try:
                os.rename(desc.catalogPath, new_fn)
                fns_fixed.append(new_fn)
            except:
                log ('Failed renaming ' + fn + ' to ' + new_fn)
        else:
            fns_fixed.append(fn)
        count += 1
    # Recreate the table of file names with the fixed up names
    tile_file_names.write_file_names(tile_file_names_table, fns_fixed)
        
        
if __name__ == '__main__':
    fixup(sys.argv[1])        