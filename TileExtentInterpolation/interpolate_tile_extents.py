# -*- coding: utf-8 -*-
"""
Created on Tue Sep 18 16:10:17 2018

@author: Don
"""

# THIS VERSION SEEMS TO DO WHAT WE WANT, MAKE SURE THE SHAPEFILE NAMES DO NOT CONTAIN 
# PERIODS. IF THEY DO, RUN RENAME_SHAPE_FILES - YOU MAY NEED TO ALTER THE CODE SINCE
# IT KEYS ON A PARTICULAR PATTERN
#
# BEFORE RUNNING, CHECK THE LOCATION OF THE OUTPUT DIRECTORY
#
# THIS CODE ASSUMES EACH TILE IS A SQUARE 1500 FEET ON EACH SIDE


# To run from Spyder iPython console:
#   runfile('D:/CRTI/python_projects/ArcGIS-scripts/TileExtentInterpolation/interpolate_tile_extents.py', wdir='D:/CRTI/python_projects/ArcGIS-scripts/TileExtentInterpolation', args="'D:/CRTI/GIS data/will_county_tree_crowns_sample/renamed'")
#
# To run under ArcGIS python, enter these commands from the DOS window
#   cd D:\CRTI\python_projects\compute_tile_extents\
#   C:\Python27_ArcGIS\ArcGIS10.6\python -m interpolate_tile_extents "D:/CRTI/GIS data/will_county_tree_crowns_sample/renamed" 

# Make sure the ArcGIS components are in the system path (from C:\Program Files (x86)\ArcGIS\Desktop10.6\Support\Python/Desktop10.6.pth)
import sys
__arc_gis_dir = "C:\\Program Files (x86)\\ArcGIS\\Desktop10.6\\"
__arc_gis_path = [__arc_gis_dir + "bin",
                __arc_gis_dir + "ArcPy",
                __arc_gis_dir + "ArcToolBox\Scripts"]
for p in __arc_gis_path: 
    if p not in sys.path: sys.path += [p]


import arcpy
import glob
import os
import sys

# Get the input arguments
__fc_input_path = sys.argv[1]
print (__fc_input_path)

__fc_output_path = __fc_input_path + '/../output'
__fc_output_name = '/tile_extents.shp'
__fc_output_file = __fc_output_path + '/' + __fc_output_name
print (__fc_output_file)

def adjust_boundary (reference, boundary, direction, step):
        x = reference
        if (direction == 'down'):
            while x > boundary:
                x = x - step
        else:
            while x < boundary:
                x = x + step
#        print ("{:.20f}".format(reference), "{:.20f}".format(boundary), "{:.20f}".format(x))                
        return x 

def main_process_shape_files ():
    
    # Create the output directory if it doesn't already exist
    if not os.path.exists(__fc_output_path):
        os.makedirs(__fc_output_path)
    
    # Delete the output feature class if it already exists
    if arcpy.Exists(__fc_output_file):
        arcpy.Delete_management(__fc_output_file)
    
    # Get a list of the shape files in the input directory
    name_list = glob.glob(__fc_input_path + '/*.shp') 

    if (len(name_list) > 0):
        # Use the first shape file to get the spacial reference (should the same for all)
        sr = arcpy.Describe(name_list[0]).spatialReference
        
        # Read in all of the shapefiles and record pertinent information
        tiles = dict()
        count = 1
        print('')
        for file_name in name_list:
            sys.stdout.write("\rReading shape file %d" % count + " of " + str(count))
            # Get the extent information
            extent = arcpy.Describe(file_name).extent
            centroid = extent.polygon.centroid
            tiles[file_name] = extent.XMin, extent.YMin, extent.XMax, extent.YMax, extent.width, extent.height, centroid
#            print (count, file_name, "{:.20f}".format(extent.XMin), extent.width, extent.height)
            count = count + 1
        print('')
        
        # Find the overall boundary coordinates
        print ('\nCalculating overall boundary extent')
        x_min_overall = float('inf')
        y_min_overall = float('inf')
        x_max_overall = float('-inf')
        y_max_overall = float('-inf')
        for tile in tiles:
            x_min, y_min, x_max, y_max, width, height, centroid = tiles[tile]
            x_min_overall = min(x_min_overall, x_min)
            y_min_overall = min(y_min_overall, y_min)
            x_max_overall = max(x_max_overall, x_max)
            y_max_overall = max(y_max_overall, y_max)
#            print "{:.20f}".format(x_min_overall), y_min_overall, x_max_overall, y_max_overall, centroid.X, centroid.Y

        # Find any tile that has a fence sitter on each side (height and width = 1500)
        for reference_tile in tiles:
            x_min_reference, y_min_reference, x_max_reference, y_max_reference, width_reference, height_reference, centroid_reference = tiles[reference_tile]
            if (width_reference == 1500.0 and height_reference == 1500.0):
                break
        print ('\nReference tile: ' + reference_tile)
        
        # Adjust overall max and mins so they are in step with the reference tile
        x_min_overall = adjust_boundary (x_min_reference, x_min_overall, 'down', 1500.0)
        y_min_overall = adjust_boundary (y_min_reference, y_min_overall, 'down', 1500.0)
        x_max_overall = adjust_boundary (x_max_reference, x_max_overall, 'up', 1500.0)
        y_max_overall = adjust_boundary (y_max_reference, y_max_overall, 'up', 1500.0)
        
        # Draw the tile boundary lines in the output feature class
        arcpy.CreateFeatureclass_management(__fc_output_path, __fc_output_name, "POLYLINE", None, "DISABLED", "DISABLED", sr)
        rows = arcpy.InsertCursor(__fc_output_file)
             
        print ('\nDrawing vertical lines')
        x = x_min_overall
        while x <= x_max_overall:
            p1 = arcpy.Point(x, y_min_overall)
            p2 = arcpy.Point(x, y_max_overall)
            line = arcpy.Polyline(arcpy.Array([p1,p2]), sr)
            row = rows.newRow()
            row.setValue("SHAPE", line)
            rows.insertRow(row)
            x = x + 1500.0
        
        print ('\nDrawing horizontal lines')
        y = y_min_overall
        while y <= y_max_overall:
            p1 = arcpy.Point(x_min_overall, y)
            p2 = arcpy.Point(x_max_overall, y)
            line = arcpy.Polyline(arcpy.Array([p1,p2]), sr)
            row = rows.newRow()
            row.setValue("SHAPE", line)
            rows.insertRow(row)
            y = y + 1500.0

        del row
        del rows
        
        return 
        
                



if __name__ == '__main__':
     main_process_shape_files()
    
    




