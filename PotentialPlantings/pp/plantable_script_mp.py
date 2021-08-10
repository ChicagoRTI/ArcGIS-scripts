# -*- coding: utf-8 -*-

import arcpy
import os
import multiprocessing
import configparser
import shutil

import pp.locate_trees

import pp.logger
logger = pp.logger.get('pp_log')

cfg_fn = os.path.normpath(__file__ + '/../../local/plantable_script.properties')
config = configparser.ConfigParser()
config.read(cfg_fn)

IS_CREATE_SPACES = bool(int(config['actions']['create_space_feature_classes']))
IS_COMBINE_SPACES = bool(int(config['actions']['combine_space_feature_classes']))
IS_CREATE_TREES = bool(int(config['actions']['create_tree_feature_classes']))
IS_COMBINE_TREES = bool(int(config['actions']['combine_tree_site_feature_classes']))
IS_SCRATCH_COMBINED_FCS = bool(int(config['actions']['scratch_combined_feature_classes']))


PROCESSORS = int(config['runtime']['processors'])
USE_IN_MEM = bool(int(config['runtime']['is_use_in_mem']))
WORK_DIR = config['runtime']['work_dir']
BUILDINGS_EXPAND_TIF = config['input_data']['buildings_tif']
CANOPY_EXPAND_TIF = config['input_data']['canopy_tif']
PLANTABLE_REGION_TIF = config['input_data']['plantable_region_tif']
MUNI_COMMUNITY_AREA =config['input_data']['muni_community_area']
LAND_USE_2015 = config['input_data']['land_use_2015']
PUBLIC_LAND = config['input_data']['public_land']
TREE_TEMPLATE_FC = config['input_data']['tree_template_fc']



SUBSET_START_POINT = config['community_subset']['start_point']
SUBSET_COUNT = int(config['community_subset']['number'])


INTERMEDIATE_OUTPUT_DIR = os.path.join(WORK_DIR, r'output\intermediate_data')
COMMUNITY_OUTPUT_DIR = os.path.join(WORK_DIR, r'output\communities')
COMBINED_SPACES_OUTPUT_GDB = os.path.join(WORK_DIR, r'output\combined_spaces.gdb')
COMBINED_TREES_OUTPUT_GDB = os.path.join(WORK_DIR, r'output\combined_trees.gdb')

SPACES_LANDUSE_COL = 'LandUse'
SPACES_PUBLIC_PRIVATE_COL = 'Public'
SPACES_COMMUNITY_COL = 'CommunityID'

TREES_LANDUSE_COL = 'land_use'
TREES_PUBLIC_PRIVATE_COL = 'is_public'
TREES_COMMUNITY_COL = 'community_id'
TREES_SIZE_COL = 'code'


LANDUSE_DOMAIN_NAME = 'Land Use'
LANDUSE_DOMAIN = {'Ag': 1,
                  'Commercial': 2,
                  'Industrial': 3,
                  'Institutional': 4,
                  'OpenSpace': 5,
                  'Residential': 6,
                  'Transit': 7,
                  'Vacant': 8,
                  'Water': 9,
                  'Other': 10}

PUBLIC_PRIVATE_DOMAIN_NAME = 'PublicPrivate'
PUBLIC_PRIVATE_DOMAIN = {'Public': 0, 'Private': 1}

COMMUNITY_DOMAIN_NAME = 'Community Name'

TREE_SIZE_DOMAIN_NAME = 'Tree Size'
TREE_SIZE_DOMAIN = {'Small': 0, 'Medium': 1, 'Large': 2}

IN_MEM_ID = 0

OS_PID = os.getpid()

def run():
    __log_info ("Logging to %s" % pp.logger.LOG_FILE)
    
    if os.path.isdir(INTERMEDIATE_OUTPUT_DIR):
        shutil.rmtree(INTERMEDIATE_OUTPUT_DIR)
    
    os.makedirs(WORK_DIR, exist_ok=True)
    os.makedirs(INTERMEDIATE_OUTPUT_DIR)
    os.makedirs(os.path.dirname(COMBINED_SPACES_OUTPUT_GDB), exist_ok=True)
    os.makedirs(os.path.dirname(COMBINED_TREES_OUTPUT_GDB), exist_ok=True)
    os.makedirs(COMMUNITY_OUTPUT_DIR, exist_ok=True)
              
    community_specs = __get_communities(SUBSET_START_POINT, SUBSET_COUNT)
    
    if IS_CREATE_SPACES:
        if PROCESSORS > 1:
            p = multiprocessing.Pool(PROCESSORS)
            p.map(run_mp, community_specs, 1)
            p.close()        
        else:
            # Process each community past the alphabetical starting point
            for community_spec in community_specs:
                run_mp (community_spec)
                
    if IS_COMBINE_SPACES:              
        __combine_spaces_fcs (community_specs)
        
    if IS_CREATE_TREES:
        for community_spec in community_specs:
            community_spaces_fc = __get_community_spaces_fc_name (community_spec[0])
            community_trees_fc = __get_community_trees_fc_name (community_spec[0])
            __delete ([community_trees_fc])           
            pp.locate_trees.run (community_spaces_fc, None, TREE_TEMPLATE_FC, community_trees_fc)
            
                
    if IS_COMBINE_TREES:              
        __combine_trees_fcs (community_specs)            
    
    __log_info('Complete: %s' % ([c[0] for c in community_specs]))
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
        
        use_in_mem = USE_IN_MEM if community != 'CHICAGO TWSHP' else False
        
        if use_in_mem:
            arcpy.Delete_management('in_memory')
            intermediate_output_gdb = None
        else:
            intermediate_output_gdb = os.path.join(INTERMEDIATE_OUTPUT_DIR,  'intermediate_%i.gdb' %(OS_PID))
            if not arcpy.Exists(intermediate_output_gdb):
                arcpy.CreateFileGDB_management(os.path.dirname(intermediate_output_gdb), os.path.basename(intermediate_output_gdb))

    
        canopy_clipped = __get_intermediate_name (intermediate_output_gdb, 'canopy_clipped', idx, use_in_mem)
        plantable_region_clipped = __get_intermediate_name (intermediate_output_gdb, 'plantable_region_clipped', idx, use_in_mem)
        buildings_clipped = __get_intermediate_name (intermediate_output_gdb, 'buildings_clipped', idx, use_in_mem)
        minus_trees = __get_intermediate_name (intermediate_output_gdb, 'minus_trees', idx, use_in_mem)
        minus_trees_buildings = __get_intermediate_name (intermediate_output_gdb, 'minus_trees_buildings', idx, use_in_mem)
        plantable_poly = __get_intermediate_name (intermediate_output_gdb, 'plantable_poly', idx, use_in_mem)
        plantable_single_poly = __get_intermediate_name (intermediate_output_gdb, 'plantable_single_poly', idx, use_in_mem)
        plantable_muni = __get_intermediate_name (intermediate_output_gdb, 'plantable_muni', idx, use_in_mem)
        plantable_muni_landuse = __get_intermediate_name (intermediate_output_gdb, 'plantable_muni_landuse', idx, use_in_mem)
        plantable_muni_landuse_public = __get_intermediate_name (intermediate_output_gdb, 'plantable_muni_landuse_public', idx, use_in_mem)
        
        community_fc = __get_community_spaces_fc_name (community)
        community_gdb = os.path.dirname(community_fc)
        if not arcpy.Exists(community_gdb):
            arcpy.CreateFileGDB_management(os.path.dirname(community_gdb), os.path.basename(community_gdb))
        __delete ([community_fc])
                   
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

        __log_debug ('Repair invalid features', community)        
        arcpy.management.RepairGeometry(plantable_poly, "DELETE_NULL", "ESRI")
    
        __log_debug ('Converting multipart polygons to singlepart', community)        
        arcpy.MultipartToSinglepart_management(plantable_poly, plantable_single_poly)            
        __delete( [plantable_poly] )
    
        __log_debug ('Spatial join', community)        
        arcpy.SpatialJoin_analysis(plantable_single_poly, MUNI_COMMUNITY_AREA, plantable_muni, "JOIN_ONE_TO_ONE", "KEEP_ALL", "", "INTERSECT", "", "")
        __delete( [plantable_single_poly] )
    
        __log_debug ('Identify land use', community)        
        arcpy.Identity_analysis(plantable_muni, LAND_USE_2015, plantable_muni_landuse, "ALL", "", "NO_RELATIONSHIPS")
        __delete( [plantable_muni] )
    
        __log_debug ('Identify public land', community)        
        arcpy.Identity_analysis(plantable_muni_landuse, PUBLIC_LAND, plantable_muni_landuse_public, "ALL", "", "NO_RELATIONSHIPS")
        __delete( [plantable_muni_landuse] )
    
        __log_debug ('Add and populate the "CommunityID" field', community)   
        arcpy.management.CalculateField(plantable_muni_landuse_public, SPACES_COMMUNITY_COL, '%i' % (idx), "PYTHON3", "", "SHORT")
    
        __log_debug ('Add and populate the "Public" field', community)   
        arcpy.management.CalculateField(plantable_muni_landuse_public, SPACES_PUBLIC_PRIVATE_COL, "is_public(!FID_%s!)" % (os.path.basename(PUBLIC_LAND)), "PYTHON3", r"""def is_public (fid):
            if fid == -1:
                return 0
            else:
                return 1""", "SHORT")
    
        __log_debug ('Trim excess fields', community)   
        __trim_excess_fields (plantable_muni_landuse_public, ['objectid', 'shape', 'shape_area', 'shape_length', SPACES_LANDUSE_COL, SPACES_PUBLIC_PRIVATE_COL, SPACES_COMMUNITY_COL])
    
        __save_community (plantable_muni_landuse_public, community_fc)
        __delete( [plantable_muni_landuse_public] )

            
    except Exception as ex:
      __log_debug ('Exception: %s' % (str(ex)))
      raise ex
        
    return community_fc
      

    
        
def __get_communities (start_point, count):
    communities = []
    with arcpy.da.SearchCursor(MUNI_COMMUNITY_AREA, ['OBJECTID', 'COMMUNITY', 'SHAPE@']) as cursor:
        for attr_vals in cursor:
            communities.append( (attr_vals[1], int(attr_vals[2].getArea('PLANAR', 'ACRES')), attr_vals[0]) )

    community_names = [c[0] for c in communities]
    if len(community_names) != len(set(community_names)):
        raise Exception ("Duplicate community names: %s" % str(community_names))
        
    communities_sorted = [c for c in sorted(communities, key=lambda x: x[0].lower()) if c[0].lower() >= start_point.lower()][0:count]        
    return communities_sorted



def  __get_intermediate_name (intermediate_output_gdb, name, idx, use_in_mem):
    global IN_MEM_ID
    
    if use_in_mem:
        IN_MEM_ID = IN_MEM_ID + 1
        fn = os.path.join('in_memory', name[0:3] + '_%i' % idx + '_' +  str(IN_MEM_ID))
    else:
        fn = os.path.join(intermediate_output_gdb, name + '_%i' % idx )
    __delete ([fn])
    return fn


def __get_community_spaces_fc_name (community):
    community_gdb = os.path.join(COMMUNITY_OUTPUT_DIR, community.replace(' ','') + '.gdb')
    community_fc =  os.path.join(community_gdb, 'plantable')
    return community_fc

def __get_community_trees_fc_name (community):
    community_gdb = os.path.join(COMMUNITY_OUTPUT_DIR, community.replace(' ','') + '.gdb')
    community_fc =  os.path.join(community_gdb, 'trees')
    return community_fc


def __log_info (text, community = None):
    __log (text, False, community)
           
def __log_debug (text, community = None):
    __log (text, True, community   )        

def __log (text, is_debug, community = None):
    if community is None:
        t = "%i: %s" % (OS_PID, text)
    else:
        t ="%i %s: %s" % (OS_PID, community, text)
    if is_debug:
        logger.debug(t)
    else:
        logger.info(t)
    return
    

def __delete (obj_list):
    for obj in obj_list:
        arcpy.Delete_management(obj)
    return


def __trim_excess_fields (fc, keep_fields):
    all_fields = set([f.name.lower() for f in arcpy.ListFields(fc)])
    keep_fields = set([k.lower() for k in keep_fields])
    arcpy.DeleteField_management(fc, ';'.join(all_fields - keep_fields))
    return



def __save_community (in_fc, out_fc):
    temp_out_fc = os.path.join(os.path.dirname(out_fc), os.path.basename(out_fc) + '_projected')
    if arcpy.da.Describe(in_fc)['catalogPath'].startswith('in_memory\\'):
        arcpy.CopyFeatures_management(in_fc, temp_out_fc)
    else:        
        arcpy.Copy_management(in_fc, temp_out_fc)   
    arcpy.management.Project(temp_out_fc, out_fc, arcpy.Describe(TREE_TEMPLATE_FC).spatialReference)
    __delete ([temp_out_fc])
    return



def __combine_spaces_fcs (community_specs):
    __log_debug ('Combining spaces feature classes')
    communities  = [c[0] for c in community_specs]
    community_fcs = [__get_community_spaces_fc_name (c) for c in communities]
    community_ids = [str(c[2]) for c in community_specs]
    
    out_fc = os.path.join(COMBINED_SPACES_OUTPUT_GDB, 'plantable')   
        
    if not arcpy.Exists(COMBINED_SPACES_OUTPUT_GDB):
        arcpy.CreateFileGDB_management(os.path.dirname(COMBINED_SPACES_OUTPUT_GDB), os.path.basename(COMBINED_SPACES_OUTPUT_GDB))
        __create_domains (COMBINED_SPACES_OUTPUT_GDB)
    
    if IS_SCRATCH_COMBINED_FCS:
        __log_debug ('Deleting combined spaces feature class')
        __delete ([out_fc])
        
        
    if not arcpy.Exists(out_fc):       
        __log_debug ('Creating combined spaces feature class')
        sr = arcpy.Describe(community_fcs[0]).spatialReference
        arcpy.CreateFeatureclass_management(os.path.dirname(out_fc), os.path.basename(out_fc), 'POLYGON', community_fcs[0], "DISABLED", "DISABLED", sr)
        arcpy.management.AssignDomainToField(out_fc, SPACES_LANDUSE_COL, LANDUSE_DOMAIN_NAME)
        arcpy.management.AssignDomainToField(out_fc, SPACES_PUBLIC_PRIVATE_COL, PUBLIC_PRIVATE_DOMAIN_NAME)
        arcpy.management.AssignDomainToField(out_fc, SPACES_COMMUNITY_COL, COMMUNITY_DOMAIN_NAME)         
        arcpy.management.AddIndex(out_fc, SPACES_COMMUNITY_COL, "IDX_Comm", "NON_UNIQUE", "NON_ASCENDING")
        arcpy.management.AddIndex(out_fc, SPACES_LANDUSE_COL, "IDX_LandUse", "NON_UNIQUE", "NON_ASCENDING")
        
    if not IS_SCRATCH_COMBINED_FCS:        
        __log_debug ('Deleting existing features in combined spaces feature class')
        where = "%s IN (%s)" % (SPACES_COMMUNITY_COL, ','.join(community_ids))
        old_records = arcpy.SelectLayerByAttribute_management(out_fc, 'NEW_SELECTION', where)[0]
        arcpy.management.DeleteFeatures(old_records)

 
    __log_info ('Write to combined spaces feature class')
    arcpy.management.Append(community_fcs, out_fc)
   
    return



def __combine_trees_fcs (community_specs):
    __log_debug ('Combining trees feature classes')
    communities  = [c[0] for c in community_specs]
    community_fcs = [__get_community_trees_fc_name (c) for c in communities]
    community_ids = [str(c[2]) for c in community_specs]
    
    out_fc = os.path.join(COMBINED_TREES_OUTPUT_GDB, 'trees')   
        
    if not arcpy.Exists(COMBINED_TREES_OUTPUT_GDB):
        arcpy.CreateFileGDB_management(os.path.dirname(COMBINED_TREES_OUTPUT_GDB), os.path.basename(COMBINED_TREES_OUTPUT_GDB))
        __create_domains (COMBINED_TREES_OUTPUT_GDB)
    
    if IS_SCRATCH_COMBINED_FCS:
        __log_debug ('Deleting combined trees feature class')
        __delete ([out_fc])
        
    if not arcpy.Exists(out_fc):       
        __log_debug ('Creating combined trees feature class')
        sr = arcpy.Describe(community_fcs[0]).spatialReference
        arcpy.CreateFeatureclass_management(os.path.dirname(out_fc), os.path.basename(out_fc), 'POINT', community_fcs[0], "DISABLED", "DISABLED", sr)
        arcpy.management.AssignDomainToField(out_fc, TREES_LANDUSE_COL, LANDUSE_DOMAIN_NAME)
        arcpy.management.AssignDomainToField(out_fc, TREES_PUBLIC_PRIVATE_COL, PUBLIC_PRIVATE_DOMAIN_NAME)
        arcpy.management.AssignDomainToField(out_fc, TREES_COMMUNITY_COL, COMMUNITY_DOMAIN_NAME)    
        arcpy.management.AssignDomainToField(out_fc, TREES_SIZE_COL, TREE_SIZE_DOMAIN_NAME) 
        arcpy.management.AddIndex(out_fc, TREES_COMMUNITY_COL, "IDX_Comm", "NON_UNIQUE", "NON_ASCENDING")
        arcpy.management.AddIndex(out_fc, TREES_LANDUSE_COL, "IDX_LandUse", "NON_UNIQUE", "NON_ASCENDING")
        arcpy.management.AddIndex(out_fc, TREES_PUBLIC_PRIVATE_COL, "IDX_PublicPrivate", "NON_UNIQUE", "NON_ASCENDING")
        
    if not IS_SCRATCH_COMBINED_FCS:
        __log_debug ('Deleting existing features in combined trees feature class')
        where = "%s IN (%s)" % (TREES_COMMUNITY_COL, ','.join(community_ids))
        old_records = arcpy.SelectLayerByAttribute_management(out_fc, 'NEW_SELECTION', where)[0]
        arcpy.management.DeleteFeatures(old_records)
        
    __log_info ('Write to combined trees feature class')
    arcpy.management.Append(community_fcs, out_fc)
   
    return


def __create_domains (workspace):
    # Land use
    arcpy.management.CreateDomain(workspace, LANDUSE_DOMAIN_NAME, None, 'SHORT', 'CODED')
    for d in LANDUSE_DOMAIN.keys():        
        arcpy.management.AddCodedValueToDomain(workspace, LANDUSE_DOMAIN_NAME, LANDUSE_DOMAIN[d], d)
    # Public/Private
    arcpy.management.CreateDomain(workspace, PUBLIC_PRIVATE_DOMAIN_NAME, None, 'SHORT', 'CODED')
    for d in PUBLIC_PRIVATE_DOMAIN.keys():
        arcpy.management.AddCodedValueToDomain(workspace, PUBLIC_PRIVATE_DOMAIN_NAME, PUBLIC_PRIVATE_DOMAIN[d], d)
    # Tree size
    arcpy.management.CreateDomain(workspace, TREE_SIZE_DOMAIN_NAME, None, 'SHORT', 'CODED')
    for d in TREE_SIZE_DOMAIN.keys():
        arcpy.management.AddCodedValueToDomain(workspace, TREE_SIZE_DOMAIN_NAME, TREE_SIZE_DOMAIN[d], d)
    # Community name
    arcpy.management.CreateDomain(workspace, COMMUNITY_DOMAIN_NAME, None, 'SHORT', 'CODED')
    with arcpy.da.SearchCursor(MUNI_COMMUNITY_AREA, ['OBJECTID', 'Community']) as cursor:
            for attr_vals in cursor:
                arcpy.management.AddCodedValueToDomain(workspace, COMMUNITY_DOMAIN_NAME, attr_vals[0], attr_vals[1])
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


