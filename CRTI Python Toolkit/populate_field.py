# To run from Spyder iPython console:
#   runfile('D:/CRTI/python_projects/ArcGIS-scripts/CRTI Python Toolkit/populate_field.py', wdir='D:/CRTI/python_projects/ArcGIS-scripts/CRTI Python Toolkit', args="'D:/Temp/shp_test/Will County_tiles_tile00450.shp' 'TileId' 'FC_NAME'")

import sys
import common_functions
common_functions.add_arcgis_to_sys_path()
import arcpy

def log (message):
    common_functions.log(message)


def populate (feature_class, field_name, field_value):  
    log('Populating ' + field_name + ' with ' + field_value + ' in ' + feature_class)
    # Add the field if it does not already exist
    if len(arcpy.ListFields(feature_class, field_name)) == 0:
        if field_value == 'UNIQUE_ID':
            arcpy.AddField_management(feature_class, field_name, "LONG")
        else:
            arcpy.AddField_management(feature_class, field_name, "TEXT")
    # Figure out when the field value should be set to 
    fc_name = arcpy.Describe(feature_class).baseName
    with arcpy.da.UpdateCursor(feature_class, [field_name]) as cursor: 
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
   

if __name__ == '__main__':
     populate(sys.argv[1], sys.argv[2], sys.argv[3])