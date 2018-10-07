# -*- coding: utf-8 -*-

# To run from Spyder iPython console:
#runfile('D:/CRTI/python_projects/ArcGIS-scripts/Test/join.py', args="\
#'D:/CRTI/GIS data/Dupage_with_NDVI/DuPage_crowns_intersecting_TreeInventory.shp' \
#'D:/CRTI/GIS data/Dupage_with_NDVI/csvs\DuPage_NDVI_tree_polys_nearInvTrees.csv' \
#'TreeNum' \
#'TreeNum' \
#'NDVI_MEAN;NDVI_MAX;NDVI_STD' \
#'D:/temp/shp_test/join.shp' \
#")
 

#
# When using using fn_left_mem instead of fn_left in the join, the time went from 
# 189 minutes to under 2 minutes
#
import time
import os
import sys


__arc_gis_dir = "C:\\Program Files (x86)\\ArcGIS\\Desktop10.6\\"
__arc_gis_path = [__arc_gis_dir + "bin",
                __arc_gis_dir + "ArcPy",
                __arc_gis_dir + "ArcToolBox\Scripts"]
for p in __arc_gis_path: 
    if p not in sys.path: sys.path += [p]

import arcpy

temporary_assets = list()

fn_left = arcpy.GetParameterAsText(0)
fn_right = arcpy.GetParameterAsText(1)
join_attr_left = arcpy.GetParameterAsText(2)
join_attr_right = arcpy.GetParameterAsText(3)
include_fields_right = arcpy.GetParameterAsText(4).split(';')
shp_out = arcpy.GetParameterAsText(5)

def log (message):
    message = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ": " + str(os.getpid()) + ": " + message
    print (message)
    sys.stdout.flush()
    arcpy.AddMessage(message)
    
def import_if_text_file (in_file, temporary_assets) :
    in_file_desc = arcpy.Describe(in_file)
    if in_file_desc.dataType == 'TextFile':
        log('Importing into in-memory geodatabase table:  ' + in_file)
        in_mem_file = 'in_memory\\' + in_file_desc.baseName
        arcpy.CopyRows_management(in_file, in_mem_file)
        temporary_assets.append(in_mem_file)
        return in_mem_file
    else:
        return in_file
    
def move_to_in_memory (in_file, temporary_assets):
    in_file_desc = arcpy.Describe(in_file)
    if in_file_desc.dataType == 'ShapeFile' and not in_file_desc.name.startswith('in_memory\\'):
        log('Importing into in-memory shape file: ' + in_file)
        in_mem_file = 'in_memory\\' + in_file_desc.baseName
        arcpy.CopyFeatures_management(in_file, in_mem_file)
        temporary_assets.append(in_mem_file)
        return in_mem_file
    else:
        return in_file
    
def create_index (in_file, join_attr):
    in_file_desc = arcpy.Describe(in_file)
    if in_file_desc.dataType == 'ShapeFile' and not in_file_desc.name.startswith('in_memory\\'):
        if join_attr not in [index.name for index in arcpy.ListIndexes(in_file)]:
            log('Indexing attribute ' + join_attr + ' in ' + in_file)  # Required by AddJoin
            arcpy.AddIndex_management(in_file, [join_attr], join_attr+'Idx', 'UNIQUE', 'ASCENDING')
    return                                  
    
        
try:
    # Log the input parameters
    for i in range(6):
        log (arcpy.GetParameterAsText(i))
    
    create_index (fn_left, join_attr_left)
    create_index (fn_right, join_attr_right)
    
    fn_left = import_if_text_file (fn_left, temporary_assets)
    fn_right = import_if_text_file (fn_right, temporary_assets)
        
    fn_left = move_to_in_memory (fn_left, temporary_assets)
    fn_right = move_to_in_memory (fn_right, temporary_assets)
       
    log("Joining files")
    shp = arcpy.JoinField_management(fn_left, join_attr_left, fn_right, join_attr_right, include_fields_right)
    #shp = arcpy.AddJoin_management(fn_left, join_attr_left, fn_right, join_attr_right, 'KEEP_ALL')
    
    log("Copying results to persistent shape file: " + shp_out)
    arcpy.Delete_management(shp_out)  
    arcpy.CopyFeatures_management(shp, shp_out)
except Exception as e:
    log("Exception: " + str(e))
    arcpy.AddError(str(e))

# Clean up    
for temporary_asset in temporary_assets:    
    log('Deleting ' + temporary_asset)
    arcpy.Delete_management(temporary_asset)
log("Done")

