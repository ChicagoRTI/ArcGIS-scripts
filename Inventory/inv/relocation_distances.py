import arcpy
from lxml import etree

# Find the distances of point relocations

STORIES_ITEM_URL = 'https://services6.arcgis.com/WNXWcrlG6DXHeQ5W/arcgis/rest/services/Inventory_Stories/FeatureServer/0'
SR_DEGREES = arcpy.SpatialReference('WGS 1984')
SR_METERS = arcpy.SpatialReference(4326)



def run ():
    
    delete_oids = []
    
    with arcpy.da.UpdateCursor(STORIES_ITEM_URL, ['objectid', 'story', 'tree_id']) as cursor:
        for oid, story_html, tree_id in cursor:
            table_rows = __parse_story_html (story_html)
            
            if 'longitude' in table_rows.keys() and 'latitude' in table_rows.keys() and 'relocated' in table_rows.keys() and len(table_rows)==3:
                # print (f'{oid}')
                cursor.deleteRow()
                
                
                # old_xy = (table_rows['longitude'][0], table_rows['latitude'][0] )
                # new_xy = (table_rows['longitude'][1], table_rows['latitude'][1] )
                # old_point = arcpy.PointGeometry(arcpy.Point(old_xy[0], old_xy[1]), SR_DEGREES).projectAs(SR_METERS)
                # new_point = arcpy.PointGeometry(arcpy.Point(new_xy[0], new_xy[1]), SR_DEGREES).projectAs(SR_METERS)
                # # print (f'{oid} {old_point} {new_point} {old_point.distanceTo(new_point) * 364,567.2}')
                # # distance = old_point.distanceTo(new_point) * 364567.2
                # distance = old_point.distanceTo(new_point)
                # print (f'{oid} {len(table_rows)} {distance} meters')


        return
    
# Return a list of dicts, one item for each row.  <field: (old_value, new_value)>
def __parse_story_html (story_html):
    ret_dict = dict()
    if story_html is not None and '<table' in story_html:
        table = etree.HTML(story_html).find("body/table")
        rows = iter(table)
        next(rows)
        # headers = [col.text for col in next(rows)]
        for row in rows:
            values = [col.text for col in row]
            ret_dict[values[0].lower()] =  (values[1] if len(values)>1 else None, values[2] if len(values)>2 else None)
    return ret_dict
    
    
    # # user = input('Portal user ID: ').strip() or "DMorrison@mortonarb.org"
    # url = 'https://gis.mortonarb.org/portal/home/'
    # # pw = getpass.getpass(prompt='Portal Password: ')
    # # gis = GIS(url=url, username=user, password=pw)
    # gis = GIS(url=url)
    # item = gis.content.get(TREES_ITEM_ID)
        
    # scientific_field_dict = {
    #     'name': 'latin_name',
    #     'domain': {
    #         'type': 'codedValue',
    #         'name': 'latin_name',
    #         'codedValues': []
    #     }
    # }
    
    # common_field_dict = {
    #     'name': 'common_name',
    #     'domain': {
    #         'type': 'codedValue',
    #         'name': 'common_name',
    #         'codedValues': []
    #     }
    # }
    
    # with arcpy.da.SearchCursor(SPECIES_LIST_CLEAN, ['common_name', 'scientific_name']) as cursor:
    #     for common_name, latin_name in cursor:
    #         scientific_field_dict['domain']['codedValues'].append({'name': f'{latin_name} ({common_name})', 'code': latin_name})
    #         common_field_dict['domain']['codedValues'].append({'name': f'{common_name} ({latin_name})', 'code': common_name})

    #         print(item.layers[0].manager.update_definition({"fields":[scientific_field_dict]}))      
    #         print(item.layers[0].manager.update_definition({"fields":[common_field_dict]}))   
    #         return
    # return
    
    



if __name__ == '__main__':
    run()