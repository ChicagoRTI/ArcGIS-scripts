# To run from Spyder iPython console:
#   runfile('D:/CRTI/python_projects/ArcGIS-scripts/AddShapeNameAttr/add_shape_name_attr.py', wdir='D:/CRTI/python_projects/ArcGIS-scripts/AddShapeNameAttr', args="")


import arcpy
import glob

#__SHPfolder = r'\\FILER01\se\Action\GEODATA\NorthAmerica\US-Midwest\Illinois\Will_County\Will_TreeCrowns\Trees_WillCounty\Sample_tree_crowns'
__SHPfolder = r'D:\Temp\shp_test'
__attr = "NAME"


def add_attr ():
    # Get a list of all shape files in the specified folder
    shps = glob.glob(__SHPfolder + "\*.shp")
    
    # Add a new attribute to all of the shape files
    for shp in shps:
        print('Adding ' + __attr + ' attribute to ' + shp)
        arcpy.AddField_management(shp, __attr, "TEXT")
    
    # Populate the attribute in all of the shape files
    for shp in shps:
        name = shp.split('\\')[-1]
        name = name[:len(name)-4]
        print('Setting ' + __attr + ' attribute to ' + name)
        with arcpy.da.UpdateCursor(shp, [__attr]) as cursor: #field that will contain the Shapefile name
            for row in cursor:
                row[0] = name
                cursor.updateRow(row)
        del cursor


if __name__ == '__main__':
     add_attr()