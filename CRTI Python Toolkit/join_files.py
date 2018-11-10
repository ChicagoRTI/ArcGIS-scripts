# To run from Spyder iPython console:
#   runfile('D:/CRTI/python_projects/ArcGIS-scripts/CRTI Python Toolkit/join_files.py', wdir='D:/CRTI/python_projects/ArcGIS-scripts/CRTI Python Toolkit', args="'C:\Users\Don\Documents\ArcGIS\scratch.gdb\canopies_without_ndvi' 'PolygonId' 'C:\Users\Don\Documents\ArcGIS\scratch.gdb\zonal_ndvi' 'PolygonId' 'MAX;MEAN;STD'")
#
# This modules the equivalent of and SQl LEFT OUTER JOIN. It performs much better than the arcGIS JoinField tool. It
# does not work on in_memory feature classes.
#
# The key to this implementation is that both files are sorted so each file has to be traversed
# only once, from start to finish

import sys
import common_functions
common_functions.add_arcgis_to_sys_path()
import arcpy

def log (message):
    common_functions.log(message)
    return

# This generator returns the next row every time the next() method is called. 
def right_side_row_gen (right_side_fc, right_side_include_fields, right_side_key):
    with arcpy.da.SearchCursor(right_side_fc, right_side_include_fields, sql_clause=['DISTINCT', 'ORDER BY ' + right_side_key]) as cursor:
        for row in cursor:
            yield row
            
            
def left_side_add_fields (left_side_fc, field_list):
    for i in range(len(field_list)):
        name = field_list[i].name
        type = field_list[i].type
        if type in ['Integer','OID']:
            arcpy.AddField_management(left_side_fc, name, field_type='LONG')
        elif type == 'String':
            arcpy.AddField_management(left_side_fc, name, field_type='TEXT',field_length=field_list[i].length)
        elif type == 'Double':
            arcpy.AddField_management(left_side_fc, name, field_type='DOUBLE')
        elif type == 'Date':
            arcpy.AddField_management(left_side_fc, name, field_type='DATE')
        else:
            arcpy.AddError('Unknown field type: {0} for field: {1}'.format(type,name))    
            

def join (left_side_fc, left_side_key, right_side_fc, right_side_key, right_side_include_fields):
    log('Join left side: ' + left_side_fc)
    log('Join right side: ' + right_side_fc)
    log('Join keys: ' + str(left_side_key) + ':' + str(right_side_key))
    
    common_functions.create_index (left_side_fc, [left_side_key], 'LeftIdx')
    common_functions.create_index (right_side_fc, [right_side_key], 'RightIdx')
    
    # Update the left side feature class with the fields from the right side (they will be populated in the next step)
    left_side_add_fields (left_side_fc, [f for f in arcpy.ListFields(right_side_fc) if f.name in right_side_include_fields.split(';')]);
    
    # Prepare to write values to left side
    right_side_cursor = right_side_row_gen(right_side_fc, [right_side_key] + right_side_include_fields.split(';'), right_side_key)
    right_side_row = right_side_cursor.next()
    
    # Since both cursors return rows sorted, we simply advance then in tandem. When we find a matching
    # key, we simply copy to specified right hand fields into the left side feature class 
    # the matching keys
    count = int(arcpy.GetCount_management(left_side_fc).getOutput(0))
    arcpy.SetProgressor("step", "Joining files...", 0, count, 1)
    i = 0
    with arcpy.da.UpdateCursor(left_side_fc, [left_side_key] + right_side_include_fields.split(';'), sql_clause=(None, 'ORDER BY ' + left_side_key)) as left_side_cursor:
        for left_side_row in left_side_cursor:
            i += 1
            common_functions.log_progress("Joining record ", count, i)
            try:
                while left_side_row[0] > right_side_row[0]:
                    right_side_row = right_side_cursor.next()
                if left_side_row[0] == right_side_row[0]:
                    left_side_cursor.updateRow(right_side_row)
            except StopIteration:
                arcpy.AddWarning('End of join table.')
                break
    del left_side_cursor
    
    log('Done.')



if __name__ == '__main__':
     join(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])