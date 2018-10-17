# -*- coding: utf-8 -*-
"""
Created on Mon Sep 17 23:03:34 2018

@author: Don
"""
# To run from Spyder iPython console:
#    runfile('D:/CRTI/python_projects/ArcGIS-scripts/CRTI Python Toolkit/fix_file_names.py', wdir='D:/CRTI/python_projects/ArcGIS-scripts/CRTI Python Toolkit', args="'D:/CRTI/GIS data/will_county_tree_crowns_sample/test'")

# The original files had periods in the file name which caused arcpy Describe to 
# not recognize them as shape files. Copy the bad files to the 'renamed'
# directory then run this to fix up the names

import os
import sys
import common_functions
common_functions.add_arcgis_to_sys_path()
import arcpy

dir = 'D:/CRTI/GIS data/will_county_tree_crowns_sample/test'

def log (message):
    common_functions.log(message)
    return

def fixup (input_folder):
    # Gather up all of the file names in the directory
    log ('Gathering all file names in input folder')
    fns = os.listdir(input_folder) 
    #loop through the name and rename
    count = 0
    for fn in fns:
        if count % ((len(fns)/25)+1) == 0:
            log('Checking file for fixup ' + str(count) + ' of ' + str(len(fns)))

        desc = arcpy.Describe(input_folder + '/' + fn)        
        if '.' in desc.baseName:
            new_fn = desc.path + '/' + desc.baseName.replace('.', '_') + '.' + desc.extension
            os.rename(desc.catalogPath, new_fn)
        count += 1
        
        
if __name__ == '__main__':
    fixup(sys.argv[1])        