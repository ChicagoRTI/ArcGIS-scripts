# -*- coding: utf-8 -*-

import arcpy
from datetime import datetime
import os


USE_IN_MEM = True
IN_MEM_ID = 0

LOG_FILE = r'E:\PotentialPlantings\pp_log.txt'

WORK_DIR = r'E:\PotentialPlantings'
LOG_FILE = os.path.join(WORK_DIR, 'pp_log.txt')
INTERMEDIATE_GDB = os.path.join(WORK_DIR, 'intermediate_data.gdb')
OUTPUT_DIR = os.path.join(WORK_DIR, 'output')



BUILDINGS_EXPAND_TIF = r"E:\PotentialPlantings\data\lindsay_tifs\BuildingsExpand_0_1_one_bit.tif"
CANOPY_EXPAND_TIF = r"E:\PotentialPlantings\data\lindsay_tifs\CanopyExpand_0_1_one_bit.tif"
PLANTABLE_REGION_TIF = r"E:\PotentialPlantings\data\lindsay_tifs\PlantableRegion_0_1_one_bit.tif"

MUNI_COMMUNITY_AREA = r"E:\PotentialPlantings\data\muni_community_area\MuniCommunityArea.shp"
LAND_USE_2015 = r"E:\PotentialPlantings\data\cmap_landuse_2015\Landuse2015_CMAP_v1.gdb\landuse"
PUBLIC_LAND = r"E:\PotentialPlantings\data\public_private_singlepart\PublicPrivateSinglepart.gdb\public"


def run(start_point, count):
    try:
        __log('')
        
        arcpy.env.outputZFlag = "Disabled"
        arcpy.env.outputMFlag = "Disabled"
        arcpy.overwriteOutput = True
        
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)
            
        community_fcs = list()
            
        # Process each community past the alphabetical starting point
        for community, acres in __get_communities(start_point, count):
            __log('%i acres' % (acres), community)
            
            if USE_IN_MEM:
                arcpy.Delete_management('in_memory')
            
            canopy_clipped = __get_intermediate_name ('canopy_clipped', USE_IN_MEM)
            plantable_region_clipped = __get_intermediate_name ('plantable_region_clipped', USE_IN_MEM)
            buildings_clipped = __get_intermediate_name ('buildings_clipped', USE_IN_MEM)
            minus_trees = __get_intermediate_name ('minus_trees', USE_IN_MEM)
            minus_trees_buildings = __get_intermediate_name ('minus_trees_buildings', USE_IN_MEM)
            plantable_poly = __get_intermediate_name ('plantable_poly', USE_IN_MEM)
            plantable_single_poly = __get_intermediate_name ('plantable_single_poly', USE_IN_MEM)
            plantable_muni = __get_intermediate_name ('plantable_muni', USE_IN_MEM)
            plantable_muni_landuse = __get_intermediate_name ('plantable_muni_landuse', USE_IN_MEM)
            plantable_muni_landuse_public = __get_intermediate_name ('plantable_muni_landuse_public', USE_IN_MEM)
            out_fc = __get_community_output_gdb (community)
                       
            __log ('Getting community boundary', community)
            community_boundary = arcpy.SelectLayerByAttribute_management(MUNI_COMMUNITY_AREA, 'NEW_SELECTION', "COMMUNITY = '%s'" % (community))[0]

            __log ('Clipping %s' %(os.path.basename(CANOPY_EXPAND_TIF)), community)
            arcpy.management.Clip(CANOPY_EXPAND_TIF, '#', canopy_clipped, community_boundary, clipping_geometry="ClippingGeometry", maintain_clipping_extent="MAINTAIN_EXTENT")

            __log ('Clipping %s' %(os.path.basename(PLANTABLE_REGION_TIF)), community)
            arcpy.management.Clip(PLANTABLE_REGION_TIF, '#', plantable_region_clipped, community_boundary, clipping_geometry="ClippingGeometry", maintain_clipping_extent="MAINTAIN_EXTENT")

            __log ('Removing trees', community)
            arcpy.gp.RasterCalculator_sa('Con(IsNull("%s"),"%s")' % (canopy_clipped, plantable_region_clipped), minus_trees)
            __delete( [canopy_clipped, plantable_region_clipped] )
                       
            __log ('Clipping %s' %(os.path.basename(BUILDINGS_EXPAND_TIF)), community)
            arcpy.management.Clip(BUILDINGS_EXPAND_TIF, '#', buildings_clipped, community_boundary, clipping_geometry="ClippingGeometry", maintain_clipping_extent="MAINTAIN_EXTENT")

            __log ('Removing buildings', community)
            arcpy.gp.RasterCalculator_sa('Con(IsNull("%s"),"%s")' % (buildings_clipped, minus_trees), minus_trees_buildings)
            __delete( [buildings_clipped, minus_trees, community_boundary] )
            
            __log ('Converting raster to polygon', community)        
            arcpy.RasterToPolygon_conversion(minus_trees_buildings, plantable_poly, "SIMPLIFY", "", "SINGLE_OUTER_PART", "")
            __delete( [minus_trees_buildings] )
    
            __log ('Converting multipart polygons to singlepart', community)        
            arcpy.MultipartToSinglepart_management(plantable_poly, plantable_single_poly)            
            __delete( [plantable_poly] )
        
            __log ('Spatial join', community)        
            arcpy.SpatialJoin_analysis(plantable_single_poly, MUNI_COMMUNITY_AREA, plantable_muni, "JOIN_ONE_TO_ONE", "KEEP_ALL", "", "INTERSECT", "", "")

            __log ('Repair invalid features', community)        
            arcpy.management.RepairGeometry(plantable_muni, "DELETE_NULL", "ESRI")
            __delete( [plantable_single_poly] )

            __log ('Identify plantable land', community)        
            arcpy.Identity_analysis(plantable_muni, LAND_USE_2015, plantable_muni_landuse, "ALL", "", "NO_RELATIONSHIPS")
            __delete( [plantable_muni] )

            __log ('Identify public land', community)        
            arcpy.Identity_analysis(plantable_muni_landuse, PUBLIC_LAND, plantable_muni_landuse_public, "ALL", "", "NO_RELATIONSHIPS")
            __delete( [plantable_muni_landuse] )

            # __log ('Add "Public" field', community)        
            # arcpy.AddField_management(plantable_muni_landuse_public, "Public", "SHORT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

            __log ('Add and populate the "Community" field', community)   
            arcpy.management.CalculateField(plantable_muni_landuse_public, "Community", '"%s"' % (community), "PYTHON3", "", "TEXT")

            __log ('Add and populate the "Public" field', community)   
            arcpy.management.CalculateField(plantable_muni_landuse_public, "Public", "is_public(!FID_Public!)", "PYTHON3", r"""def is_public (fid):
                if fid == -1:
                    return 0
                else:
                    return 1""", "SHORT")

            __log ('Trim excess fields', community)   
            trim_excess_fields (plantable_muni_landuse_public, ['objectid', 'shape', 'shape_area', 'shape_length', 'landuse', 'public', 'community'])

            __save_community (plantable_muni_landuse_public, out_fc)
            community_fcs.append (out_fc)


        __save_final_output (community_fcs)
        
        __log('Complete')


    except Exception as ex:
        __log ('Exception: %s' % (str(ex)))
        raise ex
        

def __save_final_output (community_fcs):
    out_gdb = os.path.join(OUTPUT_DIR, 'AllCommunities' + '.gdb')
    out_fc = os.path.join(out_gdb, 'plantable')
    
    __log ('Preparing final output feature class: %s' % (out_fc))
    if not arcpy.Exists(out_gdb):
        arcpy.CreateFileGDB_management(os.path.dirname(out_gdb), os.path.basename(out_gdb))
    __delete ([out_fc])   
    sr = arcpy.Describe(community_fcs[0]).spatialReference
    arcpy.CreateFeatureclass_management(os.path.dirname(out_fc), os.path.basename(out_fc), 'POLYGON', community_fcs[0], "DISABLED", "DISABLED", sr)

    __log ('Write to final output feature class')
    arcpy.management.Append(community_fcs, out_fc)
    
    __log ('Creating index on community name')
    arcpy.management.AddIndex(r"E:\PotentialPlantings\output\AllCommunities.gdb\plantable", "COMMUNITY", "IDX_Comm", "NON_UNIQUE", "NON_ASCENDING")

    return
    

        
def __get_communities (start_point, count):
    communities = []
    with arcpy.da.SearchCursor(MUNI_COMMUNITY_AREA, ['COMMUNITY', 'SHAPE@']) as cursor:
        for attr_vals in cursor:
            communities.append( (attr_vals[0], int(attr_vals[1].getArea('PLANAR', 'ACRES'))) )

    return [c for c in sorted(communities) if c[0].lower() >= start_point.lower()][0:count]


def  __get_intermediate_name (name, use_in_mem):
    global IN_MEM_ID
    
    if use_in_mem:
        IN_MEM_ID = IN_MEM_ID + 1
        fn = os.path.join('in_memory', name[0:8] + str(IN_MEM_ID))
    else:
        fn = os.path.join(INTERMEDIATE_GDB, name)
    __delete ([fn])
    return fn


def  __get_community_output_gdb (community):
    out_gdb = os.path.join(OUTPUT_DIR, 'communities', community.replace(' ','') + '.gdb')
    out_fc = os.path.join(out_gdb, 'plantable')
    if not arcpy.Exists(out_gdb):
        arcpy.CreateFileGDB_management(os.path.dirname(out_gdb), os.path.basename(out_gdb))
    __delete ([out_fc])
    return out_fc



def __log (text, community = None):
    now_ =  datetime.now().strftime("%H:%M:%S")
    if community is None:
        t = "%s: %s" % (now_, text)
    else:
        t ="%s - %s: %s" % (now_, community, text)
    print (t)
    with open(LOG_FILE, 'a+') as f:
        f.write(t + '\n')
    return
    

def __delete (obj_list):
    for obj in obj_list:
        arcpy.Delete_management(obj)
    return


def trim_excess_fields (fc, keep_fields):
    all_fields = set([f.name.lower() for f in arcpy.ListFields(fc)])
    keep_fields = set([k.lower() for k in keep_fields])
    for f in all_fields - keep_fields:
        arcpy.DeleteField_management(fc, f)
    return


def __save_community (in_fc, out_fc):
    if arcpy.da.Describe(in_fc)['catalogPath'].startswith('in_memory\\'):
        arcpy.CopyFeatures_management(in_fc, out_fc)
    else:        
        arcpy.Copy_management(in_fc, out_fc)
    return


if __name__ == '__main__':
#    run ('Albany Park', 1)
    run ('', 9999)
    
    # if len(sys.argv) == 1:
    #     run('', 9999)
    # elif len(sys.argv) == 2:
    #     run(sys.argv[1], 9999)
    # else:
    #     run(sys.argv[1], int(sys.argv[2]))


