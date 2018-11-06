# -*- coding: utf-8 -*-

# -*- coding: utf-8 -*-
"""
Created on Tue Mar 20 11:07:22 2018

@author: Don
"""
# To run from Spyder iPython console:
#   runfile('D:/CRTI/python_projects/ArcGIS-scripts/CRTI Python Toolkit/compute_zonal_stats.py', wdir='D:/CRTI/python_projects/ArcGIS-scripts/CRTI Python Toolkit', args="'C:\Users\Don\Documents\ArcGIS\scratch.gdb\canopies_without_ndvi' 'PolygonId' 'C:\Users\Don\Documents\ArcGIS\scratch.gdb\merged_ndvi_rasters' 'D:\Temp\scratch.gdb\zonal_ndvi'")
#
# Make sure the ArcGIS components are in the system path (from C:\Program Files (x86)\ArcGIS\Desktop10.6\Support\Python/Desktop10.6.pth)
#
# NOTE:
#  This custom code is required because ArcGIS can not handle feature sets with more
#  then 170,000 records.  https://support.esri.com/en/technical-article/000012343
#

import sys
import os
import common_functions
common_functions.add_arcgis_to_sys_path()
import arcpy

_CHUNK_SIZE = 150000  # Documented limit is 170,000 


def log (message):
    common_functions.log(message)
    return

def get_zone_val_chunks (fc, zone_field):
    # Get a sorted list of all of the zone field values. Note that this could be done as a list
    # but it was generating out of memory errors when done that way
    zone_vals = [0] * int(arcpy.GetCount_management(fc).getOutput(0))
    with arcpy.da.SearchCursor(fc, [zone_field], '','', False, sql_clause=['DISTINCT', 'ORDER BY ' + zone_field + ' ASC']) as cursor:
        i = 0
        for attrs in cursor:
            zone_vals[i] = attrs[0]
            i += 1
    del cursor

    # Create equal size chunks out of the list of values    
    zone_vals_list = [zone_vals[j:j + _CHUNK_SIZE] for j in range(0, len(zone_vals), _CHUNK_SIZE)] 
    # All we really need is the min and max value for each chunk. So to conserve memory create
    # a list of tuples where each tuple represent those values  (chunk_min_zone_val, chunk_max_zone_val)
    zone_val_chunks = [(zone_val[0], zone_val[len(zone_val)-1]) for zone_val in zone_vals_list]
    return zone_val_chunks
    

def compute (fc_input, zone_field, rasters, fc_output):
    arcpy.CheckOutExtension("Spatial")
    temporary_assets = list()
    
    try:
        # Create an index on the zone field
        common_functions.create_index (fc_input, [zone_field], 'ZoneIdx') 
        # Delete the output feature set
        arcpy.Delete_management(fc_output)
        
        # Get a list of zone field value ranges (chunks). In addition to circumventing the documented
        # 170000 record limitation, this also allows us to do the processing in memory
        zone_val_chunks = get_zone_val_chunks (fc_input, zone_field)

        # Prepare the in-memory feature classes
        fc_in_int = os.path.join('in_memory', 'fc_int')
        fc_out_int = os.path.join('in_memory', 'fc_out')
        temporary_assets += [fc_in_int, fc_out_int]
        
        i=0
        for zone_val_min, zone_val_max in zone_val_chunks:
            i += 1
            common_functions.log_progress("Processing segment", len(zone_val_chunks), i)
            # Create a feature class for this chunk
            where_clause = '("' + zone_field + '">=' + str(zone_val_min) + " AND " + '"' + zone_field + '"<=' + str(zone_val_max) + ')'            
            arcpy.FeatureClassToFeatureClass_conversion(fc_input, os.path.dirname(fc_in_int), os.path.basename(fc_in_int), where_clause)    
            # Compute the zonal stats for this chunk
            arcpy.sa.ZonalStatisticsAsTable(fc_in_int, zone_field, rasters, fc_out_int)
            # Append results to the output feature class
            if arcpy.Exists(fc_output):
                arcpy.Append_management(fc_out_int, fc_output)
            else:
                arcpy.CopyRows_management(fc_out_int, fc_output)
    
    finally:
        # Clean up  
        arcpy.CheckInExtension("Spatial")        
        for temporary_asset in temporary_assets:    
            log('Deleting ' + temporary_asset)
            arcpy.Delete_management(temporary_asset)
        log("Done")


if __name__ == '__main__':
     compute(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    
    



