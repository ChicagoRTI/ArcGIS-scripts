# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------

# To run from Spyder iPython console:
# runfile('D:/CRTI/python_projects/ArcGIS-scripts/CRTI Python Toolkit/prepare_canopy_data.py', wdir='D:/CRTI/python_projects/ArcGIS-scripts/CRTI Python Toolkit', args="'D:\\CRTI\\GIS data\\DP_sample_tile_block' '2500.0' 'D:/CRTI/GIS data/Earth Engine/DupageNDVI' '1' 'D:/Temp/prepared_canopy_data.shp'")

# To run under ArcGIS python, enter these commands from the DOS window
#   cd D:\CRTI\python_projects\ArcGIS-scripts\CRTI Python Toolkit
#   C:\Python27_ArcGIS\ArcGIS10.6\python -m prepare_canopy_data "D:\CRTI\GIS data\DP_sample_tile_block" "2500" "D:\CRTI\GIS data\Earth Engine\DupageNDVI\DuPage_SampleArea_least_recent.tif" "13" "C:\Users\Don\Documents\ArcGIS\scratch.gdb\prepared_canopy_data" 


# NOTE - MakeFeatureLayer has a bug and does not release the schemal lock. The lock
#        is only released when the process ends
import os
import sys
import fs.common_functions

import arcpy
import arcpy.sa
import fs.interpolate_tile_extents
import fs.merge_fence_sitters
import fs.tile_file_names
import fs.merge_tiles

import fs.logger

TILE_ID_COLUMN_NAME = 'TileId'
POLYGON_ID_COLUMN_NAME = 'PolygonId'
CLUMP_ID_COLUMN_NAME = 'ClumpId'


def prepare_canopy_data (input_tile_folder, tile_dimension, start_step, scratch_workspace, output_fc):
    try:
        arcpy.env.overwriteOutput = True
        arcpy.env.parallelProcessingFactor = "100%"
        arcpy.env.scratchWorkspace = os.path.normpath(scratch_workspace)
        arcpy.CheckOutExtension("Spatial")
    
        step_start = int(start_step)
        step_count = 1
        step_total = 12

        fs.common_functions.log("Logging to " + fs.logger.LOG_FILE)
        fs.common_functions.step_header (0, step_total, 'Input parameters', [input_tile_folder, tile_dimension, start_step, scratch_workspace, output_fc], [])
        
        input_tile_folder = os.path.normpath(input_tile_folder)
        output_fc = os.path.normpath(output_fc)
    
        tile_info = os.path.join(arcpy.env.scratchGDB, 'tile_info')
        merged_tiles_unclumped = os.path.join(arcpy.env.scratchGDB, 'merged_tiles_unclumped')
        fence_lines = os.path.join(arcpy.env.scratchGDB, 'fence_lines')
        fence_sitter_clumps_undissolved = os.path.join(arcpy.env.scratchGDB, 'fence_sitter_clumps_undissolved')
        fence_sitter_clumps_dissolved = os.path.join(arcpy.env.scratchGDB, 'fence_sitter_clumps_dissolved')
        merged_tiles_clumped = os.path.join(arcpy.env.scratchGDB, 'merged_tiles_clumped')    
            
        
        if step_count >= step_start:
            fs.common_functions.step_header (step_count, step_total, 'Collecting tile file names', [input_tile_folder], [tile_info])
            fs.tile_file_names.create_table(input_tile_folder, tile_info)
        step_count += 1   
        # return 
    
        if step_count >= step_start:
            fs.common_functions.step_header (step_count, step_total, 'Populating TileId in all tiles', [input_tile_folder], [input_tile_folder])
            for tile_file_name, tile_id, shape in  fs.tile_file_names.read_file_names(tile_info):
                arcpy.management.CalculateField(tile_file_name, TILE_ID_COLUMN_NAME, tile_id, "PYTHON3", field_type='LONG')
        step_count += 1    
        
        # return
        
        if step_count >= step_start:
            fs.common_functions.step_header (step_count, step_total, 'Merging tiles into a single feature class', [tile_info], [merged_tiles_unclumped])
            fs.merge_tiles.merge(tile_info, merged_tiles_unclumped)
        step_count += 1       
        
        if step_count >= step_start:
            fs.common_functions.step_header (step_count, step_total, 'Adding and populating PolygonId field', [merged_tiles_unclumped], [merged_tiles_unclumped])
            arcpy.management.CalculateField(merged_tiles_unclumped, POLYGON_ID_COLUMN_NAME, "!Objectid!", "PYTHON3", field_type='LONG')
        step_count += 1  
        # return
        
        if step_count >= step_start:
            fs.common_functions.step_header (step_count, step_total, 'Creating fence lines', [tile_info], [fence_lines])
            fs.interpolate_tile_extents.main_process_fc_files(tile_info, tile_dimension, fence_lines)
        step_count += 1  
        
        # return

        if step_count >= step_start:
            fs.common_functions.step_header (step_count, step_total, 'Snaping canopy polygons to fence lines', [merged_tiles_unclumped, fence_lines], [])
            arcpy.edit.Snap(merged_tiles_unclumped, [[fence_lines, "EDGE", "1 Feet"]])
        step_count += 1    
        
        # return
    
        if step_count >= step_start:
            fs.common_functions.step_header (step_count, step_total, 'Creating fence sitters feature class (all polygons that intersect a fence line)', [merged_tiles_unclumped, fence_lines], [fence_sitter_clumps_undissolved])
            arcpy.SpatialJoin_analysis(merged_tiles_unclumped, fence_lines, fence_sitter_clumps_undissolved, 'JOIN_ONE_TO_ONE', 'KEEP_COMMON', '', 'INTERSECT')
        step_count += 1   
    
        if step_count >= step_start:
            fs.common_functions.step_header (step_count, step_total, 'Dissolve fence sitters into clumps', [fence_sitter_clumps_undissolved], [fence_sitter_clumps_dissolved])
            arcpy.Dissolve_management(fence_sitter_clumps_undissolved, fence_sitter_clumps_dissolved, "", "", "SINGLE_PART", "DISSOLVE_LINES")
        step_count += 1       
    
        if step_count >= step_start:
            fs.common_functions.step_header (step_count, step_total, 'Adding and populating ClumpId', [fence_sitter_clumps_dissolved], [fence_sitter_clumps_dissolved])
            arcpy.management.CalculateField(fence_sitter_clumps_dissolved, CLUMP_ID_COLUMN_NAME, "!Objectid!", "PYTHON3", field_type='LONG')
        step_count += 1       
    
        if step_count >= step_start:
            fs.common_functions.step_header (step_count, step_total, 'Append ClumpId to merged tiles', [merged_tiles_unclumped, fence_sitter_clumps_dissolved], [merged_tiles_clumped])
            arcpy.SpatialJoin_analysis(merged_tiles_unclumped, fence_sitter_clumps_dissolved, merged_tiles_clumped, "JOIN_ONE_TO_ONE", "KEEP_ALL",'', 'WITHIN')
        step_count += 1       
    
        if step_count >= step_start:
            fs.common_functions.step_header (step_count, step_total, 'Stitching adjacent fence sitters together', [merged_tiles_clumped], [output_fc])
            fs.merge_fence_sitters.merge(merged_tiles_clumped, output_fc)
        step_count += 1       
        
        # if step_count >= step_start:
        #     fs.common_functions.step_header (step_count, step_total, 'Cleaning up', [], [])
        #     for field in ['Join_Count', 'Shape_Length_1', 'Shape_Area_1', 'PolygonId_1', 'COUNT', 'AREA_1']:
        #         fs.common_functions.log("Deleting field %s" % (field))
        #         arcpy.DeleteField_management(output_fc, field)
        step_count += 1
        
    finally:
        fs.common_functions.log("Checking in")
        arcpy.CheckInExtension("Spatial")

    fs.common_functions.log("Finished")


if __name__ == '__main__':
     prepare_canopy_data(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6])


