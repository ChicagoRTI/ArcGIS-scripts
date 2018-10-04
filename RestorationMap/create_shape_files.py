# -*- coding: utf-8 -*-
"""
Created on Tue Mar 20 11:07:22 2018

@author: Don
"""
# To run from Spyder iPython console:
#   runfile('D:/CRTI/python_projects/ArcGIS-scripts/RestorationMap/create_shape_files.py', wdir='D:/CRTI/python_projects/ArcGIS-scripts/RestorationMap', args="'D:/CRTI/MySql/Data/files' 'D:/CRTI/GIS data/restoration_map'")
#

# Make sure the ArcGIS components are in the system path (from C:\Program Files (x86)\ArcGIS\Desktop10.4\Support\Python/Desktop10.4.pth)
import sys
import pandas as pd




__arc_gis_dir = "C:\\Program Files (x86)\\ArcGIS\\Desktop10.4\\"
__arc_gis_path = [__arc_gis_dir + "bin",
                __arc_gis_dir + "ArcPy",
                __arc_gis_dir + "ArcToolBox\Scripts"]
for p in __arc_gis_path: 
    if p not in sys.path: sys.path += [p]


import arcpy

# Get the input arguments
__csv_input_dir = sys.argv[1]
__shp_output_dir = sys.argv[2]

print (__csv_input_dir)
print (__shp_output_dir)

arcpy.env.workspace = __shp_output_dir
__spatial_reference = arcpy.SpatialReference("NAD 1983")

def read_csv (fn):
    return pd.read_csv(__csv_input_dir + '/' + fn + '.csv', sep=',', quotechar='|')

def create_feature_classes (name, col_specs):
    fc_types = ['POINT', 'POLYGON', 'POLYLINE']
    fcs = list()
    for fc_type in fc_types:
        fc_name = name + '_' + fc_type
        if arcpy.Exists(fc_name + '.shp'):
            arcpy.Delete_management(fc_name + '.shp')
        
        fc = arcpy.CreateFeatureclass_management(out_path=__shp_output_dir,
                                            out_name=fc_name,
                                            geometry_type=fc_type,
                                            spatial_reference=__spatial_reference)
        for col_spec in col_specs:  
            arcpy.AddField_management(fc, *col_spec)
        fcs.append(fc)
    return fcs


    
def get_stewardship_site_info (csv, id):
    try: 
        s_site = csv[csv['id']==int(id)]
        if s_site.empty:
            raise Exception('No stewardship site')
        return {'site':s_site.name.values[0], 'county':s_site.county.values[0], 'kml':s_site.kml_url.values[0]}
    except Exception:
        return {'site':'', 'county':'', 'kml':''}


def get_user_info (csv, id):
    try: 
        users = csv[csv['id']==id]
        if users.empty:
            raise Exception('No user')
        return {'email':users.email.values[0], 'f_name':users.first_name.values[0], 'l_name':users.last_name.values[0]}
    except Exception:
        return {'email':'', 'f_name':'', 'l_name':''}
    
    
def get_geo_object (coords, shape):
    array = arcpy.Array()
    c = coords.split()
    # Remove consecutive duplicate coordinates
    i = 0
    while i < len(c)-1:
        if c[i] == c[i+1]:
            del c[i]
        else:
            i = i+1
    # Recude 2D polygon and 1D line
    if (len(c)==3 and c[0]==c[2]) :
        c = c[:-1]
    if (len(c)==2 and c[0]==c[1]) :
        c = c[:-1]

    for point in c:
        try:
            array.add(arcpy.Point(point.split(',')[0],point.split(',')[1]))
        except:
            pass
        
    if len(array)==1 and shape=='Point':
        return array[0]
    elif len(array)==2 and shape=='Polyline':
        return arcpy.Polyline(array, __spatial_reference)
    elif len(array)>2 and shape=='Polygon':
        return arcpy.Polygon(array, __spatial_reference)
    else:
        return None


def get_geo_line (coords):
    array = arcpy.Array()
    c = coords.split()
    for point in c:
        try:
            array.add(arcpy.Point(point.split(',')[0],point.split(',')[1]))
        except:
            pass
    if len(array) > 1:        
        return arcpy.Polyline(array, __spatial_reference)
    else:
        return None


def main_create_shape_files ():
    stewardship_site_csv = read_csv('stewardship_site')
    users_csv = read_csv('users')
    
    
    #################################################################
    #
    #           border
    #
    ################################################################# 
    csv_records = read_csv('border')
    fc_fields = (
            ("id_2", "SHORT"),
            ("site_id", "SHORT"),
            ("site", "TEXT"),
            ("county", "TEXT"),
            ("kml", "TEXT"),
            ("user_id", "SHORT"),
            ("email", "TEXT"),
            ("f_name", "TEXT"),
            ("l_name", "TEXT")
            )
    fcs = create_feature_classes ('border', fc_fields)
    
    for fc in fcs:
        with arcpy.da.InsertCursor(fc, ['SHAPE@'] + list(tuple(item[0] for item in fc_fields))) as cursor:
            for i, csv_record in csv_records.iterrows():           
                s_site = get_stewardship_site_info(stewardship_site_csv, csv_record['stewardshipsite_id'])
                u_info = get_user_info(users_csv, csv_record['user_id'])
                geo_object = get_geo_object(csv_record['coordinates'], arcpy.Describe(fc).shapeType)
                if geo_object is not None:
                    cursor.insertRow((geo_object, csv_record['id'], csv_record['stewardshipsite_id'], s_site['site'], s_site['county'], s_site['kml'], csv_record['user_id'], u_info['email'], u_info['f_name'], u_info['l_name']))
        del cursor 
    
    
    #################################################################
    #
    #           brush
    #
    ################################################################# 
    csv_records = read_csv('brush')
    fc_fields = (
            ("id_2", "SHORT"),
            ("site_id", "SHORT"),
            ("site", "TEXT"),
            ("county", "TEXT"),
            ("kml", "TEXT"),
            ("date", "TEXT"),
            ("title", "TEXT"),
            ("descr", "TEXT"),
            ("user_id", "SHORT"),
            ("email", "TEXT"),
            ("f_name", "TEXT"),
            ("l_name", "TEXT")
            )
    fcs = create_feature_classes ('brush', fc_fields)
    
    for fc in fcs:
        with arcpy.da.InsertCursor(fc, ['SHAPE@'] + list(tuple(item[0] for item in fc_fields))) as cursor:
            for i, csv_record in csv_records.iterrows():           
                s_site = get_stewardship_site_info(stewardship_site_csv, csv_record['stewardshipsite_id'])
                u_info = get_user_info(users_csv, csv_record['user_id'])
                geo_object = get_geo_object(csv_record['coordinates'], arcpy.Describe(fc).shapeType)
                if geo_object is not None:
                    cursor.insertRow((geo_object, csv_record['id'], csv_record['stewardshipsite_id'], s_site['site'], s_site['county'], s_site['kml'], csv_record['date'], csv_record['title'], csv_record['description'], csv_record['user_id'], u_info['email'], u_info['f_name'], u_info['l_name']))
        del cursor 

    
    
    #################################################################
    #
    #           landmark
    #
    ################################################################# 
    csv_records = read_csv('landmark')
    fc_fields = (
            ("id_2", "SHORT"),
            ("site_id", "SHORT"),
            ("site", "TEXT"),
            ("county", "TEXT"),
            ("kml", "TEXT"),
            ("name", "TEXT"),
            ("descr", "TEXT"),
            ("user_id", "SHORT"),
            ("email", "TEXT"),
            ("f_name", "TEXT"),
            ("l_name", "TEXT")
            )
    fcs = create_feature_classes ('landmark', fc_fields)
    
    for fc in fcs:
        with arcpy.da.InsertCursor(fc, ['SHAPE@'] + list(tuple(item[0] for item in fc_fields))) as cursor:
            for i, csv_record in csv_records.iterrows():           
                s_site = get_stewardship_site_info(stewardship_site_csv, csv_record['stewardshipsite_id'])
                u_info = get_user_info(users_csv, csv_record['user_id'])
                geo_object = get_geo_object(csv_record['coordinates'], arcpy.Describe(fc).shapeType)
                if geo_object is not None:
                    cursor.insertRow((geo_object, csv_record['id'], csv_record['stewardshipsite_id'], s_site['site'], s_site['county'], s_site['kml'], csv_record['name'], csv_record['description'], csv_record['user_id'], u_info['email'], u_info['f_name'], u_info['l_name']))
        del cursor 

    #################################################################
    #
    #           other
    #
    ################################################################# 
    csv_records = read_csv('other')
    fc_fields = (
            ("id_2", "SHORT"),
            ("site_id", "SHORT"),
            ("site", "TEXT"),
            ("county", "TEXT"),
            ("kml", "TEXT"),
            ("date", "TEXT"),
            ("title", "TEXT"),
            ("descr", "TEXT"),
            ("user_id", "SHORT"),
            ("email", "TEXT"),
            ("f_name", "TEXT"),
            ("l_name", "TEXT")
            )
    fcs = create_feature_classes ('other', fc_fields)
    
    for fc in fcs:
        with arcpy.da.InsertCursor(fc, ['SHAPE@'] + list(tuple(item[0] for item in fc_fields))) as cursor:
            for i, csv_record in csv_records.iterrows():           
                s_site = get_stewardship_site_info(stewardship_site_csv, csv_record['stewardshipsite_id'])
                u_info = get_user_info(users_csv, csv_record['user_id'])
                geo_object = get_geo_object(csv_record['coordinates'], arcpy.Describe(fc).shapeType)
                if geo_object is not None:
                    cursor.insertRow((geo_object, csv_record['id'], csv_record['stewardshipsite_id'], s_site['site'], s_site['county'], s_site['kml'], csv_record['date'], csv_record['title'], csv_record['description'], csv_record['user_id'], u_info['email'], u_info['f_name'], u_info['l_name']))
        del cursor 


    #################################################################
    #
    #           seed
    #
    ################################################################# 
    csv_records = read_csv('seed')
    fc_fields = (
            ("id_2", "SHORT"),
            ("site_id", "SHORT"),
            ("site", "TEXT"),
            ("county", "TEXT"),
            ("kml", "TEXT"),
            ("date", "TEXT"),
            ("title", "TEXT"),
            ("descr", "TEXT"),
            ("user_id", "SHORT"),
            ("email", "TEXT"),
            ("f_name", "TEXT"),
            ("l_name", "TEXT")
            )
    fcs = create_feature_classes ('seed', fc_fields)
    
    for fc in fcs:
        with arcpy.da.InsertCursor(fc, ['SHAPE@'] + list(tuple(item[0] for item in fc_fields))) as cursor:
            for i, csv_record in csv_records.iterrows():           
                s_site = get_stewardship_site_info(stewardship_site_csv, csv_record['stewardshipsite_id'])
                u_info = get_user_info(users_csv, csv_record['user_id'])
                geo_object = get_geo_object(csv_record['coordinates'], arcpy.Describe(fc).shapeType)
                if geo_object is not None:
                    cursor.insertRow((geo_object, csv_record['id'], csv_record['stewardshipsite_id'], s_site['site'], s_site['county'], s_site['kml'], csv_record['date'], csv_record['title'], csv_record['description'], csv_record['user_id'], u_info['email'], u_info['f_name'], u_info['l_name']))
        del cursor 




    #################################################################
    #
    #           trails
    #
    ################################################################# 
    csv_records = read_csv('trails')
    fc_fields = (
            ("id_2", "SHORT"),
            ("site_id", "SHORT"),
            ("site", "TEXT"),
            ("county", "TEXT"),
            ("kml", "TEXT"),
            ("name", "TEXT"),
            ("user_id", "SHORT"),
            ("email", "TEXT"),
            ("f_name", "TEXT"),
            ("l_name", "TEXT")
            )
    fcs = create_feature_classes ('trails', fc_fields)
    
    for fc in fcs:
        if arcpy.Describe(fc).shapeType == 'Polyline':
            with arcpy.da.InsertCursor(fc, ['SHAPE@'] + list(tuple(item[0] for item in fc_fields))) as cursor:
                for i, csv_record in csv_records.iterrows():           
                    s_site = get_stewardship_site_info(stewardship_site_csv, csv_record['stewardshipsite_id'])
                    u_info = get_user_info(users_csv, csv_record['user_id'])
                    geo_object = get_geo_line(csv_record['coordinates'])
                    if geo_object is not None:
                        cursor.insertRow((geo_object, csv_record['id'], csv_record['stewardshipsite_id'], s_site['site'], s_site['county'], s_site['kml'], csv_record['name'], csv_record['user_id'], u_info['email'], u_info['f_name'], u_info['l_name']))
            del cursor 


    #################################################################
    #
    #           weed
    #
    ################################################################# 
    csv_records = read_csv('weed')
    fc_fields = (
            ("id_2", "SHORT"),
            ("site_id", "SHORT"),
            ("site", "TEXT"),
            ("county", "TEXT"),
            ("kml", "TEXT"),
            ("date", "TEXT"),
            ("title", "TEXT"),
            ("descr", "TEXT"),
            ("user_id", "SHORT"),
            ("email", "TEXT"),
            ("f_name", "TEXT"),
            ("l_name", "TEXT")
            )
    fcs = create_feature_classes ('weed', fc_fields)
    
    for fc in fcs:
        with arcpy.da.InsertCursor(fc, ['SHAPE@'] + list(tuple(item[0] for item in fc_fields))) as cursor:
            for i, csv_record in csv_records.iterrows():           
                s_site = get_stewardship_site_info(stewardship_site_csv, csv_record['stewardshipsite_id'])
                u_info = get_user_info(users_csv, csv_record['user_id'])
                geo_object = get_geo_object(csv_record['coordinates'], arcpy.Describe(fc).shapeType)
                if geo_object is not None:
                    cursor.insertRow((geo_object, csv_record['id'], csv_record['stewardshipsite_id'], s_site['site'], s_site['county'], s_site['kml'], csv_record['date'], csv_record['title'], csv_record['description'], csv_record['user_id'], u_info['email'], u_info['f_name'], u_info['l_name']))
        del cursor 




    # Make another pass to add additional fields and delete empty shape files
    fcs = arcpy.ListFeatureClasses()
    for fc in fcs:
        if arcpy.management.GetCount(fc)[0] == "0":  
            arcpy.Delete_management(fc) 
        else:
            arcpy.AddField_management(fc, 'centroid', 'TEXT') 
            arcpy.CalculateField_management(fc, 'centroid', '!SHAPE.centroid!','PYTHON')
            if arcpy.Describe(fc).shapeType == 'Polyline':
                arcpy.AddField_management(fc, 'length', 'LONG') 
                arcpy.CalculateField_management(fc, 'length', 'int(float(!SHAPE.length@feet!))','PYTHON')
            if arcpy.Describe(fc).shapeType == 'Polygon':
                arcpy.AddField_management(fc, 'area', 'LONG') 
                arcpy.AddField_management(fc, 'p_length', 'LONG') 
                arcpy.CalculateField_management(fc, 'area', 'int(float(!SHAPE.area@squarefeet!))','PYTHON')
                arcpy.CalculateField_management(fc, 'p_length', 'int(float(!SHAPE.length@feet!))','PYTHON') 


if __name__ == '__main__':
     main_create_shape_files()
    
    



