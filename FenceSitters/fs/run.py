import sys
import fs.prepare_canopy_data
import traceback


COUNTY_SPECS = {
    'Dupage': {
        'tile_folder': r'E:\Local_Geodata\Fence_Sitters_2023\Chicago Regional Tree Crown Tiles\tiles_dupage\TreeObjects',
        'tile_dimension': 2500.0,
        'scratch_workspace': r'E:\Local_Geodata\Fence_Sitters_2023\DuPage\Work',
        'output_feature_class': r'E:\Local_Geodata\Fence_Sitters_2023\DuPage\TreeObjectsDupage.gdb\canopies',
        },
    'Kendall': {
        'tile_folder': r'E:\Local_Geodata\Fence_Sitters_2023\Chicago Regional Tree Crown Tiles\tiles_kendall\TreeObjects',
        'tile_dimension': 2000.0,
        'scratch_workspace': r'E:\Local_Geodata\Fence_Sitters_2023\Kendall\Work',
        'output_feature_class': r'E:\Local_Geodata\Fence_Sitters_2023\Kendall\TreeObjectsKendall.gdb\canopies',
        },
    'Kane': {
        'tile_folder': r'E:\Local_Geodata\Fence_Sitters_2023\Chicago Regional Tree Crown Tiles\tiles_kane\TreeObjects',
        'tile_dimension': 2500.0,
        'scratch_workspace': r'E:\Local_Geodata\Fence_Sitters_2023\Kane\Work',
        'output_feature_class': r'E:\Local_Geodata\Fence_Sitters_2023\Kane\TreeObjectsKane.gdb\canopies',
        },
    'McHenry': {
        'tile_folder': r'E:\Local_Geodata\Fence_Sitters_2023\Chicago Regional Tree Crown Tiles\tiles_mchenry\TreeObjects',
        'tile_dimension': 2500.0,
        'scratch_workspace': r'E:\Local_Geodata\Fence_Sitters_2023\McHenry\Work',
        'output_feature_class': r'E:\Local_Geodata\Fence_Sitters_2023\McHenry\TreeObjectsMcHenry.gdb\canopies',
        },
    'Lake': {
        'tile_folder': r'E:\Local_Geodata\Fence_Sitters_2023\Chicago Regional Tree Crown Tiles\tiles_lake\TreeObjects',
        'tile_dimension': 2500.0,
        'scratch_workspace': r'E:\Local_Geodata\Fence_Sitters_2023\Lake\Work',
        'output_feature_class': r'E:\Local_Geodata\Fence_Sitters_2023\Lake\TreeObjectsLake.gdb\canopies',
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
    county = 'Lake'
    start_step = 0
    s = COUNTY_SPECS[county]
    fs.prepare_canopy_data.prepare_canopy_data (s['tile_folder'], s['tile_dimension'], start_step, s['scratch_workspace'], s['output_feature_class'])
   
    
    
    
