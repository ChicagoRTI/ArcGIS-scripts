import arcpy
import pp.common as pp_c
import os
import multiprocessing
from shutil import rmtree
import traceback

import pp.logger
logger = pp.logger.get('pp_log')


COUNTY_RASTER = 'https://gis.cookcountyil.gov/imagery/services/CookOrtho2017/ImageServer'

FIPS = '17031'

BASE_DIR = r'C:\Users\dmorrison\crti\data\Potential Plantings\cook county aerial 2017'
TIFS_DIR = os.path.join(BASE_DIR, 'tifs')
MOSAIC_GDB = os.path.join(BASE_DIR, 'cook_county.gdb')
MOSAIC_RST = os.path.join(MOSAIC_GDB, 'othro_2017')

PROCESSORS = 4

COUNTIES = 'https://services.arcgis.com/P3ePLMYs2RVChkJx/arcgis/rest/services/USA_Counties/FeatureServer/0'

SCRATCH_ALL_TIFS = False


def run():
    
    pp_c.log_info ("Logging to %s" % pp.logger.LOG_FILE)
    
    arcpy.env.parallelProcessingFactor = "1"
    arcpy.env.overwriteOutput = True
       
    if SCRATCH_ALL_TIFS and os.path.isdir(TIFS_DIR):
        rmtree(TIFS_DIR)    
    os.makedirs(TIFS_DIR, exist_ok=True)

    intermediate_output_gdb =  pp_c.prepare_intermediate_output_gdb (False)
    fishnet_fc = pp_c.get_intermediate_name (intermediate_output_gdb, 'fishnet', 0, False)
    
    pp_c.log_info ("Building fishnet for tiles")
    county_boundary = arcpy.MakeFeatureLayer_management(COUNTIES, "county_layer", "FIPS = '%s'" % (FIPS)).getOutput(0)
    __get_fishnet (COUNTY_RASTER, county_boundary, 100, 100, fishnet_fc)

    pp_c.log_info ("Preparing tile specs")
    tiles = []
    with arcpy.da.SearchCursor(fishnet_fc, ['SHAPE@', 'objectid']) as cursor:
        for shape, oid in cursor:
            tiles.append ( (oid, '%i_tile.tif' % (oid), shape.extent.lowerLeft.X, shape.extent.lowerLeft.Y, shape.extent.upperRight.X, shape.extent.upperRight.Y, shape.extent.spatialReference.factoryCode) )
    pp_c.log_info ("%s tiles to be processed" % len(tiles))
    
    pp_c.delete ([fishnet_fc, county_boundary.name])
    
    # tiles = tiles[4625:]

    if PROCESSORS > 1:
        p = multiprocessing.Pool(PROCESSORS)
        tifs = p.map(__copy_tile_mp, sorted(tiles), 1)
        p.close()  
    else:
        tifs = []
        for tile_spec in sorted(tiles):
            tifs.append(__copy_tile_mp(tile_spec))    

    pp_c.log_debug (str(tifs))
    
    pp_c.log_info ("Creating mosaic dataset %s" % MOSAIC_RST)
    if arcpy.Exists(MOSAIC_RST):
        pp_c.delete ([MOSAIC_RST]) 
    arcpy.management.CreateMosaicDataset(os.path.dirname(MOSAIC_RST), os.path.basename(MOSAIC_RST), coordinate_system=arcpy.Describe(tifs[0]).spatialReference, num_bands=2, pixel_type="8_BIT_UNSIGNED")


    pp_c.log_info ("Adding rasters to mosaic dataset %s" % MOSAIC_RST)
    arcpy.management.AddRastersToMosaicDataset(
        in_mosaic_dataset=MOSAIC_RST,
        raster_type="Raster Dataset",
        input_path=[v for v in tifs if v is not None])

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


def __copy_tile_mp (spec):
    oid, rst, x_min, y_min, x_max, y_max, sr_factory_code = spec
    pp_c.log_info ("Processing tile oid %i" % oid)

    arcpy.env.overwriteOutput = True
    
    retry_max = 5
    
    tifs_dir = os.path.join(TIFS_DIR, str(oid))
    tif_out = os.path.join(tifs_dir, rst)
    
    if not SCRATCH_ALL_TIFS and arcpy.Exists(tif_out):
        return tif_out

    extent = arcpy.Extent(x_min, y_min, x_max, y_max,  spatial_reference=arcpy.SpatialReference(sr_factory_code) )
   
    for retry_count in range (0, retry_max):
    
        try:           
            if os.path.isdir(tifs_dir):
                rmtree(tifs_dir)
            os.makedirs(tifs_dir, exist_ok=True)
                        
            lyr = arcpy.MakeRasterLayer_management(COUNTY_RASTER, 'lyr_%i' % oid, envelope=extent, band_index="1;4").getOutput(0)
            lyr_rst = arcpy.sa.Raster(lyr.name)
            lyr_rst.save(tif_out)
            pp_c.delete ([lyr.name])
  
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
            