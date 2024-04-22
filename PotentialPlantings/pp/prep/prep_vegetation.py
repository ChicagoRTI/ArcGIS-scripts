import arcpy
import pp.common as pp_c
import os
import multiprocessing
from shutil import rmtree
import traceback

import pp.logger
logger = pp.logger.get('pp_log')


# COUNTY_RASTER = 'https://gis.cookcountyil.gov/imagery/services/CookOrtho2017/ImageServer'
COUNTY_RASTER = r'C:\Users\dmorrison\crti\data\Potential Plantings\cook county aerial 2017\cook_county.gdb\othro_2017'

FIPS = '17031'

VEG_TIFS_DIR = os.path.join(pp_c.PREP_DIR, 'veg_tifs', FIPS)
VEG_MOSAIC_GDB = os.path.join(pp_c.PREP_DIR, 'streets.gdb')
VEG_MOSAIC_RST = os.path.join(VEG_MOSAIC_GDB, 'veg_mosaic')

RED_BAND = "1" 
NIR_BAND = "2"

PROCESSORS = 16

COUNTIES = 'https://services.arcgis.com/P3ePLMYs2RVChkJx/arcgis/rest/services/USA_Counties/FeatureServer/0'

SCRATCH_ALL_TIFS = True

FISHNET_DIMS = (100,100)

def run():
    
    pp_c.log_info ("Logging to %s" % pp.logger.LOG_FILE)
    
    arcpy.env.parallelProcessingFactor = "1"
    arcpy.env.overwriteOutput = True
       
    if SCRATCH_ALL_TIFS and os.path.isdir(VEG_TIFS_DIR):
        rmtree(VEG_TIFS_DIR)    
    os.makedirs(VEG_TIFS_DIR, exist_ok=True)

    intermediate_output_gdb =  pp_c.prepare_intermediate_output_gdb (False)
    fishnet_fc = pp_c.get_intermediate_name (intermediate_output_gdb, 'fishnet', 0, False)
    
    pp_c.log_info ("Building fishnet for tiles")
    county_boundary = arcpy.MakeFeatureLayer_management(COUNTIES, "county_layer", "FIPS = '%s'" % (FIPS)).getOutput(0)
    __get_fishnet (COUNTY_RASTER, county_boundary, FISHNET_DIMS[0], FISHNET_DIMS[1], fishnet_fc)

    pp_c.log_info ("Preparing tile specs")
    tiles = []
    with arcpy.da.SearchCursor(fishnet_fc, ['SHAPE@', 'objectid']) as cursor:
        for shape, oid in cursor:
            tiles.append ( (oid, '%i_veg.tif' % (oid), shape.extent.lowerLeft.X, shape.extent.lowerLeft.Y, shape.extent.upperRight.X, shape.extent.upperRight.Y, shape.extent.spatialReference.factoryCode) )
    pp_c.log_info ("%s tiles to be processed" % len(tiles))
    
    pp_c.delete ([fishnet_fc, county_boundary.name])
    
    # tiles = tiles[0:32]

    if PROCESSORS > 1:
        p = multiprocessing.Pool(PROCESSORS)
        veg_tifs = p.map(__tile_to_ndvi_mp, sorted(tiles), 1)
        p.close()  
    else:
        veg_tifs = []
        for tile_spec in sorted(tiles):
            veg_tifs.append(__tile_to_ndvi_mp(tile_spec))    

    pp_c.log_debug (str(veg_tifs))
    
    pp_c.log_info ("Creating mosaic dataset %s" % VEG_MOSAIC_RST)
    if arcpy.Exists(VEG_MOSAIC_RST):
        pp_c.delete ([VEG_MOSAIC_RST]) 
    arcpy.management.CreateMosaicDataset(os.path.dirname(VEG_MOSAIC_RST), os.path.basename(VEG_MOSAIC_RST), coordinate_system=arcpy.Describe(veg_tifs[0]).spatialReference, num_bands=1, pixel_type="1_BIT")


    pp_c.log_info ("Adding rasters to mosaic dataset %s" % VEG_MOSAIC_RST)
    arcpy.management.AddRastersToMosaicDataset(
        in_mosaic_dataset=VEG_MOSAIC_RST,
        raster_type="Raster Dataset",
        input_path=[v for v in veg_tifs if v is not None])

    pp_c.log_info ('Finished', None)
    return


def __get_fishnet (county_raster, clip_fc, rows, cols, out_fc):
    
    lyr = arcpy.MakeRasterLayer_management(county_raster, 'lyr').getOutput(0)
    extent = arcpy.da.Describe(lyr)['extent']

    fishnet_fc = os.path.join('in_memory', 'fishnet');
    pp_c.log_debug ("Create %i x %i fishnet" % (rows, cols))
    origin_coord = '%i %i' % (extent.lowerLeft.X, extent.lowerLeft.Y)
    y_axis_coord = '%i %i' % (extent.upperLeft.X, extent.upperLeft.Y)
    corner_coord = '%i %i' % (extent.upperRight.X, extent.upperRight.Y)
    arcpy.management.CreateFishnet(fishnet_fc, origin_coord, y_axis_coord, 0, 0, rows, cols, corner_coord, 'NO_LABELS', extent, 'POLYGON')
    
    pp_c.log_debug ("Clip fishnet to county")
    arcpy.analysis.Clip(fishnet_fc, clip_fc, out_fc)
    pp_c.delete([fishnet_fc, lyr.name])

    return


def __tile_to_ndvi_mp (spec):
    oid, veg_rst, x_min, y_min, x_max, y_max, sr_factory_code = spec
    pp_c.log_info ("Processing tile oid %i" % oid)

    arcpy.env.overwriteOutput = True
    
    retry_max = 5
    
    tifs_dir = os.path.join(VEG_TIFS_DIR, str(oid))
    tif_out = os.path.join(tifs_dir, veg_rst)
    
    if not SCRATCH_ALL_TIFS and arcpy.Exists(tif_out):
        return tif_out

    extent = arcpy.Extent(x_min, y_min, x_max, y_max,  spatial_reference=arcpy.SpatialReference(sr_factory_code) )
   
    for retry_count in range (0, retry_max):
    
        try:           
            if os.path.isdir(tifs_dir):
                rmtree(tifs_dir)
            os.makedirs(tifs_dir, exist_ok=True)
                        
            lyr = arcpy.MakeRasterLayer_management(COUNTY_RASTER, 'lyr_%i' % oid).getOutput(0)
        
            tile_raster_red_lyr = arcpy.MakeRasterLayer_management(lyr, 'tile_raster_red_lyr_%i' % oid, envelope=extent, band_index=RED_BAND).getOutput(0)
            tile_raster_nir_lyr = arcpy.MakeRasterLayer_management(lyr, 'tile_raster_nir_lyr_%i' % oid, envelope=extent, band_index=NIR_BAND).getOutput(0)
        
            # Calcualte NDVI of the sample area    
            pp_c.log_debug ('Calculating NDVI', str(oid))
            red = arcpy.sa.Float(arcpy.sa.Raster(tile_raster_red_lyr.name))
            nir = arcpy.sa.Float(arcpy.sa.Raster(tile_raster_nir_lyr.name))
            pp_c.delete ([tile_raster_red_lyr.name, tile_raster_nir_lyr.name, lyr.name])
            
            ndvi = (nir - red) / (nir + red)
            ndvi_rst = os.path.join(tifs_dir, '%i_ndvi_rst.tif' % oid)
            ndvi.save(ndvi_rst)
            pp_c.delete ([red, nir])
            
            # Reclassify NDVI  <0: non-vegetation (0),  >0: vegetation (1)
            spec = "-1 0 0;0 1 1"
            pp_c.log_debug ('Classifying: %s ' % str(spec), str(oid))
            reclass_raster_obj = arcpy.sa.Reclassify(ndvi_rst,  reclass_field="Value", remap=spec, missing_values="DATA")
            pp_c.delete([ndvi_rst])
            
            pp_c.log_debug ('Running Majority filter to clean out noise', str(oid))
            arcpy.BuildRasterAttributeTable_management(reclass_raster_obj, "Overwrite")
            filtered_raster_obj = arcpy.sa.MajorityFilter(reclass_raster_obj, "EIGHT", "MAJORITY") 
            pp_c.delete([reclass_raster_obj])   
            
            pp_c.log_debug ('Reducing to 1 bit pixel depth', str(oid))
            
            one_bit_rst = tif_out
            
            # one_bit_rst = os.path.join(tifs_dir, '%i_one_bit_rst.tif' % oid)            
            arcpy.management.CopyRaster(filtered_raster_obj, one_bit_rst, pixel_type="1_BIT")
            pp_c.delete([filtered_raster_obj])
            arcpy.management.SetRasterProperties(one_bit_rst,  nodata="1 0")
            
            # pp_c.log_debug ('Shifting raster', str(oid))
            # arcpy.management.Shift(one_bit_rst, tif_out, x_value=-2.5, y_value=3.0)
            # pp_c.delete([one_bit_rst])
 
            return tif_out
        
        except Exception as ex:
            pp_c.log_debug ('Exception: %s' % (str(ex)))
            pp_c.log_debug (str(traceback.format_exc()))
            if retry_count >= retry_max:
                pp_c.log_info ('Failed')
                return None
            else:
                pp_c.log_info ('Failed - retrying')




            

if __name__ == '__main__':
     run()
            