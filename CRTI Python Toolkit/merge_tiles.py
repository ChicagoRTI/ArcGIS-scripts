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

_fc_mem = "in_memory\\fence_sitters"
_use_fc_mem = False



def log (message):
    common_functions.log(message)
    return


def merge (tile_file_names_table, fc_output):
    temporary_assets = list()
    try:
        # Get the tile names
        fns = [fn[0] for fn in tile_file_names.read_file_names(tile_file_names_table)] 
        fn_first = fns.pop(0)
        # Get the spatial reference from the first tile
        sr = arcpy.Describe(fn_first).spatialReference
        # Copy the first tile to seed the output feature class
#        arcpy.FeatureClassToFeatureClass_conversion(fn_first, os.path.dirname(fc_output), os.path.basename(fc_output), '')
        arcpy.CopyFeatures_management(fn_first, fc_output)

        in_mem_tile_fc = os.path.join('in_memory', 'tile')
        in_mem_fc_output = os.path.join('in_memory', 'fc_output')
        arcpy.CopyFeatures_management(fc_output, in_mem_fc_output)
        temporary_assets += [in_mem_tile_fc, in_mem_fc_output]
        
        test = 0
        
        if test == 0:
            # APPEND
            i = 1
            for fn in fns:
                arcpy.CopyFeatures_management(fn, in_mem_tile_fc)
                common_functions.log_progress("Merging tile ", len(fns)+1, i)
                arcpy.Append_management(in_mem_tile_fc, in_mem_fc_output)
                i += 1
        
        if test == 1:
            # UPDATE CURSOR
            with arcpy.da.InsertCursor(in_mem_fc_output, '*') as insert_cursor:
                # Loop through each of the tiles and append them to the output feature class
                i = 2
                for fn in fns:
                    common_functions.log_progress("Merging tile ", len(fns)+1, i)
                    arcpy.CopyFeatures_management(fn, in_mem_tile_fc)
                    with arcpy.da.SearchCursor(in_mem_tile_fc, '*', '', sr, False) as read_cursor:
                        for attrs in read_cursor:
                            insert_cursor.insertRow(attrs)
                    del read_cursor
                    i += 1
            del insert_cursor
        

        log("Copying merged features to " + fc_output)
        arcpy.CopyFeatures_management(in_mem_fc_output, fc_output)



    finally:
        # Clean up    
        for temporary_asset in temporary_assets:    
            log('Deleting ' + temporary_asset)
            arcpy.Delete_management(temporary_asset)
        log("Done")



if __name__ == '__main__':
     merge(sys.argv[1], sys.argv[2])
    
    



