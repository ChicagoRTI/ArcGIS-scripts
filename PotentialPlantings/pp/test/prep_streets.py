import arcpy
import pp.common as pp_c
import os
import multiprocessing

import pp.logger
logger = pp.logger.get('pp_log')


#LANDUSE = r'C:\Users\dmorrison\Documents\ArcGIS\Projects\Potential Plantings\Potential Plantings.gdb\landuse_Clip'
LANDUSE = r'C:\Users\dmorrison\Documents\ArcGIS\Projects\PotentialPlantings\PotentialPlantings.gdb\Landuse_Cicero'

#LANDCOVER = r'E:\PotentialPlantings\temp\landcover_2018_clip.tif'
LANDCOVER = r'C:\Users\dmorrison\Documents\ArcGIS\Projects\PotentialPlantings\PotentialPlantings.gdb\Landcover_Cicero'

#SAMPLE_AREA = r'E:\PotentialPlantings\temp\16008800.tif'
SAMPLE_AREA = r'C:\Users\dmorrison\crti\data\Cook_County_Aerial_Imagery_2017\Cicero.tif'

#LANDCOVER = r'E:\PotentialPlantings\data\land_cover_2018\land_cover_2018_clipped.tif'

OUTPUT_DIR = os.path.join(pp_c.PREP_DIR)
OUTPUT_GDB =  os.path.join(OUTPUT_DIR, 'streets.gdb')


FINAL_FC = os.path.join(OUTPUT_GDB, 'transport_planting_areas')

def run():
    
    pp_c.log_info ("Logging to %s" % pp.logger.LOG_FILE)
    
    arcpy.env.parallelProcessingFactor = "4"
    
    use_in_mem = True
    
    intermediate_output_mem =  pp_c.prepare_intermediate_output_gdb (use_in_mem)    
    intermediate_output_gdb =  pp_c.prepare_intermediate_output_gdb (False)

    sample_ndvi_rst = __get_intermediate_tif_name (intermediate_output_mem, 'sample_ndvi_rst', 1, use_in_mem)
    sample_veg_rst = __get_intermediate_tif_name (intermediate_output_mem, 'sample_veg_rst', 1, use_in_mem)
    
    #THIS ONE IS THE PROBLEM - FAILS IF in_mem
    sample_veg_cleaned_rst = __get_intermediate_tif_name (intermediate_output_gdb, 'sample_veg_cleaned_rst', 1, False)
    sample_veg_fc = pp_c.get_intermediate_name (intermediate_output_mem, 'sample_veg_fc', 1, use_in_mem)
    sample_veg_transport_fc = pp_c.get_intermediate_name (intermediate_output_mem, 'sample_veg_transport_fc', 1, use_in_mem)

    trees_rst = __get_intermediate_tif_name (intermediate_output_mem, 'trees', 1, use_in_mem)
    trees_fc = pp_c.get_intermediate_name (intermediate_output_mem, 'trees_fc', 1, use_in_mem)  
    trees_expanded_fc = pp_c.get_intermediate_name (intermediate_output_mem, 'trees_expanded_fc', 1, use_in_mem) 


    if not arcpy.Exists(OUTPUT_GDB):
        arcpy.CreateFileGDB_management(os.path.dirname(OUTPUT_GDB), os.path.basename(OUTPUT_GDB))
    
   
    # Calcualte NDVI of the sample area    
    pp_c.log_info ('Calclating NDVI to %s' % sample_ndvi_rst, None)
    # __delete_if_exists (sample_ndvi_rst)
    red = arcpy.sa.Float(arcpy.sa.Raster(SAMPLE_AREA + r"\Band_3"))
    nir = arcpy.sa.Float(arcpy.sa.Raster(SAMPLE_AREA + r"\Band_4"))
    ndvi = (nir - red) / (nir + red)
    arcpy.Delete_management(red)
    arcpy.Delete_management(nir)
    ndvi.save(sample_ndvi_rst)
         
    # Reclassify NDVI  <0: non-vegetation (0),  >0: vegetation (1)
    __reclassify_raster ( (sample_ndvi_rst, "-1 0 0;0 1 1", sample_veg_rst) ) 
    arcpy.Delete_management(sample_ndvi_rst)

    pp_c.log_info ('Running Majority filter to clean out noise', None)
    # __delete_if_exists (sample_veg_cleaned_rst)
    raster_obj = arcpy.sa.MajorityFilter(sample_veg_rst, "EIGHT", "MAJORITY") 
    arcpy.Delete_management(sample_veg_rst)
    raster_obj.save(sample_veg_cleaned_rst)
    arcpy.management.SetRasterProperties(sample_veg_cleaned_rst,  nodata="1 0")           



    pp_c.log_info ('Converting vegetation to polygons to %s' % sample_veg_fc, None)
    # __delete_if_exists (sample_veg_fc)
    arcpy.conversion.RasterToPolygon(
        in_raster=sample_veg_cleaned_rst,
        out_polygon_features=sample_veg_fc,
        simplify="SIMPLIFY",
        # raster_field="Value",
        create_multipart_features="SINGLE_OUTER_PART",
        max_vertices_per_feature=None
    )
    pp_c.log_info ('Conversion complete. %s records' % (arcpy.GetCount_management(sample_veg_fc)), None)
    arcpy.Delete_management(sample_veg_cleaned_rst)
    arcpy.Delete_management(raster_obj)


    pp_c.log_info ('Creating landuse transport layer: %s ' % str(sample_veg_transport_fc), None)
    lyr = arcpy.MakeFeatureLayer_management(LANDUSE, "transport_lyr", "LandUse = 7").getOutput(0)


    pp_c.log_info ('Reducing vegetation polygons to transportation layer: %s' % sample_veg_transport_fc, None)
    # __delete_if_exists(sample_veg_transport_fc)
    arcpy.analysis.PairwiseIntersect([lyr,sample_veg_fc ], sample_veg_transport_fc)
    arcpy.Delete_management(lyr)
    arcpy.Delete_management(sample_veg_fc)
    
    
    # Reclassify Landcover trees=1
    # __delete_if_exists(trees_rst)
    remap = "0 NODATA;1 1;2 NODATA;3 NODATA;4 NODATA;5 NODATA;6 NODATA;7 NODATA"
    __reclassify_raster ( (LANDCOVER, remap, trees_rst) )    


    __raster_to_polygon ( (trees_rst, trees_fc))
    arcpy.Delete_management(trees_rst)

    
    # Buffer out trees
    __expand_polygons (trees_fc, "10 Feet", trees_expanded_fc)
    arcpy.Delete_management(trees_fc)
    
    
    pp_c.log_info ('Creating final output: %s ' % FINAL_FC, None)
    __delete_if_exists(FINAL_FC)
    arcpy.analysis.Erase(sample_veg_transport_fc, trees_expanded_fc, FINAL_FC)
    arcpy.Delete_management(sample_veg_transport_fc)
    arcpy.Delete_management(trees_expanded_fc)


    pp_c.log_info ('Finished', None)
    return


def __raster_to_polygon (spec):
    in_raster, out_fc = spec
    __delete_if_exists (out_fc)

    pp_c.log_info ('Converting raster to polygon: %s ' % str(spec), None)
    arcpy.RasterToPolygon_conversion(in_raster, out_fc, "SIMPLIFY", "", "SINGLE_OUTER_PART", "")
    pp_c.log_info ('Conversion complete. %s records' % (arcpy.GetCount_management(out_fc)), None)
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



def __expand_polygons (in_fc, distance, out_fc):
    __delete_if_exists (out_fc)
    
    pp_c.log_info ('Expanding %s record in  %s by %s' % (arcpy.GetCount_management(in_fc), in_fc, distance), None)
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
        
def __get_intermediate_tif_name (intermediate_output, name, idx, use_in_mem):
    return pp_c.get_intermediate_name (intermediate_output, name, idx, use_in_mem, '.tif' if use_in_mem else '')
    # if use_in_mem:
    #     return pp_c.get_intermediate_name (intermediate_output, name, idx, use_in_mem) + '.tif'
    # else:
    #     return pp_c.get_intermediate_name (intermediate_output, name, idx, use_in_mem)

if __name__ == '__main__':
     run()
            