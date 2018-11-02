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

test = 0

def log (message):
    common_functions.log(message)
    return


def merge_one_chunk (fns, sr, fc_output):
    temporary_assets = list()
    try:
        in_mem_tile_fc = os.path.join('in_memory', 'tile')
        temporary_assets += [in_mem_tile_fc]

        arcpy.CreateFeatureclass_management(os.path.dirname(in_mem_tile_fc), os.path.basename(in_mem_tile_fc), "POLYGON", fns[0], '','', sr)
        
        if test == 0:
            # APPEND
            for fn in fns:
                arcpy.Append_management(fn, in_mem_tile_fc)
        
        if test == 1:
            # UPDATE CURSOR
            with arcpy.da.InsertCursor(in_mem_tile_fc, '*') as insert_cursor:
                # Loop through each of the tiles and append them to the output feature class
                for fn in fns:
                    with arcpy.da.SearchCursor(fn, '*', '', sr, False) as read_cursor:
                        for attrs in read_cursor:
                            insert_cursor.insertRow(attrs)
                    del read_cursor
            del insert_cursor

        arcpy.Append_management(in_mem_tile_fc, fc_output)
            
    finally:
        # Clean up    
        for temporary_asset in temporary_assets:    
            arcpy.Delete_management(temporary_asset)



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
    
    



