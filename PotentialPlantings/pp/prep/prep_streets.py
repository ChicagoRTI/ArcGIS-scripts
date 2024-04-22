import arcpy
import pp.common as pp_c
import os
import multiprocessing
import traceback

import pp.logger
logger = pp.logger.get('pp_log')

PROCESSORS = 10

LANDUSE = pp_c.LANDUSE_FC
LANDCOVER = pp_c.LANDCOVER_TIF


SAMPLE_AREA = r'C:\Users\dmorrison\crti\data\Cook_County_Aerial_Imagery_2017\Cicero.tif'

FIPS = '17031'

VEG_TIFS_DIR = os.path.join(pp_c.PREP_DIR, 'veg_tifs', FIPS)
VEG_MOSAIC_GDB = os.path.join(pp_c.PREP_DIR, 'streets.gdb')
VEG_MOSAIC_RST = os.path.join(VEG_MOSAIC_GDB, 'veg_mosaic')

OUTPUT_DIR = os.path.join(pp_c.PREP_DIR)
OUTPUT_GDB =  os.path.join(OUTPUT_DIR, 'streets.gdb')


FINAL_FC = os.path.join(OUTPUT_GDB, 'transport_planting_areas')

def run():
    
    pp_c.log_info ("Logging to %s" % pp.logger.LOG_FILE)
    
    arcpy.env.parallelProcessingFactor = "4"
    
    use_in_mem = True
    
    intermediate_output_mem =  pp_c.prepare_intermediate_output_gdb (use_in_mem)    
    # intermediate_output_gdb =  pp_c.prepare_intermediate_output_gdb (False)
    
    veg_tif_names = pp_c.get_intermediate_name (intermediate_output_mem, 'veg_tifs_tbl', 0, use_in_mem)

    if not arcpy.Exists(OUTPUT_GDB):
        arcpy.CreateFileGDB_management(os.path.dirname(OUTPUT_GDB), os.path.basename(OUTPUT_GDB))
    
    
    pp_c.log_info ('Getting vegetation rasters from %s' % VEG_MOSAIC_GDB, None)
    arcpy.management.ExportMosaicDatasetPaths(VEG_MOSAIC_RST, veg_tif_names, '', "ALL", "RASTER")
    veg_tif_specs = [attrs for attrs in arcpy.da.SearchCursor(veg_tif_names, ['SourceOID', 'path'])]
    
    # veg_tif_specs = veg_tif_specs[0:100]


    if PROCESSORS > 1:
        p = multiprocessing.Pool(PROCESSORS)
        street_spaces_fcs = p.map(__tile_to_spaces_mp, sorted(veg_tif_specs), 1)
        p.close()  
    else:
        street_spaces_fcs = []
        for veg_tif_spec in sorted(veg_tif_specs):
            street_spaces_fcs.append(__tile_to_spaces_mp(veg_tif_spec)) 
            
    pp_c.log_debug (str(street_spaces_fcs))           

    pp_c.log_info ('Creating final output: %s ' % FINAL_FC, None)
    __delete_if_exists(FINAL_FC)
    arcpy.CreateFeatureclass_management(os.path.dirname(FINAL_FC), os.path.basename(FINAL_FC), "POLYGON", street_spaces_fcs[0], spatial_reference=street_spaces_fcs[0])
    arcpy.management.Append([s for s in street_spaces_fcs if s is not None], FINAL_FC, 'NO_TEST')


    return    

def __tile_to_spaces_mp (veg_tif_spec):
    idx, veg_tif = veg_tif_spec
    pp_c.log_info ("Processing vegetatition tif %i" % idx)
    
    arcpy.env.overwriteOutput = True
    use_in_mem = True
    
    retry_max = 5       
    for retry_count in range (0, retry_max):
    
        try:         
            intermediate_output_gdb =  pp_c.prepare_intermediate_output_gdb (False)
           
            out_fc = pp_c.get_intermediate_name (intermediate_output_gdb, 'out_fc', idx, False)
            veg_fc = pp_c.get_intermediate_name (intermediate_output_gdb, 'vpy_veg_fc', idx, False)
            land_use_clipped_fc = pp_c.get_intermediate_name (intermediate_output_gdb, 'luc_land_use_clipped_fc', idx, use_in_mem)
            veg_transport_fc = pp_c.get_intermediate_name (intermediate_output_gdb, 'vtp_veg_fc', idx, use_in_mem)
            land_cover_clipped_fc = pp_c.get_intermediate_name (intermediate_output_gdb, 'lcc_land_cover_clipped_fc', idx, use_in_mem)
            trees_rst = __get_intermediate_tif_name (None, 'trees', 1, use_in_mem)
            trees_fc = pp_c.get_intermediate_name (intermediate_output_gdb, 'trees_fc', 1, use_in_mem)  
            trees_expanded_fc = pp_c.get_intermediate_name (None, 'trees_expanded_fc', 1, use_in_mem) 
        
            pp_c.log_debug ('Converting vegetation to polygons: %s' % veg_tif, None)
            arcpy.conversion.RasterToPolygon(
                in_raster=veg_tif,
                out_polygon_features=veg_fc,
                simplify="SIMPLIFY",
                create_multipart_features="SINGLE_OUTER_PART",
                max_vertices_per_feature=None
            )
            pp_c.log_debug ('Conversion complete. %s records' % (arcpy.GetCount_management(veg_fc)), None)
        
                
            pp_c.log_debug ('Clip land use to tile')
            orig_extent = arcpy.env.extent
            arcpy.env.extent = arcpy.da.Describe(veg_fc)['extent']
            arcpy.CopyFeatures_management(LANDUSE, land_use_clipped_fc)
            arcpy.env.extent = orig_extent
             
            pp_c.log_debug ('Creating land use transport layer', None)
            transport_lyr = arcpy.MakeFeatureLayer_management(land_use_clipped_fc, "transport_lyr_%i" % idx, "LandUse = 7").getOutput(0)
                
            pp_c.log_debug ('Reducing vegetation polygons to transportation layer', None)
            arcpy.analysis.PairwiseIntersect([veg_fc, transport_lyr], veg_transport_fc)
            pp_c.delete([transport_lyr])
        
            pp_c.log_debug ('Filtering out very small spaces')
            veg_big_lyr = arcpy.management.MakeFeatureLayer(veg_transport_fc, "veg_big_lyr_%i" % idx, "Shape_Area > 20").getOutput(0)
        
        
            pp_c.log_debug ('Clip land cover to tile')
            arcpy.Clip_management (LANDCOVER, None, land_cover_clipped_fc, in_template_dataset=veg_fc)
            pp_c.delete([veg_fc])
                        
            # Reclassify Landcover trees=1
            remap = "0 NODATA;1 1;2 NODATA;3 NODATA;4 NODATA;5 NODATA;6 NODATA;7 NODATA"
            __reclassify_raster ( (land_cover_clipped_fc, remap, trees_rst) )    
        
            __raster_to_polygon ( (trees_rst, trees_fc))
            pp_c.delete([trees_rst])    
        
            # Buffer out trees
            __expand_polygons (trees_fc, "10 Feet", trees_expanded_fc)
            pp_c.delete([trees_fc])
        
            
            pp_c.log_debug ('Creating final output: %s' % (out_fc), None)
            arcpy.analysis.Erase(veg_big_lyr, trees_expanded_fc, out_fc)
            pp_c.delete([veg_big_lyr.name, trees_fc])
        
            pp_c.log_debug ('Finished:  %s polygons' % arcpy.GetCount_management(out_fc), None)
            return out_fc
        
        except Exception as ex:
            pp_c.log_debug ('Exception: %s' % (str(ex)))
            pp_c.log_debug (str(traceback.format_exc()))
            if retry_count < retry_max:
                pp_c.log_info ('Failed - retrying')
                
    pp_c.log_info ('Failed')
    return None
                

def __raster_to_polygon (spec):
    in_raster, out_fc = spec
    __delete_if_exists (out_fc)

    pp_c.log_debug ('Converting raster to polygon: %s ' % str(spec), None)
    arcpy.RasterToPolygon_conversion(in_raster, out_fc, "SIMPLIFY", "", "SINGLE_OUTER_PART", "")
    pp_c.log_debug ('Conversion complete. %s records' % (arcpy.GetCount_management(out_fc)), None)
    return  


def __reclassify_raster (spec):
    in_raster, remap, out_raster = spec
    __delete_if_exists (out_raster)

    pp_c.log_debug ('Classifying: %s ' % str(spec), None)
    raster_obj = arcpy.sa.Reclassify(in_raster,  reclass_field="Value", remap=remap, missing_values="DATA")
    pp_c.log_debug ('Saving reclassified raster to %s' % (out_raster), None)
    raster_obj.save(out_raster)
    pp_c.log_debug ('Reclassify complete', None)
    return



def __expand_polygons (in_fc, distance, out_fc):
    __delete_if_exists (out_fc)
    
    pp_c.log_debug ('Expanding %s record in  %s by %s' % (arcpy.GetCount_management(in_fc), in_fc, distance), None)
    arcpy.analysis.PairwiseBuffer(
    in_features=in_fc,
    out_feature_class=out_fc,
    buffer_distance_or_field=distance,
    dissolve_option="NONE",
    dissolve_field=None,
    method="PLANAR",
    max_deviation="0 Feet")
    pp_c.log_debug ('Expansion complete', None)
    return
    
        
def __delete_if_exists (f):
    if arcpy.Exists(f):
        pp_c.log_debug ('Deleting %s' % (f), None)
        arcpy.Delete_management(f)    
    return
        
def __get_intermediate_tif_name (intermediate_output, name, idx, use_in_mem):
    return pp_c.get_intermediate_name (intermediate_output, name, idx, use_in_mem, '.tif' if use_in_mem else '')


if __name__ == '__main__':
     run()
            