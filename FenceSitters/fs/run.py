import sys, os
import fs.prepare_canopy_data
import traceback


# COUNTY_SPECS = {
#     'Dupage': {
#         'tile_folder': r'E:\Local_Geodata\Fence_Sitters_2023\Chicago Regional Tree Crown Tiles\tiles_dupage\TreeObjects',
#         'tile_dimension': 2500.0,
#         'scratch_workspace': r'E:\Local_Geodata\Fence_Sitters_2023\DuPage\Work',
#         'output_feature_class': r'E:\Local_Geodata\Fence_Sitters_2023\DuPage\TreeObjectsDupage.gdb\canopies',
#         },
#     'Kendall': {
#         'tile_folder': r'E:\Local_Geodata\Fence_Sitters_2023\Chicago Regional Tree Crown Tiles\tiles_kendall\TreeObjects',
#         'tile_dimension': 2000.0,
#         'scratch_workspace': r'E:\Local_Geodata\Fence_Sitters_2023\Kendall\Work',
#         'output_feature_class': r'E:\Local_Geodata\Fence_Sitters_2023\Kendall\TreeObjectsKendall.gdb\canopies',
#         },
#     'Kane': {
#         'tile_folder': r'E:\Local_Geodata\Fence_Sitters_2023\Chicago Regional Tree Crown Tiles\tiles_kane\TreeObjects',
#         'tile_dimension': 2500.0,
#         'scratch_workspace': r'E:\Local_Geodata\Fence_Sitters_2023\Kane\Work',
#         'output_feature_class': r'E:\Local_Geodata\Fence_Sitters_2023\Kane\TreeObjectsKane.gdb\canopies',
#         },
#     'McHenry': {
#         'tile_folder': r'E:\Local_Geodata\Fence_Sitters_2023\Chicago Regional Tree Crown Tiles\tiles_mchenry\TreeObjects',
#         'tile_dimension': 2500.0,
#         'scratch_workspace': r'E:\Local_Geodata\Fence_Sitters_2023\McHenry\Work',
#         'output_feature_class': r'E:\Local_Geodata\Fence_Sitters_2023\McHenry\TreeObjectsMcHenry.gdb\canopies',
#         },
#     'Lake': {
#         'tile_folder': r'E:\Local_Geodata\Fence_Sitters_2023\Chicago Regional Tree Crown Tiles\tiles_lake\TreeObjects',
#         'tile_dimension': 2500.0,
#         'scratch_workspace': r'E:\Local_Geodata\Fence_Sitters_2023\Lake\Work',
#         'output_feature_class': r'E:\Local_Geodata\Fence_Sitters_2023\Lake\TreeObjectsLake.gdb\canopies',
#         },
#     }

BASE_DIR = r'C:\Users\dmorrison\crti'
TILES_DIR = os.path.join(BASE_DIR, r'data\Chicago Regional Tree Crown Tiles')
WORK_DIR = os.path.join(BASE_DIR, r'work\fence_sitters')
OUTPUT_GDB = os.path.join(BASE_DIR, r'output\fence_sitters\canopies.gdb')


COUNTY_SPECS = {
    # 'Kendall': {
    #     'tile_folder': os.path.join(TILES_DIR, r'tiles_kendall\TreeObjects'),
    #     'tile_dimension': 2000.0,
    #     'scratch_workspace': os.path.join(WORK_DIR, r'kendall'),
    #     'output_feature_class': os.path.join(OUTPUT_GDB, r'kendall')
    #     },
    'Kane': {
        'tile_folder': os.path.join(TILES_DIR, r'tiles_kane\TreeObjects'),
        'tile_dimension': 2500.0,
        'scratch_workspace': os.path.join(WORK_DIR, r'kane'),
        'output_feature_class': os.path.join(OUTPUT_GDB, r'kane')
        },
    'McHenry': {
        'tile_folder': os.path.join(TILES_DIR, r'tiles_mchenry\TreeObjects'),
        'tile_dimension': 2500.0,
        'scratch_workspace': os.path.join(WORK_DIR, r'mchenry'),
        'output_feature_class': os.path.join(OUTPUT_GDB, r'mchenry')
        },
    'Lake': {
        'tile_folder': os.path.join(TILES_DIR, r'tiles_lake\TreeObjects'),
        'tile_dimension': 2500.0,
        'scratch_workspace': os.path.join(WORK_DIR, r'lake'),
        'output_feature_class': os.path.join(OUTPUT_GDB, r'lake')
        },
    # 'Dupage': {
    #     'tile_folder': os.path.join(TILES_DIR, r'tiles_dupage\TreeObjects'),
    #     'tile_dimension': 2500.0,
    #     'scratch_workspace': os.path.join(WORK_DIR, r'dupage'),
    #     'output_feature_class': os.path.join(OUTPUT_GDB, r'dupage')
    #     },
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
        start_step = 0
        s = COUNTY_SPECS[county]
        fs.prepare_canopy_data.prepare_canopy_data (s['tile_folder'], s['tile_dimension'], start_step, s['scratch_workspace'], s['output_feature_class'])
   
    
    
    
