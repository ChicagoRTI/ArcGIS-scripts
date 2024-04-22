import arcpy
import pp.common as pp_c
import os
import multiprocessing

import pp.logger
logger = pp.logger.get('pp_log')


LANDCOVER = pp_c.LANDCOVER_TIF

TREES_AND_BUILDING_GDB = os.path.join(pp_c.PREP_DIR, 'trees_and_buildings.gdb')
TREES_AND_BUILDINGS_RST = os.path.join(pp_c.PREP_DIR, 'trees_and_buildings_raster.tif')
TREES_AND_BUILDINGS_FC = os.path.join(TREES_AND_BUILDING_GDB, 'trees_and_buildings')
TREES_AND_BUILDINGS_EXPANDED_FC = os.path.join(TREES_AND_BUILDING_GDB, 'trees_and_buildings_expanded')

SOIL_AND_TURF_GDB = os.path.join(pp_c.PREP_DIR, 'soil_and_turf.gdb')
SOIL_AND_TURF_RST = os.path.join(pp_c.PREP_DIR, 'soil_and_turf_raster.tif')
SOIL_AND_TURF_FC = os.path.join(SOIL_AND_TURF_GDB, 'soil_and_turf')
SOIL_AND_TURF_REDUCED_FC = os.path.join(SOIL_AND_TURF_GDB, 'soil_and_turf_reduced')

PLANTABLE_SPACES_GDB = os.path.join(pp_c.PREP_DIR, 'plantable_spaces.gdb')
PLANTABLE_SPACES_UNPROJECTED_FC = os.path.join(PLANTABLE_SPACES_GDB, 'all_spaces_unprojected')
PLANTABLE_SPACES_FC = os.path.join(PLANTABLE_SPACES_GDB, 'all_spaces')


RECLASSIFY_SPECS = [
    (LANDCOVER, "0 NODATA;1 1;2 NODATA;3 NODATA;4 NODATA;5 1;6 NODATA;7 NODATA", TREES_AND_BUILDINGS_RST),
    (LANDCOVER, "0 NODATA;1 NODATA;2 1;3 1;4 NODATA;5 NODATA;6 NODATA;7 NODATA", SOIL_AND_TURF_RST)
    ]

RASTER_TO_POLYGON_SPECS  = [
    (TREES_AND_BUILDINGS_RST, TREES_AND_BUILDINGS_FC),
    (SOIL_AND_TURF_RST, SOIL_AND_TURF_FC)
   
    ]

def run():
    
    pp_c.log_info ("Logging to %s" % pp.logger.LOG_FILE)
    
    arcpy.env.parallelProcessingFactor = "50%"
    
    os.makedirs(pp_c.PREP_DIR, exist_ok=True)
    
    if not arcpy.Exists(TREES_AND_BUILDING_GDB):
        arcpy.CreateFileGDB_management(os.path.dirname(TREES_AND_BUILDING_GDB), os.path.basename(TREES_AND_BUILDING_GDB))

    
    if not arcpy.Exists(SOIL_AND_TURF_GDB):
        arcpy.CreateFileGDB_management(os.path.dirname(SOIL_AND_TURF_GDB), os.path.basename(SOIL_AND_TURF_GDB))

    
    if not arcpy.Exists(PLANTABLE_SPACES_GDB):
        arcpy.CreateFileGDB_management(os.path.dirname(PLANTABLE_SPACES_GDB), os.path.basename(PLANTABLE_SPACES_GDB))

    
    p = multiprocessing.Pool(len(RECLASSIFY_SPECS))
    p.map(__reclassify_raster, RECLASSIFY_SPECS, 1)
    p.close() 
        
    p = multiprocessing.Pool(len(RASTER_TO_POLYGON_SPECS))
    p.map(__raster_to_polygon, RASTER_TO_POLYGON_SPECS, 1)
    p.close()
    
    __expand_polygons (TREES_AND_BUILDINGS_FC, "20 Feet", TREES_AND_BUILDINGS_EXPANDED_FC)

    
    pp_c.log_info ('Reducing spaces to: %s ' % SOIL_AND_TURF_REDUCED_FC, None)
    __delete_if_exists (SOIL_AND_TURF_REDUCED_FC)
    arcpy.analysis.PairwiseErase(SOIL_AND_TURF_FC, TREES_AND_BUILDINGS_EXPANDED_FC, SOIL_AND_TURF_REDUCED_FC)
    
    pp_c.log_info ('Repair invalid features', None)        
    arcpy.management.RepairGeometry(SOIL_AND_TURF_REDUCED_FC, "DELETE_NULL", "ESRI")

    pp_c.log_info ('Converting multipart polygons to singlepart', None)  
    __delete_if_exists (PLANTABLE_SPACES_UNPROJECTED_FC)      
    arcpy.MultipartToSinglepart_management(SOIL_AND_TURF_REDUCED_FC, PLANTABLE_SPACES_UNPROJECTED_FC)            
                
    pp_c.log_info ('Projecting results', None)        
    __delete_if_exists (PLANTABLE_SPACES_FC)      
    arcpy.management.Project(PLANTABLE_SPACES_UNPROJECTED_FC, PLANTABLE_SPACES_FC, arcpy.SpatialReference(102671))
    
    pp_c.log_info ('Finished', None)
    return


def __reclassify_raster (spec):
    in_raster, remap, out_raster = spec
    __delete_if_exists (out_raster)

    pp_c.log_info ('Classifying: %s ' % str(spec), None)
    raster_obj = arcpy.sa.Reclassify(in_raster,  reclass_field="Value", remap=remap, missing_values="DATA")
    pp_c.log_info ('Saving reclassified raster to %s' % (out_raster), None)
    raster_obj.save(out_raster)
    pp_c.log_info ('Reclassify complete', None)
    return
 
def __raster_to_polygon (spec):
    in_raster, out_fc = spec
    __delete_if_exists (out_fc)

    pp_c.log_info ('Converting raster to polygon: %s ' % str(spec), None)
    arcpy.RasterToPolygon_conversion(in_raster, out_fc, "SIMPLIFY", "", "SINGLE_OUTER_PART", "")
    pp_c.log_info ('Conversion complete', None)
    return  


def __expand_polygons (in_fc, distance, out_fc):
    __delete_if_exists (out_fc)
    
    pp_c.log_info ('Expanding %s by %s' % (in_fc, distance), None)
    arcpy.analysis.PairwiseBuffer(
    in_features=in_fc,
    out_feature_class=out_fc,
    buffer_distance_or_field=distance,
    dissolve_option="NONE",
    dissolve_field=None,
    method="PLANAR",
    max_deviation="0 Feet")
    pp_c.log_info ('Expansion complete', None)
    return
    
    
        
def __delete_if_exists (f):
    if arcpy.Exists(f):
        pp_c.log_info ('Deleting %s' % (f), None)
        arcpy.Delete_management(f)    
    return
        

        

if __name__ == '__main__':
     run()
            