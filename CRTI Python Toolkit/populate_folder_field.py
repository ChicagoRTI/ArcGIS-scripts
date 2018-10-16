# To run from Spyder iPython console:
#   runfile('D:/CRTI/python_projects/ArcGIS-scripts/CRTI Python Toolkit/populate_folder_field.py', wdir='D:/CRTI/python_projects/ArcGIS-scripts/CRTI Python Toolkit', args="'D:/Temp/shp_test' 'TileId' 'FC_NAME'")

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

def populate_mp (fcs, field_name, field_value, log_file):
    try:
        # Add a new attribute to all of the shape files, then populate it with the shape file name
        fc_count = 0
        for fc in fcs:
            if fc_count % ((len(fcs)/10)+1) == 0:
                common_functions.log_mp(log_file, 'Populating ' + field_name + ' with ' + field_value + ' in ' + fc + ' (' + str(fc_count) + ' of ' + str(len(fcs)) + ')')
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
            fc_count = fc_count+1
    except Exception as e:
        common_functions.log_mp(log_file, "Exception: " + str(e))
        common_functions.log_mp(log_file, traceback.format_exc())
        arcpy.AddError(str(e))
        raise  
    
def populate (feature_class_folder, field_name, field_value):
    log (feature_class_folder)
    log (field_name)
    log_mp_fn = arcpy.env.scratchFolder + '/log_populate_field.txt'
    # Get a list of all requested feature classes
    arcpy.env.workspace = feature_class_folder
    fcs = [feature_class_folder + '/' + fc_name for fc_name in arcpy.ListFeatureClasses()]
            
    if len(fcs) > 100 and field_value != 'UNIQUE_ID': 
        # Use multiprocessing support to do the work
        multiprocessing.set_executable(os.path.join(common_functions.get_install_path(), 'pythonw.exe'))
        log('Launching ' + str(_threads) + ' worker processes')
        log('Logging multiprocess activity to ' + log_mp_fn)
        shps_lists = [ fcs[i::_threads] for i in xrange(_threads if _threads < len(fcs) else len(fcs)) ]
        p = multiprocessing.Pool(_threads)
        p.map(partial(populate_mp, field_name=field_name, field_value=field_value, log_file=log_mp_fn), shps_lists)
        p.close()
    else:
        import populate_field
        for fc in fcs:
            populate_field.populate (fc, field_name, field_value)

if __name__ == '__main__':
     populate(sys.argv[1], sys.argv[2], sys.argv[3])