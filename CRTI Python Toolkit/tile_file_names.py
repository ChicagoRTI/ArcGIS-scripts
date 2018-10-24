# -*- coding: utf-8 -*-
"""
Created on Tue Sep 18 16:10:17 2018

@author: Don
"""
# To run from Spyder iPython console:
#   runfile('D:/CRTI/python_projects/ArcGIS-scripts/CRTI Python Toolkit/tile_file_names.py', wdir='D:/CRTI/python_projects/ArcGIS-scripts/CRTI Python Toolkit', args="'D:/CRTI/GIS data/will_county_tree_crowns_sample/renamed' 'C:\\Users\\Don\\Documents\\ArcGIS\\scratch.gdb\\tile_names'")
#

import os
import sys
import common_functions
common_functions.add_arcgis_to_sys_path()
import arcpy

_TILE_NAME = 'TileName'
_TILE_ID = 'TileId'

def log (message):
    common_functions.log(message)
    return

# Return the file names/ids as a list of tuples <tile_name, tile_id>
def read_file_names (table):
    names = list()
    with arcpy.da.SearchCursor(table, [_TILE_NAME, _TILE_ID ]) as rows:
        for row in rows:
            names.append((row[0],row[1]))
        del rows
    return names

# Write the list of file names/ids to the output table
def write_file_names (table, file_names):
    log ('Creating output table ' + table)
    out_path, out_fc = os.path.split(table)
    arcpy.env.workspace = out_path
    if arcpy.Exists(table):
        arcpy.Delete_management(table)
    arcpy.CreateTable_management(out_path, out_fc)
    arcpy.AddField_management(out_fc, _TILE_NAME, 'TEXT', '512')
    arcpy.AddField_management(out_fc, _TILE_ID, 'LONG')

    log ('Writing file names to ' + table)
    tile_id = 1    
    with  arcpy.da.InsertCursor(out_fc, [_TILE_NAME, _TILE_ID]) as rows:
        for name in file_names:
            rows.insertRow([name, tile_id])
            tile_id += 1
        del rows     
        
def create_table (input_fc_folder, output_table):
    log ('Gathering file names from ' + input_fc_folder)
    arcpy.env.workspace = input_fc_folder
    names = [os.path.join(input_fc_folder, fc_name) for fc_name in arcpy.ListFeatureClasses()]   
    log (str(len(names)) + ' files found')
    write_file_names (output_table, names)
#    x = read_file_names(output_table)
#    print(x)
    return 
 

if __name__ == '__main__':
    create_table(sys.argv[1], sys.argv[2])
    
    




