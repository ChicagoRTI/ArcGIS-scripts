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
import csv


__fields_to_keep = [ 
        ["COMMUNITY", "Municipality"],
        ["CANOPY", "Canopy"],
        ["VEGETATION", "Vegetation"],
        ["BARESOIL", "Bare Soil"],
        ["WATER", "Water"],
        ["BUILDINGS", "Buildings"],
        ["ROADRAIL", "Roads/Rail"],
        ["OTHERPAVED", "Other Paved"]
        ]

def main_process_shape_file (fc_input, output_csv_dir):
    print (fc_input)
    print (output_csv_dir)
    arcpy.env.overwriteOutput = True

    input_field_names = [f[0] for f in __fields_to_keep]
    output_field_names = [f[1] for f in __fields_to_keep]

    all_municipalities_layer = os.path.join(arcpy.env.scratchGDB, 'all_municipalities')
    selected_municipality_layer = os.path.join(arcpy.env.scratchGDB, 'selected_municipality')
    selected_municipality_fc = os.path.join(arcpy.env.scratchGDB, 'adjacent_comps')
    adjacent_municipalities_fc = os.path.join(arcpy.env.scratchGDB, 'adjacent_municipalities')
    table_view = os.path.join(arcpy.env.scratchGDB, 'table_view')
    print (selected_municipality_fc)
    
    # Create a list of all the municipalities
    all_municipalities_names = list()
    with arcpy.da.SearchCursor(fc_input, "COMMUNITY") as rows:  
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
        arcpy.SelectLayerByAttribute_management(selected_municipality_layer, "NEW_SELECTION", "COMMUNITY = '" + municipality_name + "'")
        arcpy.CopyFeatures_management(selected_municipality_layer, selected_municipality_fc)
        
        # Get all adjacent municipalities
        arcpy.SelectLayerByLocation_management(all_municipalities_layer, 'intersect', selected_municipality_layer)
        arcpy.CopyFeatures_management(all_municipalities_layer, adjacent_municipalities_fc)

        # Create the output CSV  
        outputCSV = os.path.join(output_csv_dir, municipality_name) + '.csv'
        with open(outputCSV, "w") as csvfile:  
            csvwriter = csv.writer(csvfile, delimiter=',', lineterminator='\n')  
            # Write field name header line  
            csvwriter.writerow(output_field_names)  
            # Write data rows  
            with arcpy.da.SearchCursor(table_view, input_field_names) as s_cursor:  
                for row in s_cursor:  
                    csvwriter.writerow(row)
    return;



if __name__ == '__main__':
     main_process_shape_file(sys.argv[1], sys.argv[2])
    
    



