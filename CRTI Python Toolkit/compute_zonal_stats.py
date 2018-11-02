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



def compute (fc_input, zone_field, rasters, fc_output):
    arcpy.CheckOutExtension("Spatial")
    temporary_assets = list()
    
    try:
        # Create an index on the zone field
        common_functions.create_index (fc_input, [zone_field], 'ZoneIdx') 
        # Delete the output feature set
        arcpy.Delete_management(fc_output)

        # Get all of the polygon IDs
        p_ids = list()
        with arcpy.da.SearchCursor(fc_input, [zone_field], '','', False) as cursor:
            for attrs in cursor:
                p_ids.append(attrs[0])
        del cursor
        
        # Sort the list and chunk it up
        p_ids.sort()
        p_ids_list = [p_ids[i:i+_CHUNK_SIZE] for i in range(0, len(p_ids), _CHUNK_SIZE)] 
        
        fc_in_int = os.path.join('in_memory', 'fc_int')
        fc_out_int = os.path.join('in_memory', 'fc_out')
        temporary_assets += [fc_in_int, fc_out_int]
        
        i=0
        for p_ids in p_ids_list:
            i += 1
            common_functions.log_progress("Processing segment", len(p_ids_list), i)
            # Create a feature class for this chunk
            p_id_min = p_ids[0]
            p_id_max = p_ids[len(p_ids)-1]
            where_clause = """{0} >= {1} AND {2} <= {3}""".format(arcpy.AddFieldDelimiters(fc_in_int, zone_field), p_id_min,arcpy.AddFieldDelimiters(fc_in_int, zone_field), p_id_max)
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
    
    



