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


_threads = multiprocessing.cpu_count()

def log (message):
    common_functions.log(message)
    
def populate_fc (fc, field_name, field_value):
    # Add the field if it does not already exist
    if len(arcpy.ListFields(fc, field_name)) == 0 :
        if field_value == 'UNIQUE_ID':
            arcpy.AddField_management(fc, field_name, "LONG")
        else:                    
            arcpy.AddField_management(fc, field_name, "TEXT")
    # Figure out what the field value should be set to 
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


def populate_mp (fcs, field_name, field_value, log_file):
    try:
        # Add a new attribute to all of the shape files, then populate it with the shape file name
        fc_count = 1
        for fc in fcs:
            common_functions.log_progress_mp (log_file, 'Populating ' + field_name + ' with ' + field_value + ' in ' + fc, len(fcs), fc_count)    
            populate_fc (fc, field_name, field_value)    
            fc_count = fc_count+1
    except Exception as e:
        common_functions.log_mp(log_file, "Exception: " + str(e))
        common_functions.log_mp(log_file, traceback.format_exc())
        arcpy.AddError(str(e))
        raise  

    
def populate (fcs, field_name, field_value):
            
    if len(fcs) > 1 and field_value != 'UNIQUE_ID': 
        # Use multiprocessing support to do the work
        log_mp_fn = os.path.join(arcpy.env.scratchFolder, 'log_mp.txt')
        multiprocessing.set_executable(os.path.join(common_functions.get_install_path(), 'pythonw.exe'))
        log('Launching ' + str(_threads) + ' worker processes')
        log('Logging multiprocess activity to ' + log_mp_fn)
        shps_lists = [ fcs[i::_threads] for i in xrange(_threads if _threads < len(fcs) else len(fcs)) ]
        p = multiprocessing.Pool(_threads)
        p.map(partial(populate_mp, field_name=field_name, field_value=field_value, log_file=log_mp_fn), shps_lists)
        p.close()
    else:
        fc_count = 1
        for fc in fcs:
            common_functions.log_progress ('Populating ' + field_name + ' with ' + field_value + ' in ' + fc, len(fcs), fc_count)    
            populate_fc (fc, field_name, field_value)    
            fc_count = fc_count+1
            

if __name__ == '__main__':
     populate(sys.argv[1].split(','), sys.argv[2], sys.argv[3])