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
IS_UPDATE_TREE_STATS = bool(int(config['actions']['update_tree_stats']))
IS_COMBINE_SPACES = bool(int(config['actions']['combine_space_feature_classes']))
IS_COMBINE_TREES = bool(int(config['actions']['combine_tree_site_feature_classes']))
IS_SCRATCH_OUTPUT_DATA = bool(int(config['actions']['scratch_combined_output_data']))


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
COMMUNITY_SPACES_FC = 'plantable'
COMMUNITY_TREES_FC = 'trees'
COMMUNITY_TREES_FC = 'stats'


COMBINED_OUTPUT_DIR = os.path.join(WORK_DIR, r'output\combined')
COMBINED_SPACES_OUTPUT_GDB = os.path.join(COMBINED_OUTPUT_DIR, 'spaces.gdb')
COMBINED_SPACES_FC = os.path.join(COMBINED_SPACES_OUTPUT_GDB, 'plantable')
COMBINED_TREES_OUTPUT_GDB = os.path.join(COMBINED_OUTPUT_DIR, 'trees.gdb')
COMBINED_TREES_FC = os.path.join(COMBINED_TREES_OUTPUT_GDB, 'trees')
COMBINED_STATS_FC = os.path.join(COMBINED_TREES_OUTPUT_GDB, 'stats')

STATS_SPEC = [('community_id', 'SHORT'),
              ('acres', 'FLOAT'),
              ('trees', 'LONG'),
              ('trees_per_acre', 'FLOAT'),
              ('percent_canopy', 'FLOAT'),
              ('percent_buildings', 'FLOAT')]


STATS_COMMUNITY_COL = 'community_id'

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
        arcpy.Delete_management(obj)
    return