# To run from Spyder iPython console:
#   runfile('D:/CRTI/python_projects/ArcGIS-scripts/CRTI Python Toolkit/populate_field.py', wdir='D:/CRTI/python_projects/ArcGIS-scripts/CRTI Python Toolkit', args="'D:/Temp/shp_test/Will County_tiles_tile00450.shp,D:/Temp/shp_test/Will County_tiles_tile00451.shp' 'TileId' 'FC_NAME'")

import sys
import os
import multiprocessing
from functools import partial
import traceback
import common_functions
common_functions.add_arcgis_to_sys_path()
import arcpy

_FC =0
_FIELD_VALUE = 1
_FIELD_NAME = 2
_FIELD_TYPE = 3

_threads = multiprocessing.cpu_count()

def log (message):
    common_functions.log(message)
    return

def log_progress (message, max_range, step_count, threads=1):
    common_functions.log_progress (message, max_range, step_count, threads)
    


def get_field_action (fc, field_name, field_type):
    if len(arcpy.ListFields(fc, field_name)) == 0:
        return "Add"
    field = arcpy.ListFields(fc, field_name)[0]
    if field.type == field_type:
        return "Reuse"
    else:
        return "DeleteAdd"
        

    
def populate_fc (fc, field_name, field_value, field_type):
    
    # Prepare the field to be updated
    field_action = get_field_action (fc, field_name, field_type)
    if field_action == "DeleteAdd":
        arcpy.DeleteField_management(fc, field_name)
    if field_action == "Add" or field_action == "DeleteAdd":
        arcpy.AddField_management(fc, field_name, field_type)
        
    # Update the field
    fc_name = arcpy.Describe(fc).baseName
    with arcpy.da.UpdateCursor(fc, [field_name]) as cursor: 
        row_count = 1                
        for row in cursor:
            if field_value == 'FC_NAME':
                row[0] = fc_name
            elif field_value == 'UNIQUE_ID':
                row[0] = row_count
            else:
                row[0] = field_value
            cursor.updateRow(row)
            row_count = row_count + 1                
    del cursor


def populate_mp (tuple_list, scratch_ws):
    try:
        arcpy.env.scratchWorkspace = scratch_ws
        # Add a new attribute to all of the shape files, then populate it with the shape file name
        fc_count = 1
        for tuple_ in tuple_list:
            fc = tuple_[_FC]
            field_name = tuple_[_FIELD_NAME]
            field_value = tuple_[_FIELD_VALUE]
            field_type = tuple_[_FIELD_TYPE]
            log_progress ('Populating ' + field_name + ' with ' + str(field_value) + ' in ' + os.path.basename(fc), len(tuple_list), fc_count, _threads)    
            populate_fc (fc, field_name, field_value, field_type)    
            fc_count = fc_count+1
    except Exception as e:
        log("Exception: " + str(e))
        log(traceback.format_exc())
        arcpy.AddError(str(e))
        raise  

# Takes a list of tuples <feature_class, field_value, field_name, field_type>    
def populate (tuple_list):
    
    if len(tuple_list) > sys.maxint and 'UNIQUE_ID' not in [i[_FIELD_VALUE] for i in tuple_list]:  # turn off mp support due to ESRI bug
#    if len(tuple_list) > 1 and 'UNIQUE_ID' not in [i[_FIELD_VALUE] for i in tuple_list]:  # turn off mp support due to ESRI bug in AddField
        # Use multiprocessing support to do the work
        multiprocessing.set_executable(os.path.join(common_functions.get_install_path(), 'pythonw.exe'))
        log('Launching ' + str(_threads) + ' worker processes')
        tuple_lists = [tuple_list[i::_threads] for i in xrange(_threads if _threads < len(tuple_list) else len(tuple_list)) ]
        p = multiprocessing.Pool(_threads)
        p.map(partial(populate_mp, scratch_ws=arcpy.env.scratchWorkspace), tuple_lists)
        p.close()
    else:
        fc_count = 1
        for tuple_ in tuple_list:
            fc = tuple_[_FC]
            field_name = tuple_[_FIELD_NAME]
            field_value = tuple_[_FIELD_VALUE]
            field_type = tuple_[_FIELD_TYPE]
            common_functions.log_progress ('Populating ' + field_name + ' with ' + str(field_value) + ' in ' + fc,  len(tuple_list), fc_count)    
            populate_fc (fc, field_name, field_value, field_type)    
            fc_count = fc_count+1
            

if __name__ == '__main__':
     populate([tuple(sys.argv[1].split(','))])