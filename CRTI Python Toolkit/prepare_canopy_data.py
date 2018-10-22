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
import common_functions
common_functions.add_arcgis_to_sys_path()
import arcpy
import arcpy.sa
import populate_field
#import populate_folder_field
#import merge_folder
import interpolate_tile_extents
import merge_fence_sitters
import fix_file_names
import tile_file_names
import join_files

TILE_COLUMN_NAME = 'TileId'
POLYGON_ID_COLUMN_NAME = 'PolygonId'
CLUMP_ID_COLUMN_NAME = 'ClumpId'

def prepare_canopy_data (input_tile_folder, tile_dimension, ndvi_raster_folder, start_step, output_fc):
    try:
        arcpy.env.overwriteOutput = True
        arcpy.env.scratchWorkspace = os.path.normpath(os.path.join(os.getenv('USERPROFILE'),'Documents/ArcGIS'))
        arcpy.CheckOutExtension("Spatial")
    
        common_functions.log("Logging to " + arcpy.env.scratchFolder)
    
        step_start = int(start_step)
        step_count = 1
        step_total = 15
    
        tile_file_name_table = os.path.join(arcpy.env.scratchGDB, 'tile_file_names')
        merged_tiles_unclumped = os.path.join(arcpy.env.scratchGDB, 'merged_tiles_unclumped')
        create_fence_lines_output_fc = os.path.join(arcpy.env.scratchGDB, 'fence_lines')
        merged_tiles_as_layer = os.path.join(arcpy.env.scratchGDB, 'merged_tiles_as_layer')
        fence_sitter_clumps_undissolved = os.path.join(arcpy.env.scratchGDB, 'fence_sitter_clumps_undissolved')
        fence_sitter_clumps_dissolved = os.path.join(arcpy.env.scratchGDB, 'fence_sitter_clumps_dissolved')
        merged_tiles_clumped = os.path.join(arcpy.env.scratchGDB, 'merged_tiles_clumped')
        merged_ndvi_rasters = os.path.join(arcpy.env.scratchGDB, 'merged_ndvi_rasters')
        canopies_without_ndvi = os.path.join(arcpy.env.scratchGDB, 'canopies_without_ndvi')       
        zonal_ndvi = os.path.join(arcpy.env.scratchGDB, 'zonal_ndvi')
    
        
        if step_count >= step_start:
            common_functions.step_header (step_count, step_total, 'Collecting tile file names', [input_tile_folder], [])
            tile_file_names.create_table(input_tile_folder, tile_file_name_table)
        step_count += 1       
    
        if step_count >= step_start:
            common_functions.step_header (step_count, step_total, 'Fixing up tile file names', [tile_file_name_table], [tile_file_name_table])
            fix_file_names.fixup(tile_file_name_table)
        step_count += 1       
        
        if step_count >= step_start:
            common_functions.step_header (step_count, step_total, 'Populating TileId in all tiles', [input_tile_folder], [input_tile_folder])
            populate_field.populate(tile_file_names.read_file_names(tile_file_name_table), TILE_COLUMN_NAME, 'FC_NAME') 
        step_count += 1       
        
        if step_count >= step_start:
            common_functions.step_header (step_count, step_total, 'Merging tiles into a single feature class', [tile_file_name_table], [merged_tiles_unclumped])
            arcpy.Merge_management(tile_file_names.read_file_names(tile_file_name_table), merged_tiles_unclumped)
        step_count += 1       
        
        if step_count >= step_start:
            common_functions.step_header (step_count, step_total, 'Adding and populating PolygonId field', [merged_tiles_unclumped], [merged_tiles_unclumped])
            populate_field.populate([merged_tiles_unclumped], POLYGON_ID_COLUMN_NAME, "UNIQUE_ID")
        step_count += 1       
        
        if step_count >= step_start:
            common_functions.step_header (step_count, step_total, 'Creating fence lines', [tile_file_name_table], [create_fence_lines_output_fc])
            interpolate_tile_extents.main_process_fc_files(tile_file_name_table, tile_dimension, create_fence_lines_output_fc)
        step_count += 1       
    
        if step_count >= step_start:
            common_functions.step_header (step_count, step_total, 'Creating fence sitters feature class (all polygons that intersect a fence line)', [merged_tiles_unclumped, create_fence_lines_output_fc], [fence_sitter_clumps_undissolved])
            arcpy.MakeFeatureLayer_management(merged_tiles_unclumped, merged_tiles_as_layer, "", "", "")
            arcpy.SelectLayerByLocation_management(merged_tiles_as_layer, "INTERSECT", create_fence_lines_output_fc, "", "NEW_SELECTION", "NOT_INVERT")
            arcpy.CopyFeatures_management(merged_tiles_as_layer, fence_sitter_clumps_undissolved, "", "0", "0", "0")
        step_count += 1       
    
        if step_count >= step_start:
            common_functions.step_header (step_count, step_total, 'Dissolve fence sitters into clumps', [fence_sitter_clumps_undissolved], [fence_sitter_clumps_dissolved])
            arcpy.Dissolve_management(fence_sitter_clumps_undissolved, fence_sitter_clumps_dissolved, "", "", "SINGLE_PART", "DISSOLVE_LINES")
        step_count += 1       
    
        if step_count >= step_start:
            common_functions.step_header (step_count, step_total, 'Adding and populating ClumpId', [fence_sitter_clumps_dissolved], [fence_sitter_clumps_dissolved])
            populate_field.populate([fence_sitter_clumps_dissolved], CLUMP_ID_COLUMN_NAME, "UNIQUE_ID")
        step_count += 1       
    
        if step_count >= step_start:
            common_functions.step_header (step_count, step_total, 'Append ClumpId to merged tiles', [merged_tiles_unclumped, fence_sitter_clumps_dissolved], [merged_tiles_clumped])
            arcpy.SpatialJoin_analysis(merged_tiles_unclumped, fence_sitter_clumps_dissolved, merged_tiles_clumped, "JOIN_ONE_TO_ONE", "KEEP_ALL")
        step_count += 1       
    
        if step_count >= step_start:
            common_functions.step_header (step_count, step_total, 'Stitching adjacent fence sitters together', [merged_tiles_clumped], [canopies_without_ndvi])
            merge_fence_sitters.merge(merged_tiles_clumped, canopies_without_ndvi)
        step_count += 1       

        if step_count >= step_start:
            common_functions.step_header (step_count, step_total, 'Merge NDVI rasters', [ndvi_raster_folder], [merged_ndvi_rasters])
            arcpy.env.workspace = ndvi_raster_folder
            arcpy.MosaicToNewRaster_management(arcpy.ListRasters('', ''), os.path.dirname(merged_ndvi_rasters), os.path.basename(merged_ndvi_rasters), '', '32_BIT_FLOAT', '', 1)
        step_count += 1   
        
        if step_count >= step_start:
            common_functions.step_header (step_count, step_total, 'Computing NDVI zonal statistics', [canopies_without_ndvi, merged_ndvi_rasters], [zonal_ndvi])
            arcpy.sa.ZonalStatisticsAsTable(canopies_without_ndvi, POLYGON_ID_COLUMN_NAME, merged_ndvi_rasters, zonal_ndvi)
        step_count += 1       
    
        if step_count >= step_start:
            common_functions.step_header (step_count, step_total, 'Appending NDVI statistics', [canopies_without_ndvi, zonal_ndvi], [output_fc])
            join_files.join(canopies_without_ndvi, zonal_ndvi, POLYGON_ID_COLUMN_NAME, POLYGON_ID_COLUMN_NAME, '', output_fc)
        step_count += 1       
        
        if step_count >= step_start:
            common_functions.step_header (step_count, step_total, 'Cleaning up', [], [])
            arcpy.DeleteField_management(output_fc, ['Join_Count', 'Shape_Length_1', 'Shape_Area_1', 'PolygonId_1', 'COUNT', 'AREA_1'])
        step_count += 1
    finally:
        arcpy.CheckInExtension("Spatial")


if __name__ == '__main__':
     prepare_canopy_data(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])


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

