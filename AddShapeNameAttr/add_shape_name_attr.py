# To run from Spyder iPython console:
#   runfile('D:/CRTI/python_projects/ArcGIS-scripts/AddShapeNameAttr/add_shape_name_attr.py', wdir='D:/CRTI/python_projects/ArcGIS-scripts/AddShapeNameAttr', args="'D:/Temp/shp_test' 'NAME'")

import arcpy
import glob

# Get the input arguments
__SHPfolder = arcpy.GetParameterAsText(0)
__attr = arcpy.GetParameterAsText(1)

def log (message):
    print (message)
    arcpy.AddMessage(message)
    
log (__SHPfolder)
log (__attr)

def add_attr ():
    # Get a list of all shape files in the specified folder
    shps = glob.glob(__SHPfolder + "\*.shp")
    
    # Add a new attribute to all of the shape files
    for shp in shps:
        log('Adding ' + __attr + ' attribute to ' + shp)
        arcpy.AddField_management(shp, __attr, "TEXT")
    
    # Populate the attribute in all of the shape files
    for shp in shps:
        name = shp.split('\\')[-1]
        name = name[:len(name)-4]
        log('Setting ' + __attr + ' attribute to ' + name)
        with arcpy.da.UpdateCursor(shp, [__attr]) as cursor: 
            for row in cursor:
                row[0] = name
                cursor.updateRow(row)
        del cursor


if __name__ == '__main__':
     add_attr()