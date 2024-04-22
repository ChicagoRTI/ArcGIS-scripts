import arcpy
import pp.common as pp_c
import os

import pp.logger
logger = pp.logger.get('pp_log')


LANDUSE_GDB = os.path.dirname(pp_c.LANDUSE_FC)

def run():
    
    pp_c.log_info ("Logging to %s" % pp.logger.LOG_FILE)
    
    arcpy.env.parallelProcessingFactor = "4"
    
    os.makedirs(pp_c.PREP_DIR, exist_ok=True)
    
    records = arcpy.GetCount_management(pp_c.LANDUSE_STRATIFIED_FC)
    
    if not arcpy.Exists(LANDUSE_GDB):
        arcpy.CreateFileGDB_management(os.path.dirname(LANDUSE_GDB), os.path.basename(LANDUSE_GDB))

    if arcpy.Exists(pp_c.LANDUSE_FC):
        pp_c.delete ([pp_c.LANDUSE_FC]) 
    
    arcpy.CreateFeatureclass_management(os.path.dirname(pp_c.LANDUSE_FC), os.path.basename(pp_c.LANDUSE_FC), "POLYGON", spatial_reference=arcpy.SpatialReference(102670))
    arcpy.AddField_management(pp_c.LANDUSE_FC, 'LandUse', 'SHORT')

    pp_c.log_info ("Updating %s" % pp_c.LANDUSE_FC)
    with arcpy.da.SearchCursor(pp_c.LANDUSE_STRATIFIED_FC, ['Shape@', 'NEW']) as search_cursor:
        with arcpy.da.InsertCursor(pp_c.LANDUSE_FC, ['Shape@', 'LandUse']) as insert_cursor: 
            i = 0
            for shape, lu_str in search_cursor:
                if i%50000 == 0:
                    pp_c.log_info ("Record %i of %s" % (i, records))                   
                insert_cursor.insertRow([shape, pp_c.LANDUSE_DOMAIN[lu_str]])
                i=i+1               

    pp_c.log_info ('Finished', None)
    return


if __name__ == '__main__':
     run()
            