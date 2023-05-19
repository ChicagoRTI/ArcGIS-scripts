import os
import fs.prepare_canopy_data
import traceback



BASE_DIR = r'C:\Users\dmorrison\crti'
TILES_DIR = os.path.join(BASE_DIR, r'data\Chicago Regional Tree Crown Tiles')
WORK_DIR = os.path.join(BASE_DIR, r'work\fence_sitters')
OUTPUT_GDB = os.path.join(BASE_DIR, r'output\fence_sitters\canopies.gdb')


COUNTY_SPECS = {
    # 'Cook': {
    #     'tile_folder': os.path.join(TILES_DIR, r'tiles_cook\TreeObjects'),
    #     'tile_dimension': 2500.0,
    #     'scratch_workspace': os.path.join(WORK_DIR, r'cook'),
    #     'output_feature_class': os.path.join(OUTPUT_GDB, r'cook')
    #     },
    # 'Kendall': {
    #     'tile_folder': os.path.join(TILES_DIR, r'tiles_kendall\TreeObjects'),
    #     'tile_dimension': 2000.0,
    #     'scratch_workspace': os.path.join(WORK_DIR, r'kendall'),
    #     'output_feature_class': os.path.join(OUTPUT_GDB, r'kendall')
    #     },
    # 'Kane': {
    #     'tile_folder': os.path.join(TILES_DIR, r'tiles_kane\TreeObjects'),
    #     'tile_dimension': 2500.0,
    #     'scratch_workspace': os.path.join(WORK_DIR, r'kane'),
    #     'output_feature_class': os.path.join(OUTPUT_GDB, r'kane')
    #     },
    # 'McHenry': {
    #     'tile_folder': os.path.join(TILES_DIR, r'tiles_mchenry\TreeObjects'),
    #     'tile_dimension': 2500.0,
    #     'scratch_workspace': os.path.join(WORK_DIR, r'mchenry'),
    #     'output_feature_class': os.path.join(OUTPUT_GDB, r'mchenry')
    #     },
    # 'Lake': {
    #     'tile_folder': os.path.join(TILES_DIR, r'tiles_lake\TreeObjects'),
    #     'tile_dimension': 2500.0,
    #     'scratch_workspace': os.path.join(WORK_DIR, r'lake'),
    #     'output_feature_class': os.path.join(OUTPUT_GDB, r'lake')
    #     },
    # 'Dupage': {
    #     'tile_folder': os.path.join(TILES_DIR, r'tiles_dupage\TreeObjects'),
    #     'tile_dimension': 2500.0,
    #     'scratch_workspace': os.path.join(WORK_DIR, r'dupage'),
    #     'output_feature_class': os.path.join(OUTPUT_GDB, r'dupage')
    #     },
    'Will': {
        'tile_folder': os.path.join(TILES_DIR, r'tiles_will\TreeObjects'),
        'tile_dimension': 2500.0,
        'scratch_workspace': os.path.join(WORK_DIR, r'will'),
        'output_feature_class': os.path.join(OUTPUT_GDB, r'will')
        },
    }


def run_from_bat (county, start_step):
    try:
        s = COUNTY_SPECS[county]
        fs.prepare_canopy_data.prepare_canopy_data (s['tile_folder'], s['tile_dimension'], start_step, s['scratch_workspace'], s['output_feature_class'])
    except Exception as e:
        print("Exception: " + str(e))
        print(traceback.format_exc())
        raise
    return



if __name__ == '__main__':
    # county = 'Dupage'
    # start_step = 0
    # s = COUNTY_SPECS[county]
    # fs.prepare_canopy_data.prepare_canopy_data (s['tile_folder'], s['tile_dimension'], start_step, s['scratch_workspace'], s['output_feature_class'])
    for county in COUNTY_SPECS.keys():
        start_step = 1
        s = COUNTY_SPECS[county]
        fs.prepare_canopy_data.prepare_canopy_data (s['tile_folder'], s['tile_dimension'], start_step, s['scratch_workspace'], s['output_feature_class'])
   
    
    
    
