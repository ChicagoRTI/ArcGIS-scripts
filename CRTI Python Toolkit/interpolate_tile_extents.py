# -*- coding: utf-8 -*-
"""
Created on Tue Sep 18 16:10:17 2018

@author: Don
"""
# MULTIPROCESSOR VERSION  - TEST ONLY FOR NOW - SEEMS TO WORK OK


# THIS VERSION SEEMS TO DO WHAT WE WANT, MAKE SURE THE SHAPEFILE NAMES DO NOT CONTAIN 
# PERIODS. IF THEY DO, RUN RENAME_SHAPE_FILES - YOU MAY NEED TO ALTER THE CODE SINCE
# IT KEYS ON A PARTICULAR PATTERN
#
# BEFORE RUNNING, CHECK THE LOCATION OF THE OUTPUT DIRECTORY
#
# THIS CODE ASSUMES EACH TILE IS A SQUARE 2500 FEET ON EACH SIDE


# To run from Spyder iPython console:
#   runfile('D:/CRTI/python_projects/ArcGIS-scripts/CRTI Python Toolkit/interpolate_tile_extents.py', wdir='D:/CRTI/python_projects/ArcGIS-scripts/CRTI Python Toolkit', args="'C:/Users/Don/Documents/ArcGIS/scratch.gdb/tile_file_names' '2500.0' 'C:\\Users\\Don\\Documents\\ArcGIS\\scratch.gdb\\fishnet'")
#
# To run under ArcGIS python, enter these commands from the DOS window
#   cd D:\CRTI\python_projects\ArcGIS-scripts\CRTI Python Toolkit\
#   C:\Python27_ArcGIS\ArcGIS10.6\python -m interpolate_tile_extents "D:/CRTI/GIS data/will_county_tree_crowns_sample/renamed" 

# Make sure the ArcGIS components are in the system path (from C:\Program Files (x86)\ArcGIS\Desktop10.6\Support\Python/Desktop10.6.pth)

import os
import sys
import multiprocessing
import traceback
import common_functions
common_functions.add_arcgis_to_sys_path()
import arcpy
import tile_file_names
import math

_threads = multiprocessing.cpu_count()

def get_install_path():
    return sys.exec_prefix

def log (message):
    common_functions.log(message)
    return

def log_progress (message, max_range, step_count, threads=1):
    common_functions.log_progress (message, max_range, step_count, threads)

def get_tile_extents_mp (name_list):
    try:
        # This function is run in parallel on multiple processors. Read the list of assigned shape files
        # and return a dictionary object with the extent information for each shape file
        log("Starting")
        count = 1
        tiles = dict()
        for file_name in name_list:
            log_progress ("Reading shape file", len(name_list), count, _threads)    
            # Get the extent information
            extent = arcpy.Describe(file_name).extent
            tiles[file_name] = extent.XMin, extent.YMin, extent.XMax, extent.YMax, extent.width, extent.height
            count = count + 1
        log("Finished")
        return tiles
    except Exception as e:
        log("Exception: " + str(e))
        log(traceback.format_exc())
        raise
    return


def adjust_boundary (reference, boundary, direction, step):
        x = reference
        if (direction == 'down'):
            while x > boundary:
                x = x - step
        else:
            while x < boundary:
                x = x + step
        return x 


def main_process_fc_files (tile_file_names_table, tile_dim, fc_output_file):
    fc_output_path, fc_output_name = os.path.split(fc_output_file)
    tile_dim = float(tile_dim)
    
    # Create the output directory if it doesn't already exist
    if not os.path.exists(fc_output_path):
        os.makedirs(fc_output_path)
    
    # Delete the output feature class if it already exists
    if arcpy.Exists(fc_output_file):
        arcpy.Delete_management(fc_output_file)
    
    # Get a list of the input feature classes
    name_list = [fn[0] for fn in tile_file_names.read_file_names(tile_file_names_table)]        
    # TEMP _ DON'T FORGET TO REMOVE THIS!!!
#    name_list = name_list * 25

    if (len(name_list) > 0):
        # Use the first shape file to get the spacial reference (should the same for all)
        sr = arcpy.Describe(name_list[0]).spatialReference
                
        # Farm out to all of the processors the task of reading in the shape files
        # and discovering the extent information, then reassemble the results into
        # a single dictionary object
        multiprocessing.set_executable(os.path.join(get_install_path(), 'pythonw.exe'))
        log('Launching ' + str(_threads) + ' worker processes')
        name_lists = [ name_list[i::_threads] for i in xrange(_threads if _threads < len(name_list) else len(name_list)) ]
        p = multiprocessing.Pool(_threads)
        tile_dicts = p.map(get_tile_extents_mp, name_lists)
        p.close()
        p.join()
        tiles = dict()
        for tile_dict in tile_dicts:
            tiles.update(tile_dict)
        
        #tiles= get_tile_extents_mp(name_lists[0]) #Non-mp call
        
        # Find the overall boundary coordinates
        log('Calculating overall boundary extent')
        x_min_overall = float('inf')
        y_min_overall = float('inf')
        x_max_overall = float('-inf')
        y_max_overall = float('-inf')
        for tile in tiles:
            x_min, y_min, x_max, y_max, width, height = tiles[tile]
            x_min_overall = min(x_min_overall, x_min)
            y_min_overall = min(y_min_overall, y_min)
            x_max_overall = max(x_max_overall, x_max)
            y_max_overall = max(y_max_overall, y_max)

        # Find any tile that has a fence sitter on each side (height and width = tile_dim)
        for reference_tile in tiles:
            x_min_reference, y_min_reference, x_max_reference, y_max_reference, width_reference, height_reference = tiles[reference_tile]
            if (width_reference == tile_dim and height_reference == tile_dim):
                break
        log('Reference tile: ' + reference_tile)
        
        # Adjust overall max and mins so they are in step with the reference tile
        x_min_overall = adjust_boundary (x_min_reference, x_min_overall, 'down', tile_dim)
        y_min_overall = adjust_boundary (y_min_reference, y_min_overall, 'down', tile_dim)
        x_max_overall = adjust_boundary (x_max_reference, x_max_overall, 'up', tile_dim)
        y_max_overall = adjust_boundary (y_max_reference, y_max_overall, 'up', tile_dim)
        
        # Create the fish net mark the tile boundaries
        arcpy.env.outputCoordinateSystem = sr
        arcpy.CreateFishnet_management (fc_output_file, "%f %f" % (x_min_overall, y_min_overall), "%f %f" % (x_min_overall, y_max_overall), tile_dim, tile_dim, math.ceil((y_max_overall-y_min_overall)/tile_dim), math.ceil((x_max_overall-x_min_overall)/tile_dim))
  
        return 

if __name__ == '__main__':
    main_process_fc_files(sys.argv[1], sys.argv[2], sys.argv[3])
    
    




