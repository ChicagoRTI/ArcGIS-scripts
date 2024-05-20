import getpass
import arcpy
from arcgis.gis import GIS

# Rebuild the host feature layer species domains. This should be run whenever the species list changes

SPECIES_LIST_CLEAN = 'https://services6.arcgis.com/WNXWcrlG6DXHeQ5W/arcgis/rest/services/Species_List/FeatureServer/0'
TREES_ITEM_ID = '8cbd16a6807247b081f9836352bafadf'


def run ():
    
    user = input('AGOL user ID: ').strip() or "don.morrison.2000@gmail.com"
    pw = getpass.getpass(prompt='AGOL Password: ')
    gis = GIS(username=user, password=pw)
    item = gis.content.get(TREES_ITEM_ID)
        
    scientific_field_dict = {
        'name': 'scientific_name',
        'domain': {
            'type': 'codedValue',
            'name': 'scientific_name',
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
        for common_name, scientific_name in cursor:
            scientific_field_dict['domain']['codedValues'].append({'name': f'{scientific_name} ({common_name})', 'code': scientific_name})
            common_field_dict['domain']['codedValues'].append({'name': f'{common_name} ({scientific_name})', 'code': common_name})

    print(item.layers[0].manager.update_definition({"fields":[scientific_field_dict]}))      
    print(item.layers[0].manager.update_definition({"fields":[common_field_dict]}))            
    return
    
    



if __name__ == '__main__':
    run()