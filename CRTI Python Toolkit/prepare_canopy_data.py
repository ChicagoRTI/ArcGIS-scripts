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
import interpolate_tile_extents
import merge_fence_sitters
import fix_file_names
import tile_file_names
import join_files

TILE_ID_COLUMN_NAME = 'TileId'
POLYGON_ID_COLUMN_NAME = 'PolygonId'
CLUMP_ID_COLUMN_NAME = 'ClumpId'
RASTER_COORDINATE_SYSTEM = 'WGS 1984'

def prepare_canopy_data (input_tile_folder, tile_dimension, ndvi_raster_folder, start_step, scratch_workspace, output_fc):
    try:
        arcpy.env.overwriteOutput = True
        arcpy.env.scratchWorkspace = os.path.normpath(scratch_workspace)
        arcpy.CheckOutExtension("Spatial")
    
        common_functions.log("Logging to " + arcpy.env.scratchFolder)
    
        step_start = int(start_step)
        step_count = 1
        step_total = 15
    
        tile_file_name_table = os.path.join(arcpy.env.scratchGDB, 'tile_file_names')
        merged_tiles_unclumped = os.path.join(arcpy.env.scratchGDB, 'merged_tiles_unclumped')
        fence_lines = os.path.join(arcpy.env.scratchGDB, 'fence_lines')
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
            populate_field.populate([l + (TILE_ID_COLUMN_NAME,'LONG',) for l in tile_file_names.read_file_names(tile_file_name_table)]) 
        step_count += 1       
        
        if step_count >= step_start:
            common_functions.step_header (step_count, step_total, 'Merging tiles into a single feature class', [tile_file_name_table], [merged_tiles_unclumped])
            arcpy.Merge_management(tile_file_names.read_file_names(tile_file_name_table), merged_tiles_unclumped)
        step_count += 1       
        
        if step_count >= step_start:
            common_functions.step_header (step_count, step_total, 'Adding and populating PolygonId field', [merged_tiles_unclumped], [merged_tiles_unclumped])
            populate_field.populate([(merged_tiles_unclumped, 'UNIQUE_ID', POLYGON_ID_COLUMN_NAME, 'LONG')])
        step_count += 1       
        
        if step_count >= step_start:
            common_functions.step_header (step_count, step_total, 'Creating fence lines', [tile_file_name_table], [fence_lines])
            interpolate_tile_extents.main_process_fc_files(tile_file_name_table, tile_dimension, fence_lines)
        step_count += 1       
    
        if step_count >= step_start:
            common_functions.step_header (step_count, step_total, 'Creating fence sitters feature class (all polygons that intersect a fence line)', [merged_tiles_unclumped, fence_lines], [fence_sitter_clumps_undissolved])
            arcpy.SpatialJoin_analysis(merged_tiles_unclumped, fence_lines, fence_sitter_clumps_undissolved, 'JOIN_ONE_TO_ONE', 'KEEP_COMMON', '', 'INTERSECT')
        step_count += 1       
    
        if step_count >= step_start:
            common_functions.step_header (step_count, step_total, 'Dissolve fence sitters into clumps', [fence_sitter_clumps_undissolved], [fence_sitter_clumps_dissolved])
            arcpy.Dissolve_management(fence_sitter_clumps_undissolved, fence_sitter_clumps_dissolved, "", "", "SINGLE_PART", "DISSOLVE_LINES")
        step_count += 1       
    
        if step_count >= step_start:
            common_functions.step_header (step_count, step_total, 'Adding and populating ClumpId', [fence_sitter_clumps_dissolved], [fence_sitter_clumps_dissolved])
            populate_field.populate([(fence_sitter_clumps_dissolved, 'UNIQUE_ID', CLUMP_ID_COLUMN_NAME, 'LONG')])
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
#            arcpy.env.workspace = ndvi_raster_folder
#            arcpy.MosaicToNewRaster_management(arcpy.ListRasters('', ''), os.path.dirname(merged_ndvi_rasters), os.path.basename(merged_ndvi_rasters), '', '32_BIT_FLOAT', '', 1)
            arcpy.Delete_management(merged_ndvi_rasters)
            arcpy.CreateMosaicDataset_management(os.path.dirname(merged_ndvi_rasters), os.path.basename(merged_ndvi_rasters), RASTER_COORDINATE_SYSTEM, 1, '32_BIT_FLOAT', 'NONE')
            arcpy.AddRastersToMosaicDataset_management(merged_ndvi_rasters, 'Raster Dataset', ndvi_raster_folder, '', '', '', '', '', '', '', '*.tif', False, 'OVERWRITE_DUPLICATES')
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
     prepare_canopy_data(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6])


