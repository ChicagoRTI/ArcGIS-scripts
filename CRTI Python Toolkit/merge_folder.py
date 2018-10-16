# -*- coding: utf-8 -*-

# To run from Spyder iPython console:
# runfile('D:/CRTI/python_projects/ArcGIS-scripts/CRTI Python Toolkit/merge_folder.py', args="'D:/CRTI/GIS data/DP_sample_tile_block' 'D:/Temp/merge_folder.shp'")
 

import sys
import common_functions
common_functions.add_arcgis_to_sys_path()
import arcpy

def log (message):
    common_functions.log(message)
                                     
    
def merge(folder, out_file):
    log("Merge " + folder + ' into ' + out_file)
    arcpy.env.workspace = folder
    fcs = arcpy.ListFeatureClasses()  
    arcpy.Merge_management(fcs, out_file)

if __name__ == '__main__':
     merge(sys.argv[1], sys.argv[2])