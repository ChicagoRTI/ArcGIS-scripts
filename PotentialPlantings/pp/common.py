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


#COMBINED_OUTPUT_DIR = os.path.join(WORK_DIR, r'output\merged')
#COMBINED_OUTPUT_GDB = os.path.join(COMBINED_OUTPUT_DIR, 'pp.gdb')
#COMBINED_SPACES_OUTPUT_GDB = os.path.join(COMBINED_OUTPUT_DIR, 'spaces.gdb')
#COMBINED_SPACES_FC = os.path.join(COMBINED_OUTPUT_GDB, 'spaces')
#COMBINED_TREES_OUTPUT_GDB = os.path.join(COMBINED_OUTPUT_DIR, 'trees.gdb')
#COMBINED_TREES_FC = os.path.join(COMBINED_OUTPUT_GDB, 'trees')
#COMBINED_STATS_FC = os.path.join(COMBINED_OUTPUT_GDB, 'stats')


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
PUBLIC_PRIVATE_DOMAIN = {'Public': 0, 'Private': 1}

COMMUNITY_DOMAIN_NAME = 'Community Name'

TREE_SIZE_DOMAIN_NAME = 'Tree Size'
TREE_SIZE_DOMAIN = {'Small': 0, 'Medium': 1, 'Large': 2}

DOMAIN_ASSIGNMENTS = {SPACES_GDB:  [COMMUNITY_DOMAIN_NAME],
                      TREES_AND_STATS_GDB:  [LANDUSE_DOMAIN_NAME,
                                             PUBLIC_PRIVATE_DOMAIN_NAME,
                                             COMMUNITY_DOMAIN_NAME, 
                                             TREE_SIZE_DOMAIN_NAME]}

# DOMAIN_ASSIGNMENTS = {SPACES_GDB:           [(COMMUNITY_DOMAIN_NAME, SPACES_COMMUNITY_COL)], 
#                       TREES_AND_STATS_GDB:  [(LANDUSE_DOMAIN_NAME, TREES_LANDUSE_COL), 
#                                              (PUBLIC_PRIVATE_DOMAIN_NAME, TREES_PUBLIC_PRIVATE_COL),
#                                              (COMMUNITY_DOMAIN_NAME, TREES_COMMUNITY_COL),
#                                              (TREE_SIZE_DOMAIN_NAME, TREES_SIZE_COL)]}

IN_MEM_ID = 0

OS_PID = os.getpid()


def get_community_gdb (community):
    community_gdb = os.path.join(COMMUNITIES_DIR, community.replace(' ','') + '.gdb')
    return community_gdb


def get_community_spaces_fc_name (community):
    community_gdb = get_community_gdb (community)
    community_fc =  os.path.join(community_gdb, COMMUNITY_SPACES_FC)
    return community_fc


def get_community_trees_fc_name (community):
    community_gdb = get_community_gdb (community)
    community_fc =  os.path.join(community_gdb, COMMUNITY_TREES_FC)
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