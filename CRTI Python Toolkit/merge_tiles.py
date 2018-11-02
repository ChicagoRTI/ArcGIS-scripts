# -*- coding: utf-8 -*-
"""
Created on Tue Mar 20 11:07:22 2018

@author: Don
"""
# To run from Spyder iPython console:
#   runfile('D:/CRTI/python_projects/ArcGIS-scripts/CRTI Python Toolkit/merge_tiles.py', wdir='D:/CRTI/python_projects/ArcGIS-scripts/CRTI Python Toolkit', args="'C:\Users\Don\Documents\ArcGIS\scratch.gdb\\tile_file_names' 'D:/Temp/scratch.gdb\merged_tiles_unclumped'")
#

# Make sure the ArcGIS components are in the system path (from C:\Program Files (x86)\ArcGIS\Desktop10.6\Support\Python/Desktop10.6.pth)
import sys
import os
import common_functions
common_functions.add_arcgis_to_sys_path()
import arcpy
import tile_file_names


_CHUNK_SIZE = 1000


def log (message):
    common_functions.log(message)
    return


def merge_one_chunk (fns, sr, fc_output):
    in_mem_tile_fc = os.path.join('in_memory', 'tile')
    try:
        # Create an in-memory feature class to accumulate the chunk
        arcpy.CreateFeatureclass_management(os.path.dirname(in_mem_tile_fc), os.path.basename(in_mem_tile_fc), "POLYGON", fns[0], '','', sr)
        # Aggregate all tiles in the chunk        
        for fn in fns:
            arcpy.Append_management(fn, in_mem_tile_fc)
        # Append the chunk to the output feature class
        arcpy.Append_management(in_mem_tile_fc, fc_output)
            
    finally:
        # Clean up    
        arcpy.Delete_management(in_mem_tile_fc)



def merge (tile_file_names_table, fc_output):
    
    # Chunk up the list of tiles
    fns = [fn[0] for fn in tile_file_names.read_file_names(tile_file_names_table)]
    fns_list = [fns[i:i+_CHUNK_SIZE] for i in range(0, len(fns), _CHUNK_SIZE)] 
    sr = arcpy.Describe(fns[0]).spatialReference
    
    # Delete the output feature set
    arcpy.Delete_management(fc_output)
    arcpy.CreateFeatureclass_management(os.path.dirname(fc_output), os.path.basename(fc_output), "POLYGON", fns[0], '','', sr)
    
    i=0
    for fns in fns_list:
        i += 1
        common_functions.log_progress("Processing segment", len(fns_list), i)
        merge_one_chunk (fns, sr, fc_output)
 


if __name__ == '__main__':
     merge(sys.argv[1], sys.argv[2])
    
    



