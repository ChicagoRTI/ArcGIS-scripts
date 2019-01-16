# -*- coding: utf-8 -*-
"""
Created on Tue Mar 20 11:07:22 2018

@author: Don
"""
# To run from Spyder iPython console:
#   runfile('D:/CRTI/python_projects/ArcGIS-scripts/CRTI Python Toolkit/adjacent_canopy_comp/adjacent_canopy_comp.py', wdir='D:/CRTI/python_projects/ArcGIS-scripts/CRTI Python Toolkit/adjacent_canopy_comp/', args="'D:/Temp/Downloads/SevenCountyByMuni/SevenCountyByMuni.shp' 'D:/temp/canopy_comps'")
#
# To run under ArcGIS python:
#   cd D:\CRTI\python_projects\ArcGIS-scripts\CRTI Python Toolkit\adjacent_canopy_comp\
#   C:\Python27_ArcGIS\ArcGIS10.6\python -m adjacent_canopy_comp "D:/Temp/Downloads/SevenCountyByMuni/SevenCountyByMuni.shp" "Schaumburg" "D:/temp/canopy_comps.csv"

# Make sure the ArcGIS components are in the system path (from C:\Program Files (x86)\ArcGIS\Desktop10.6\Support\Python/Desktop10.6.pth)
import os
import sys

__arc_gis_dir = "C:\\Program Files (x86)\\ArcGIS\\Desktop10.6\\"
__arc_gis_path = [__arc_gis_dir + "bin",
                __arc_gis_dir + "ArcPy",
                __arc_gis_dir + "ArcToolBox\Scripts"]
for p in __arc_gis_path: 
    if p not in sys.path: sys.path += [p]


import arcpy


__fields_to_keep = {
        "NAME" : "Municipality",
        "CANOPY" : "Canopy",
        "GRASS_SHRU" : "Vegetation",
        "BARE_SOIL" : "Bare Soil",
        "WATER" : "Water",
        "BUILDING" : "Buildings",
        "ROADS_RAIL" : "Roads/Rail",
        "OTHER_PAVE" : "Other Paved"
        }



def main_process_shape_file (fc_input, output_csv_dir):
    print (fc_input)
    print (output_csv_dir)
    arcpy.env.overwriteOutput = True

    all_municipalities_layer = os.path.join(arcpy.env.scratchGDB, 'all_municipalities')
    selected_municipality_layer = os.path.join(arcpy.env.scratchGDB, 'selected_municipality')
    selected_municipality_fc = os.path.join(arcpy.env.scratchGDB, 'adjacent_comps')
    adjacent_municipalities_fc = os.path.join(arcpy.env.scratchGDB, 'adjacent_municipalities')
    table_view = os.path.join(arcpy.env.scratchGDB, 'table_view')
    print (selected_municipality_fc)
    
    # Create a list of all the municipalities
    all_municipalities_names = list()
    with arcpy.da.SearchCursor(fc_input, "NAME") as rows:  
        all_municipalities_names = sorted(list(set([row[0] for row in rows])))
    
    # Generate a csv file for each municipality
    for municipality_name in all_municipalities_names:
        arcpy.AddMessage ("Processing " + municipality_name)
        print ("Processing " + municipality_name)
        municipality_name = municipality_name.replace('.', '')

        # Create a layer with all municipalities
        arcpy.MakeFeatureLayer_management(fc_input, all_municipalities_layer)
        
        # Create a feature class with just the selected municipality
        arcpy.MakeFeatureLayer_management(fc_input, selected_municipality_layer)
        arcpy.SelectLayerByAttribute_management(selected_municipality_layer, "NEW_SELECTION", "NAME = '" + municipality_name + "'")
        arcpy.CopyFeatures_management(selected_municipality_layer, selected_municipality_fc)
        
        # Get all adjacent municipalities
        arcpy.SelectLayerByLocation_management(all_municipalities_layer, 'intersect', selected_municipality_layer)
        arcpy.CopyFeatures_management(all_municipalities_layer, adjacent_municipalities_fc)
        
        # Get the fields from the input
        all_fields= arcpy.ListFields(fc_input)
        # Create a fieldinfo object and populate it to describe the fields we want to be visible
        field_info = arcpy.FieldInfo()
        for field in all_fields:
            if field.name in __fields_to_keep.keys():
                field_info.addField(field.name, __fields_to_keep[field.name], "VISIBLE", "")
            else:
                field_info.addField(field.name, field.name, "HIDDEN", "")
        field_info.addField("OBJECTID_1", "OBJECTID_1", "HIDDEN", "")
        field_info.addField("Shape_Length", "Shape_Length", "HIDDEN", "")
        # Make a table view so we can export just the tabular data
        arcpy.MakeTableView_management(adjacent_municipalities_fc, table_view, "", "", field_info)
        
        # Export the table to a csv file
        arcpy.CopyRows_management(table_view, os.path.join(output_csv_dir, municipality_name) + '.csv')
        
    return;



if __name__ == '__main__':
     main_process_shape_file(sys.argv[1], sys.argv[2])
    
    



