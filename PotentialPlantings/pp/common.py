import os
import arcpy
import configparser

import pp.logger
logger = pp.logger.get('pp_log')

cfg_fn = os.path.normpath(__file__ + '/../../local/plantable_script.properties')
config = configparser.ConfigParser()
config.read(cfg_fn)

IS_CREATE_SPACES = bool(int(config['actions']['create_space_feature_classes']))
IS_CREATE_TREES = bool(int(config['actions']['create_tree_feature_classes']))
IS_COMBINE_SPACES = bool(int(config['actions']['combine_space_feature_classes']))
IS_COMBINE_TREES = bool(int(config['actions']['combine_tree_site_feature_classes']))
IS_SCRATCH_OUTPUT_DATA = bool(int(config['actions']['scratch_combined_output_data']))

# Runtime
PROCESSORS = int(config['runtime']['processors'])
USE_IN_MEM = bool(int(config['runtime']['is_use_in_mem']))
# Input Data
BUILDINGS_EXPAND_TIF = config['input_data']['buildings_tif']
CANOPY_EXPAND_TIF = config['input_data']['canopy_tif']
PLANTABLE_REGION_TIF = config['input_data']['plantable_region_tif']
MUNI_COMMUNITY_AREA =config['input_data']['muni_community_area']
LAND_USE_2015 = config['input_data']['land_use_2015']
PUBLIC_LAND = config['input_data']['public_land']
SPACES_TEMPLATE_FC = config['input_data']['spaces_template_fc']
TREES_TEMPLATE_FC = config['input_data']['trees_template_fc']
# Output Data
SPACES_GDB = config['output_data']['spaces_gdb']
TREES_AND_STATS_GDB = config['output_data']['trees_and_stats_gdb']
COMMUNITIES_DIR = config['output_data']['communities_dir']
TEMP_DIR = config['output_data']['temp_dir']
# Community subset
SUBSET_LIST = config['community_subset']['list']
SUBSET_START_POINT = config['community_subset']['start_point']
SUBSET_COUNT = int(config['community_subset']['number'])


SPACES_FC = os.path.join(SPACES_GDB, 'spaces')
TREES_FC = os.path.join(TREES_AND_STATS_GDB, 'trees')
STATS_FC = os.path.join(TREES_AND_STATS_GDB, 'stats')

COMMUNITIES_DIR = config['output_data']['communities_dir']
COMMUNITY_SPACES_FC = 'spaces'
COMMUNITY_TREES_FC = 'trees'
COMMUNITY_SPACE_STATS_TBL = 'space_stats'
COMMUNITY_TREE_STATS_TBL = 'tree_stats'


STAT_TREES = 'trees'
STAT_TREES_PER_ACRE = 'trees_per_acre'
STAT_PERCENT_CANOPY = 'percent_canopy'
STAT_PERCENT_BUILDINGS = 'percent_buildings'
STAT_PERCENT_CANOPY = 'percent_canopy'
STAT_SMALL = 'small'
STAT_MEDIUM = 'medium'
STAT_LARGE = 'large'

SPACE_STATS = [STAT_PERCENT_CANOPY, STAT_PERCENT_BUILDINGS]
DERIVED_STATS = [STAT_TREES, STAT_TREES_PER_ACRE]
SIZE_STATS = [STAT_SMALL, STAT_MEDIUM, STAT_LARGE]

COMMUNITY_STATS_SPEC = [('community_id', 'SHORT'),
                        ('acres', 'FLOAT')]

SPACE_STATS_SPEC = [('percent_canopy', 'FLOAT'),
                    ('percent_buildings', 'FLOAT')]

TREE_STATS_SPEC = [('small', 'LONG'),
                  ('medium', 'LONG'),
                  ('large', 'LONG'),
                  ('ag', 'LONG'),
                  ('commercial', 'LONG'),
                  ('industrial', 'LONG'),
                  ('institutional', 'LONG'),
                  ('openSpace', 'LONG'),
                  ('residential', 'LONG'),
                  ('transit', 'LONG'),
                  ('vacant', 'LONG'),
                  ('water', 'LONG'),
                  ('other', 'LONG'),
                  ('private', 'LONG'),
                  ('public', 'LONG')]

DERIVED_STATS =   [('trees', 'LONG'),
                  ('trees_per_acre', 'FLOAT'),
                  ('percent_other', 'FLOAT')]


STATS_COMMUNITY_COL = 'community_id'

SPACES_LANDUSE_COL = 'land_use'
SPACES_PUBLIC_PRIVATE_COL = 'is_public'
SPACES_COMMUNITY_COL = 'community_id'

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
PUBLIC_PRIVATE_DOMAIN = {'Private': 0, 'Public': 1}

COMMUNITY_DOMAIN_NAME = 'Community Name'

TREE_SIZE_DOMAIN_NAME = 'Tree Size'
TREE_SIZE_DOMAIN = {'Small': 0, 'Medium': 1, 'Large': 2}

DOMAIN_ASSIGNMENTS = {SPACES_GDB:  [COMMUNITY_DOMAIN_NAME],
                      TREES_AND_STATS_GDB:  [LANDUSE_DOMAIN_NAME,
                                             PUBLIC_PRIVATE_DOMAIN_NAME,
                                             COMMUNITY_DOMAIN_NAME, 
                                             TREE_SIZE_DOMAIN_NAME]}

TREES_INDEX_SPEC  = [(TREES_LANDUSE_COL, 'IDX_LandUse'),
                     (TREES_PUBLIC_PRIVATE_COL, 'IDX_PublicPrivate'),
                     (TREES_COMMUNITY_COL, 'IDX_Community'),
                     (TREES_SIZE_COL, 'IDX_TreeSize')]
SPACES_INDEX_SPEC  = [(SPACES_COMMUNITY_COL, 'IDX_Community')]


IN_MEM_ID = 0

OS_PID = os.getpid()


def get_community_gdb (community):
    community_gdb = os.path.join(COMMUNITIES_DIR, community.replace(' ','') + '.gdb')
    return community_gdb


def get_community_fc_name (community, fc_type):
    community_gdb = get_community_gdb (community)
    community_fc =  os.path.join(community_gdb, fc_type)
    return community_fc


def create_domains (workspace, domain_names):
    active_domains = arcpy.Describe(workspace).domains
    # Land use
    if LANDUSE_DOMAIN_NAME not in active_domains and LANDUSE_DOMAIN_NAME in domain_names:
        arcpy.management.CreateDomain(workspace, LANDUSE_DOMAIN_NAME, None, 'SHORT', 'CODED')
        for d in LANDUSE_DOMAIN.keys():        
            arcpy.management.AddCodedValueToDomain(workspace, LANDUSE_DOMAIN_NAME, LANDUSE_DOMAIN[d], d)
    # Public/Private
    if PUBLIC_PRIVATE_DOMAIN_NAME not in active_domains and PUBLIC_PRIVATE_DOMAIN_NAME in domain_names:
        arcpy.management.CreateDomain(workspace, PUBLIC_PRIVATE_DOMAIN_NAME, None, 'SHORT', 'CODED')
        for d in PUBLIC_PRIVATE_DOMAIN.keys():
            arcpy.management.AddCodedValueToDomain(workspace, PUBLIC_PRIVATE_DOMAIN_NAME, PUBLIC_PRIVATE_DOMAIN[d], d)
    # Tree size
    if TREE_SIZE_DOMAIN_NAME not in active_domains and TREE_SIZE_DOMAIN_NAME in domain_names:
        arcpy.management.CreateDomain(workspace, TREE_SIZE_DOMAIN_NAME, None, 'SHORT', 'CODED')
        for d in TREE_SIZE_DOMAIN.keys():
            arcpy.management.AddCodedValueToDomain(workspace, TREE_SIZE_DOMAIN_NAME, TREE_SIZE_DOMAIN[d], d)
    # Community name
    if COMMUNITY_DOMAIN_NAME not in active_domains and COMMUNITY_DOMAIN_NAME in domain_names:
        arcpy.management.CreateDomain(workspace, COMMUNITY_DOMAIN_NAME, None, 'SHORT', 'CODED')
        with arcpy.da.SearchCursor(MUNI_COMMUNITY_AREA, ['OBJECTID', 'Community']) as cursor:
                for attr_vals in cursor:
                    arcpy.management.AddCodedValueToDomain(workspace, COMMUNITY_DOMAIN_NAME, attr_vals[0], attr_vals[1])
    return 


def prepare_intermediate_output_gdb (use_in_mem):
    if use_in_mem:
        arcpy.Delete_management('in_memory')
        intermediate_output_gdb = None
    else:
        intermediate_output_gdb = os.path.join(TEMP_DIR,  'intermediate_%i.gdb' %(OS_PID))
        if not arcpy.Exists(intermediate_output_gdb):
            arcpy.CreateFileGDB_management(os.path.dirname(intermediate_output_gdb), os.path.basename(intermediate_output_gdb))
    return intermediate_output_gdb


def get_intermediate_name (intermediate_output_gdb, name, idx, use_in_mem):
    global IN_MEM_ID
    
    if use_in_mem:
        IN_MEM_ID = IN_MEM_ID + 1
        fn = os.path.join('in_memory', 'm%i' % (idx) + '_' + name[0:3] + '_' + str(IN_MEM_ID))
    else:
        fn = os.path.join(intermediate_output_gdb, name + '_%i' % idx )
    delete ([fn])
    return fn


def add_indexes (table, index_spec):
     existing_indexes = [i.name for i in arcpy.ListIndexes(table)]
     for field, index in index_spec:
        if index not in existing_indexes:
            log_debug ('Adding index %s to field %s in table %s' % (index, field, table))
            arcpy.management.AddIndex(table, [field], index, "NON_UNIQUE", "NON_ASCENDING")


def remove_indexes (table, index_spec):
    existing_indexes = [i.name for i in arcpy.ListIndexes(table)]
    for field, index in index_spec:
        if index in existing_indexes:
            log_debug ('Removing index %s from field %s in table %s' % (index, field, table))
            arcpy.RemoveIndex_management(table, [index])


def is_in_memory (fc):
    return os.path.dirname(fc).split(os.sep)[-1] == 'in_memory'


def log_info (text, community = None):
    __log (text, False, community)
           
def log_debug (text, community = None):
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
    

def delete (obj_list):
    for obj in obj_list:
        log_debug ("Deleting '%s'" % str(obj))
        arcpy.Delete_management(obj)
    return