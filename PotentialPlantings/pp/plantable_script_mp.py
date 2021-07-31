# -*- coding: utf-8 -*-

import arcpy
import os
import multiprocessing
import configparser

import pp.logger
logger = pp.logger.get('pp_log')

cfg_fn = os.path.normpath(__file__ + '/../../local/plantable_script.properties')
config = configparser.ConfigParser()
config.read(cfg_fn)

PROCESSORS = int(config['runtime']['processors'])
USE_IN_MEM = bool(int(config['runtime']['is_use_in_mem']))
WORK_DIR = config['runtime']['work_dir']
BUILDINGS_EXPAND_TIF = config['input_data']['buildings_tif']
CANOPY_EXPAND_TIF = config['input_data']['canopy_tif']
PLANTABLE_REGION_TIF = config['input_data']['plantable_region_tif']
MUNI_COMMUNITY_AREA =config['input_data']['muni_community_area']
LAND_USE_2015 = config['input_data']['land_use_2015']
PUBLIC_LAND = config['input_data']['public_land']
SUBSET_START_POINT = config['community_subset']['start_point']
SUBSET_COUNT = int(config['community_subset']['number'])


INTERMEDIATE_OUTPUT_GDB = os.path.join(WORK_DIR, 'output/intermediate_data.gdb')
FINAL_OUTPUT_GDB = os.path.join(WORK_DIR, 'output/all_communities.gdb')
COMMUNITY_OUTPUT_DIR = os.path.join(WORK_DIR, 'output/community')

IN_MEM_ID = 0

OS_PID = os.getpid()

def run():
    __log_info ("Logging to %s" % pp.logger.LOG_FILE)
       
    os.makedirs(WORK_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(INTERMEDIATE_OUTPUT_GDB), exist_ok=True)
    os.makedirs(os.path.dirname(FINAL_OUTPUT_GDB), exist_ok=True)
    os.makedirs(COMMUNITY_OUTPUT_DIR, exist_ok=True)
    
    if not arcpy.Exists(INTERMEDIATE_OUTPUT_GDB):
        __delete ([INTERMEDIATE_OUTPUT_GDB])
        arcpy.CreateFileGDB_management(os.path.dirname(INTERMEDIATE_OUTPUT_GDB), os.path.basename(INTERMEDIATE_OUTPUT_GDB))
    if not arcpy.Exists(FINAL_OUTPUT_GDB):
        arcpy.CreateFileGDB_management(os.path.dirname(FINAL_OUTPUT_GDB), os.path.basename(FINAL_OUTPUT_GDB))

    
    communities = __get_communities(SUBSET_START_POINT, SUBSET_COUNT)
    
    if PROCESSORS > 1:
        p = multiprocessing.Pool(PROCESSORS)
        community_fcs = p.map(run_mp, communities, 1)
        p.close()        
    else:
        # Process each community past the alphabetical starting point
        community_fcs = list()
        for community in communities:
            community_fcs.append (run_mp (community))

    __save_final_output (community_fcs)
    
    __log_info('Complete')
    return


def run_mp (community_spec):
    try:

        __log_debug ("C: %s" % str(community_spec))
       
        arcpy.env.outputZFlag = "Disabled"
        arcpy.env.outputMFlag = "Disabled"
        arcpy.overwriteOutput = True

        # Process each community past the alphabetical starting point
        community, acres, idx = community_spec
        __log_info('%i acres' % (acres), community)
        
        if USE_IN_MEM:
            arcpy.Delete_management('in_memory')
            
        canopy_clipped = __get_intermediate_name ('canopy_clipped', idx, USE_IN_MEM)
        plantable_region_clipped = __get_intermediate_name ('plantable_region_clipped', idx, USE_IN_MEM)
        buildings_clipped = __get_intermediate_name ('buildings_clipped', idx, USE_IN_MEM)
        minus_trees = __get_intermediate_name ('minus_trees', idx, USE_IN_MEM)
        minus_trees_buildings = __get_intermediate_name ('minus_trees_buildings', idx, USE_IN_MEM)
        plantable_poly = __get_intermediate_name ('plantable_poly', idx, USE_IN_MEM)
        plantable_single_poly = __get_intermediate_name ('plantable_single_poly', idx, USE_IN_MEM)
        plantable_muni = __get_intermediate_name ('plantable_muni', idx, USE_IN_MEM)
        plantable_muni_landuse = __get_intermediate_name ('plantable_muni_landuse', idx, USE_IN_MEM)
        plantable_muni_landuse_public = __get_intermediate_name ('plantable_muni_landuse_public', idx, USE_IN_MEM)
        out_fc = __get_community_output_gdb (community)
                   
        __log_debug ('Getting community boundary', community)
        community_boundary = arcpy.SelectLayerByAttribute_management(MUNI_COMMUNITY_AREA, 'NEW_SELECTION', "COMMUNITY = '%s'" % (community))[0]
    
        __log_debug ('Clipping %s' %(os.path.basename(CANOPY_EXPAND_TIF)), community)
        arcpy.management.Clip(CANOPY_EXPAND_TIF, '#', canopy_clipped, community_boundary, clipping_geometry="ClippingGeometry", maintain_clipping_extent="MAINTAIN_EXTENT")
    
        __log_debug ('Clipping %s' %(os.path.basename(PLANTABLE_REGION_TIF)), community)
        arcpy.management.Clip(PLANTABLE_REGION_TIF, '#', plantable_region_clipped, community_boundary, clipping_geometry="ClippingGeometry", maintain_clipping_extent="MAINTAIN_EXTENT")
    
        __log_debug ('Removing trees', community)
        arcpy.gp.RasterCalculator_sa('Con(IsNull("%s"),"%s")' % (canopy_clipped, plantable_region_clipped), minus_trees)
        __delete( [canopy_clipped, plantable_region_clipped] )
                   
        __log_debug ('Clipping %s' %(os.path.basename(BUILDINGS_EXPAND_TIF)), community)
        arcpy.management.Clip(BUILDINGS_EXPAND_TIF, '#', buildings_clipped, community_boundary, clipping_geometry="ClippingGeometry", maintain_clipping_extent="MAINTAIN_EXTENT")
    
        __log_debug ('Removing buildings', community)
        arcpy.gp.RasterCalculator_sa('Con(IsNull("%s"),"%s")' % (buildings_clipped, minus_trees), minus_trees_buildings)
        __delete( [buildings_clipped, minus_trees, community_boundary] )
        
        __log_debug ('Converting raster to polygon', community)        
        arcpy.RasterToPolygon_conversion(minus_trees_buildings, plantable_poly, "SIMPLIFY", "", "SINGLE_OUTER_PART", "")
        __delete( [minus_trees_buildings] )
    
        __log_debug ('Converting multipart polygons to singlepart', community)        
        arcpy.MultipartToSinglepart_management(plantable_poly, plantable_single_poly)            
        __delete( [plantable_poly] )
    
        __log_debug ('Spatial join', community)        
        arcpy.SpatialJoin_analysis(plantable_single_poly, MUNI_COMMUNITY_AREA, plantable_muni, "JOIN_ONE_TO_ONE", "KEEP_ALL", "", "INTERSECT", "", "")
    
        __log_debug ('Repair invalid features', community)        
        arcpy.management.RepairGeometry(plantable_muni, "DELETE_NULL", "ESRI")
        __delete( [plantable_single_poly] )
    
        __log_debug ('Identify plantable land', community)        
        arcpy.Identity_analysis(plantable_muni, LAND_USE_2015, plantable_muni_landuse, "ALL", "", "NO_RELATIONSHIPS")
        __delete( [plantable_muni] )
    
        __log_debug ('Identify public land', community)        
        arcpy.Identity_analysis(plantable_muni_landuse, PUBLIC_LAND, plantable_muni_landuse_public, "ALL", "", "NO_RELATIONSHIPS")
        __delete( [plantable_muni_landuse] )
    
        __log_debug ('Add and populate the "Community" field', community)   
        arcpy.management.CalculateField(plantable_muni_landuse_public, "Community", '"%s"' % (community), "PYTHON3", "", "TEXT")
    
        __log_debug ('Add and populate the "Public" field', community)   
        arcpy.management.CalculateField(plantable_muni_landuse_public, "Public", "is_public(!FID_Public!)", "PYTHON3", r"""def is_public (fid):
            if fid == -1:
                return 0
            else:
                return 1""", "SHORT")
    
        __log_debug ('Trim excess fields', community)   
        trim_excess_fields (plantable_muni_landuse_public, ['objectid', 'shape', 'shape_area', 'shape_length', 'landuse', 'public', 'community'])
    
        __save_community (plantable_muni_landuse_public, out_fc)

            
    except Exception as ex:
      __log_debug ('Exception: %s' % (str(ex)))
      raise ex
        
    return out_fc
      


        
# def __get_communities (start_point, count):
#     communities = []
#     idx = 0
#     with arcpy.da.SearchCursor(MUNI_COMMUNITY_AREA, ['COMMUNITY', 'SHAPE@']) as cursor:
#         for attr_vals in cursor:
#             communities.append( (attr_vals[0], int(attr_vals[1].getArea('PLANAR', 'ACRES')), idx) )
#             idx = idx + 1

#     community_names = [c[0] for c in communities]
#     if len(community_names) != len(set(community_names)):
#         raise Exception ("Duplicate community names: %s" % str(community_names))
        
#     communities_sorted = [c for c in sorted(communities) if c[0].lower() >= start_point.lower()][0:count]       
    
#     communities = []
#     idx = 0
#     for s in communities_sorted:
#         communities.append ( (s[0], s[1], idx))
#         idx = idx + 1
#     return communities
    
        
def __get_communities (start_point, count):
    communities = []
    with arcpy.da.SearchCursor(MUNI_COMMUNITY_AREA, ['FID', 'COMMUNITY', 'SHAPE@']) as cursor:
        for attr_vals in cursor:
            communities.append( (attr_vals[1], int(attr_vals[2].getArea('PLANAR', 'ACRES')), attr_vals[0]) )

    community_names = [c[0] for c in communities]
    if len(community_names) != len(set(community_names)):
        raise Exception ("Duplicate community names: %s" % str(community_names))
        
    communities_sorted = [c for c in sorted(communities) if c[0].lower() >= start_point.lower()][0:count]       
    return communities_sorted



def  __get_intermediate_name (name, idx, use_in_mem):
    global IN_MEM_ID
    
    if use_in_mem:
        IN_MEM_ID = IN_MEM_ID + 1
        fn = os.path.join('in_memory', name[0:3] + '_%i' % idx + '_' +  str(IN_MEM_ID))
    else:
        fn = os.path.join(INTERMEDIATE_OUTPUT_GDB, name + '_%i' % idx )
    __delete ([fn])
#    __log_debug ('Intermediate file: %s' % (fn))
    return fn


def  __get_community_output_gdb (community):
    out_gdb = os.path.join(COMMUNITY_OUTPUT_DIR, community.replace(' ','') + '.gdb')
    out_fc = os.path.join(out_gdb, 'plantable')
    if not arcpy.Exists(out_gdb):
        arcpy.CreateFileGDB_management(os.path.dirname(out_gdb), os.path.basename(out_gdb))
    __delete ([out_fc])
    return out_fc


def __log_info (text, community = None):
    __log (text, False, community)
           
def __log_debug (text, community = None):
    __log (text, True, community   )        

def __log (text, is_debug, community = None):
    if community is None:
        t = "%i: %s" % (OS_PID, text)
    else:
        t ="%i %s: %s" % (OS_PID, community, text)
    #print (t)
    if is_debug:
        logger.debug(t)
    else:
        logger.info(t)
    return

    

def __delete (obj_list):
    for obj in obj_list:
#        __log_debug ('Deleting file: %s' % (str(obj)))
        arcpy.Delete_management(obj)
    return


def trim_excess_fields (fc, keep_fields):
    all_fields = set([f.name.lower() for f in arcpy.ListFields(fc)])
    keep_fields = set([k.lower() for k in keep_fields])
    arcpy.DeleteField_management(fc, ';'.join(all_fields - keep_fields))
    return


def __save_community (in_fc, out_fc):
    if arcpy.da.Describe(in_fc)['catalogPath'].startswith('in_memory\\'):
        arcpy.CopyFeatures_management(in_fc, out_fc)
    else:        
        arcpy.Copy_management(in_fc, out_fc)
    return


def __save_final_output (community_fcs):
    out_fc = os.path.join(FINAL_OUTPUT_GDB, 'plantable')
    
    __log_debug ('Preparing final output feature class: %s' % (out_fc))
    # if not arcpy.Exists(FINAL_OUTPUT_GDB):
    #     arcpy.CreateFileGDB_management(os.path.dirname(FINAL_OUTPUT_GDB), os.path.basename(FINAL_OUTPUT_GDB))
    __delete ([out_fc])   
    sr = arcpy.Describe(community_fcs[0]).spatialReference
    arcpy.CreateFeatureclass_management(os.path.dirname(out_fc), os.path.basename(out_fc), 'POLYGON', community_fcs[0], "DISABLED", "DISABLED", sr)

    __log_info ('Write to final output feature class')
    arcpy.management.Append(community_fcs, out_fc)
    
    __log_info ('Creating index on community name')
    arcpy.management.AddIndex(out_fc, "COMMUNITY", "IDX_Comm", "NON_UNIQUE", "NON_ASCENDING")

    return
    

if __name__ == '__main__':
    run()
#    run ('B', 2)
#    run ('Albany Park', 1)
#    run ('', 9999)
    
    # if len(sys.argv) == 1:
    #     run('', 9999)
    # elif len(sys.argv) == 2:
    #     run(sys.argv[1], 9999)
    # else:
    #     run(sys.argv[1], int(sys.argv[2]))


