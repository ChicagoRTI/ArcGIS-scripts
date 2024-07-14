import getpass
import arcpy
from arcgis.gis import GIS

# Rebuild the host feature layer species domains. This should be run whenever the species list changes
# The enterprise portal must be the active portal in ArcGIS Pro for this to run


SPECIES_LIST_CLEAN = 'https://services6.arcgis.com/WNXWcrlG6DXHeQ5W/arcgis/rest/services/Species_List/FeatureServer/0'
TREES_ITEM_ID = 'b2d057c4927040fe9312cd91cf794b6e'


def run ():
    
    # user = input('Portal user ID: ').strip() or "DMorrison@mortonarb.org"
    url = 'https://gis.mortonarb.org/portal/home/'
    # pw = getpass.getpass(prompt='Portal Password: ')
    # gis = GIS(url=url, username=user, password=pw)
    gis = GIS(url=url)
    item = gis.content.get(TREES_ITEM_ID)
        
    scientific_field_dict = {
        'name': 'latin_name',
        'domain': {
            'type': 'codedValue',
            'name': 'latin_name',
            'codedValues': []
        }
    }
    
    common_field_dict = {
        'name': 'common_name',
        'domain': {
            'type': 'codedValue',
            'name': 'common_name',
            'codedValues': []
        }
    }
    
    with arcpy.da.SearchCursor(SPECIES_LIST_CLEAN, ['common_name', 'scientific_name']) as cursor:
        for common_name, latin_name in cursor:
            scientific_field_dict['domain']['codedValues'].append({'name': f'{latin_name} ({common_name})', 'code': latin_name})
            common_field_dict['domain']['codedValues'].append({'name': f'{common_name} ({latin_name})', 'code': common_name})

            print(item.layers[0].manager.update_definition({"fields":[scientific_field_dict]}))      
            print(item.layers[0].manager.update_definition({"fields":[common_field_dict]}))   
            return
    return
    
    



if __name__ == '__main__':
    run()