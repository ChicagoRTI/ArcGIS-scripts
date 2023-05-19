import arcpy
import pp.common as pp_c
import os

import pp.logger
logger = pp.logger.get('pp_log')


LANDUSE_IN = r'C:\Users\dmorrison\crti\data\Potential Plantings\landuse\2018CMAPLU_stratified.shp'

LANDUSE_GDB = os.path.join(pp_c.PREP_DIR, 'landuse.gdb')
LANDUSE_OUT_FC = os.path.join(LANDUSE_GDB, 'landuse')

DOMAIN_MAP = {
	'Agriculture': 1,
	'Commercial': 2,
	'Industrial': 3,
	'Institutional': 4,
	'Natural area': 5,
	'Residential': 6,
	'Transit': 7,
	'Vacant': 8,
	'Golf': 9,
	'Park': 10,
	'Utility': 11,
	'Other': 12,
    }


def run():
    
    pp_c.log_info ("Logging to %s" % pp.logger.LOG_FILE)
    
    arcpy.env.parallelProcessingFactor = "4"
    
    os.makedirs(pp_c.PREP_DIR, exist_ok=True)
    
    records = arcpy.GetCount_management(LANDUSE_IN)
    
    if not arcpy.Exists(LANDUSE_GDB):
        arcpy.CreateFileGDB_management(os.path.dirname(LANDUSE_GDB), os.path.basename(LANDUSE_GDB))

    if arcpy.Exists(LANDUSE_OUT_FC):
        pp_c.delete ([LANDUSE_OUT_FC]) 
    
    arcpy.CreateFeatureclass_management(os.path.dirname(LANDUSE_OUT_FC), os.path.basename(LANDUSE_OUT_FC), "POLYGON", spatial_reference=arcpy.SpatialReference(102670))
    arcpy.AddField_management(LANDUSE_OUT_FC, 'LandUse', 'SHORT')

    pp_c.log_info ("Updating %s" % LANDUSE_OUT_FC)
    with arcpy.da.SearchCursor(LANDUSE_IN, ['Shape@', 'NEW']) as search_cursor:
        with arcpy.da.InsertCursor(LANDUSE_OUT_FC, ['Shape@', 'LandUse']) as insert_cursor: 
            i = 0
            for shape, lu_str in search_cursor:
                if i%50000 == 0:
                    pp_c.log_info ("Record %i of %s" % (i, records))                   
                insert_cursor.insertRow([shape, DOMAIN_MAP[lu_str]])
                i=i+1               

    pp_c.log_info ('Finished', None)
    return


if __name__ == '__main__':
     run()
            