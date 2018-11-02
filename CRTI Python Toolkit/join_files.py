# -*- coding: utf-8 -*-

# To run from Spyder iPython console:
#runfile('D:/CRTI/python_projects/ArcGIS-scripts/CRTI Python Toolkit/join_files.py', args="\
#'D:/CRTI/GIS data/Dupage_with_NDVI/DuPage_crowns_intersecting_TreeInventory.shp' \
#'D:/CRTI/GIS data/Dupage_with_NDVI/csvs\DuPage_NDVI_tree_polys_nearInvTrees.csv' \
#'TreeNum' \
#'TreeNum' \
#'NDVI_MEAN;NDVI_MAX;NDVI_STD' \
#'D:/temp/shp_test/join.shp' \
#")
 

#
# When using using fn_left_mem instead of fn_left in the join, the time went from 
# 189 minutes to under 2 minutes
#



import sys
import common_functions
common_functions.add_arcgis_to_sys_path()
import arcpy

def log (message):
    common_functions.log(message)
    

    
def import_if_text_file (in_file, temporary_assets) :
    in_file_desc = arcpy.Describe(in_file)
    if in_file_desc.dataType == 'TextFile':
        log('Importing into in-memory geodatabase table:  ' + in_file)
        in_mem_file = 'in_memory\\' + in_file_desc.baseName
        arcpy.CopyRows_management(in_file, in_mem_file)
        temporary_assets.append(in_mem_file)
        return in_mem_file
    else:
        return in_file
                                  
    
def join(fn_left, fn_right, join_attr_left, join_attr_right, include_fields_right, shp_out):
    temporary_assets = list()
    try:              
        common_functions.create_index (fn_left, [join_attr_left], 'LeftIdx')
        common_functions.create_index (fn_right, [join_attr_right], 'RightIdx')
        
        fn_left = import_if_text_file (fn_left, temporary_assets)
        fn_right = import_if_text_file (fn_right, temporary_assets)
            
#        fn_left = common_functions.move_to_in_memory (fn_left, temporary_assets)
#        fn_right = common_functions.move_to_in_memory (fn_right, temporary_assets)
           
        log("Joining files")
        shp = arcpy.JoinField_management(fn_left, join_attr_left, fn_right, join_attr_right, include_fields_right)
        
        log("Copying results to persistent shape file: " + shp_out)
        arcpy.Delete_management(shp_out)  
        arcpy.CopyFeatures_management(shp, shp_out)
    except Exception as e:
        log("Exception: " + str(e))
        arcpy.AddError(str(e))
        raise
    finally:
        # Clean up    
        for temporary_asset in temporary_assets:    
            log('Deleting ' + temporary_asset)
            arcpy.Delete_management(temporary_asset)
        log("Done")

if __name__ == '__main__':
     join(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6])