# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------

# To run from Spyder iPython console:
# runfile('D:/CRTI/python_projects/ArcGIS-scripts/CRTI Python Toolkit/prepare_canopy_data.py', wdir='D:/CRTI/python_projects/ArcGIS-scripts/CRTI Python Toolkit', args="'D:\\CRTI\\GIS data\\DP_sample_tile_block' 'D:/Temp/prepared_canopy_data'")

# To run under ArcGIS python, enter these commands from the DOS window
#   cd D:\CRTI\python_projects\ArcGIS-scripts\CRTI Python Toolkit\
#   C:\Python27_ArcGIS\ArcGIS10.6\python -m prepare_canopy_data "<args>" 


# NOTE - MakeFeatureLayer has a bug and does not release the schemal lock. The lock
#        is only released when the process ends
import os
import sys
import common_functions
common_functions.add_arcgis_to_sys_path()
import arcpy
import populate_field
import populate_folder_field
import merge_folder
import interpolate_tile_extents
import merge_fence_sitters


TILE_COLUMN_NAME = 'TileId'
POLYGON_ID_COLUMN_NAME = 'PolygonId'
CLUMP_ID_COLUMN_NAME = 'ClumpId'
TILE_DIMENSION = 2500.0

def prepare_canopy_data (input_tile_folder, output_fc):

    arcpy.env.overwriteOutput = True
    arcpy.env.scratchWorkspace = os.getenv('USERPROFILE') + '\\Documents\\ArcGIS'
    
    step_count = 0
    step_total = 10

    step_count += 1       
    common_functions.step_header (step_count, step_total, 'Populating TileId in all tiles', [input_tile_folder], [input_tile_folder])
    populate_folder_field.populate(input_tile_folder, TILE_COLUMN_NAME, 'FC_NAME') 
    
    step_count += 1       
    merged_tiles_unclumped = arcpy.env.scratchGDB + '\\merged_tiles_unclumped'
    common_functions.step_header (step_count, step_total, 'Merging tiles into a single feature class', [input_tile_folder], [merged_tiles_unclumped])
    merge_folder.merge(input_tile_folder, merged_tiles_unclumped)        
    
    step_count += 1       
    common_functions.step_header (step_count, step_total, 'Adding and populating PolygonId field', [merged_tiles_unclumped], [merged_tiles_unclumped])
    populate_field.populate(merged_tiles_unclumped, POLYGON_ID_COLUMN_NAME, "UNIQUE_ID")
    
    step_count += 1       
    create_fence_lines_output_fc = arcpy.env.scratchGDB + '\\fence_lines'
    common_functions.step_header (step_count, step_total, 'Creating fence lines', [input_tile_folder], [create_fence_lines_output_fc])
    interpolate_tile_extents.main_process_fc_files(input_tile_folder, create_fence_lines_output_fc, TILE_DIMENSION)

    step_count += 1       
    merged_tiles_as_layer = arcpy.env.scratchGDB + '\\merged_tiles_as_layer'
    fence_sitter_clumps_undissolved = arcpy.env.scratchGDB + '\\fence_sitter_clumps_undissolved'
    common_functions.step_header (step_count, step_total, 'Creating fence sitters feature class (all polygons that intersect a fence line)', [merged_tiles_unclumped, create_fence_lines_output_fc], [fence_sitter_clumps_undissolved])
    arcpy.MakeFeatureLayer_management(merged_tiles_unclumped, merged_tiles_as_layer, "", "", "")
    arcpy.SelectLayerByLocation_management(merged_tiles_as_layer, "INTERSECT", create_fence_lines_output_fc, "", "NEW_SELECTION", "NOT_INVERT")
    arcpy.CopyFeatures_management(merged_tiles_as_layer, fence_sitter_clumps_undissolved, "", "0", "0", "0")

    step_count += 1       
    fence_sitter_clumps_dissolved = arcpy.env.scratchGDB + '\\fence_sitter_clumps_dissolved'
    common_functions.step_header (step_count, step_total, 'Dissolve fence sitters into clumps', [fence_sitter_clumps_undissolved], [fence_sitter_clumps_dissolved])
    arcpy.Dissolve_management(fence_sitter_clumps_undissolved, fence_sitter_clumps_dissolved, "", "", "SINGLE_PART", "DISSOLVE_LINES")

    step_count += 1       
    common_functions.step_header (step_count, step_total, 'Adding and populating ClumpId', [fence_sitter_clumps_dissolved], [fence_sitter_clumps_dissolved])
    populate_field.populate(fence_sitter_clumps_dissolved, CLUMP_ID_COLUMN_NAME, "UNIQUE_ID")

    step_count += 1       
    merged_tiles_clumped = arcpy.env.scratchGDB + '\\merged_tiles_clumped'
    common_functions.step_header (step_count, step_total, 'Append ClumpId to merged tiles', [merged_tiles_unclumped, fence_sitter_clumps_dissolved], [merged_tiles_clumped])
    arcpy.SpatialJoin_analysis(merged_tiles_unclumped, fence_sitter_clumps_dissolved, merged_tiles_clumped, "JOIN_ONE_TO_ONE", "KEEP_ALL")

    step_count += 1       
    common_functions.step_header (step_count, step_total, 'Stitching adjacent fence sitters together', [merged_tiles_clumped], [output_fc])
    merge_fence_sitters.merge(merged_tiles_clumped, output_fc)

    step_count += 1       
    common_functions.step_header (step_count, step_total, 'Cleaning up', [], [])
    arcpy.DeleteField_management(output_fc, ['Join_Count', 'Shape_Length_1', 'Shape_Area_1'])


if __name__ == '__main__':
     prepare_canopy_data(sys.argv[1], sys.argv[2])


#rcpy.MakeFeatureLayer_management(Merged_tiles, Merged_tiles__as_layer_, "", "", "")


#
## Process: Add Field (PolygonId)
#arcpy.AddField_management(Merged_tiles, "PolygonId", "SHORT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
#
## Process: Make Feature Layer
#arcpy.MakeFeatureLayer_management(Merged_tiles, Merged_tiles__as_layer_, "", "", "")
#
## Process: Create fence lines
#arcpy.gp.toolbox = "D:/CRTI/python_projects/ArcGIS-scripts/CRTI Python Toolkit/CRIT python tools.pyt";
## Warning: the toolbox D:/CRTI/python_projects/ArcGIS-scripts/CRTI Python Toolkit/CRIT python tools.pyt DOES NOT have an alias. 
## Please assign this toolbox an alias to avoid tool name collisions
## And replace arcpy.gp.interpolate_tile_extents(...) with arcpy.interpolate_tile_extents_ALIAS(...)
#arcpy.gp.interpolate_tile_extents(Canopy_polygons_tiles, Fence_lines)
#
## Process: Select Layer by Location - fence sitters
#arcpy.SelectLayerByLocation_management(Merged_tiles__as_layer_, "INTERSECT", Fence_lines, "", "NEW_SELECTION", "NOT_INVERT")
#
## Process: Copy Features
#arcpy.CopyFeatures_management(Fence_sitters_layer, fence_sitters_feature_class, "", "0", "0", "0")
#
## Process: Dissolve (into clumps)
#arcpy.Dissolve_management(fence_sitters_feature_class, fence_sitters_Dissolve, "", "", "SINGLE_PART", "DISSOLVE_LINES")
#
## Process: Add Field (ClumpId)
#arcpy.AddField_management(fence_sitters_Dissolve, "ClumpId", "SHORT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
#
## Process: Populate PolygonId
#arcpy.gp.toolbox = "D:/CRTI/python_projects/ArcGIS-scripts/CRTI Python Toolkit/CRIT python tools.pyt";
## Warning: the toolbox D:/CRTI/python_projects/ArcGIS-scripts/CRTI Python Toolkit/CRIT python tools.pyt DOES NOT have an alias. 
## Please assign this toolbox an alias to avoid tool name collisions
## And replace arcpy.gp.populate_field(...) with arcpy.populate_field_ALIAS(...)
#arcpy.gp.populate_field(merged_tiles_w_polygon_id, "PolygonId", "UNIQUE_ID", Is_complete__4_)
#
## Process: Populate ClumpId
#arcpy.gp.toolbox = "D:/CRTI/python_projects/ArcGIS-scripts/CRTI Python Toolkit/CRIT python tools.pyt";
## Warning: the toolbox D:/CRTI/python_projects/ArcGIS-scripts/CRTI Python Toolkit/CRIT python tools.pyt DOES NOT have an alias. 
## Please assign this toolbox an alias to avoid tool name collisions
## And replace arcpy.gp.populate_field(...) with arcpy.populate_field_ALIAS(...)
#arcpy.gp.populate_field(fence_sitters_Dissolve__w_clump_id_, "ClumpId", "UNIQUE_ID", Is_complete__2_)
#
## Process: Spatial Join (append ClumpId)
#arcpy.SpatialJoin_analysis(merged_tiles_w_polygon_id, fence_sitters_Dissolve__w_clump_id_, merged_tiles_clumped, "JOIN_ONE_TO_ONE", "KEEP_ALL", "Area \"Area\" true true false 8 Double 0 0 ,First,#,C:\\Users\\Don\\Documents\\ArcGIS\\scratch.gdb\\merged_tiles,Area,-1,-1;Border_ind \"Border_ind\" true true false 8 Double 0 0 ,First,#,C:\\Users\\Don\\Documents\\ArcGIS\\scratch.gdb\\merged_tiles,Border_ind,-1,-1;Border_len \"Border_len\" true true false 8 Double 0 0 ,First,#,C:\\Users\\Don\\Documents\\ArcGIS\\scratch.gdb\\merged_tiles,Border_len,-1,-1;Border_tre \"Border_tre\" true true false 8 Double 0 0 ,First,#,C:\\Users\\Don\\Documents\\ArcGIS\\scratch.gdb\\merged_tiles,Border_tre,-1,-1;Compactnes \"Compactnes\" true true false 8 Double 0 0 ,First,#,C:\\Users\\Don\\Documents\\ArcGIS\\scratch.gdb\\merged_tiles,Compactnes,-1,-1;nDSM_max \"nDSM_max\" true true false 8 Double 0 0 ,First,#,C:\\Users\\Don\\Documents\\ArcGIS\\scratch.gdb\\merged_tiles,nDSM_max,-1,-1;nDSM_mean \"nDSM_mean\" true true false 8 Double 0 0 ,First,#,C:\\Users\\Don\\Documents\\ArcGIS\\scratch.gdb\\merged_tiles,nDSM_mean,-1,-1;nDSM_min \"nDSM_min\" true true false 8 Double 0 0 ,First,#,C:\\Users\\Don\\Documents\\ArcGIS\\scratch.gdb\\merged_tiles,nDSM_min,-1,-1;RelBord_tr \"RelBord_tr\" true true false 8 Double 0 0 ,First,#,C:\\Users\\Don\\Documents\\ArcGIS\\scratch.gdb\\merged_tiles,RelBord_tr,-1,-1;ShapeIndex \"ShapeIndex\" true true false 8 Double 0 0 ,First,#,C:\\Users\\Don\\Documents\\ArcGIS\\scratch.gdb\\merged_tiles,ShapeIndex,-1,-1;nDSM_StdDe \"nDSM_StdDe\" true true false 8 Double 0 0 ,First,#,C:\\Users\\Don\\Documents\\ArcGIS\\scratch.gdb\\merged_tiles,nDSM_StdDe,-1,-1;TileId \"TileId\" true true false 254 Text 0 0 ,First,#,C:\\Users\\Don\\Documents\\ArcGIS\\scratch.gdb\\merged_tiles,TileId,-1,-1;Shape_Length \"Shape_Length\" false true true 8 Double 0 0 ,First,#,C:\\Users\\Don\\Documents\\ArcGIS\\scratch.gdb\\merged_tiles,Shape_Length,-1,-1;Shape_Area \"Shape_Area\" false true true 8 Double 0 0 ,First,#,C:\\Users\\Don\\Documents\\ArcGIS\\scratch.gdb\\merged_tiles,Shape_Area,-1,-1;PolygonId \"PolygonId\" true true false 2 Short 0 0 ,First,#,C:\\Users\\Don\\Documents\\ArcGIS\\scratch.gdb\\merged_tiles,PolygonId,-1,-1;ClumpId \"ClumpId\" true true false 0 Short 0 0 ,First,#,%scratchGDB%\\fence_sitters_Dissolve,ClumpId,-1,-1", "WITHIN", "", "")
#
## Process: merge_fence_sitters
#arcpy.gp.toolbox = "D:/CRTI/python_projects/ArcGIS-scripts/CRTI Python Toolkit/CRIT python tools.pyt";
## Warning: the toolbox D:/CRTI/python_projects/ArcGIS-scripts/CRTI Python Toolkit/CRIT python tools.pyt DOES NOT have an alias. 
## Please assign this toolbox an alias to avoid tool name collisions
## And replace arcpy.gp.merge_fence_sitters(...) with arcpy.merge_fence_sitters_ALIAS(...)
#arcpy.gp.merge_fence_sitters(merged_tiles_clumped, Output_folder, "canopy_polygons")

