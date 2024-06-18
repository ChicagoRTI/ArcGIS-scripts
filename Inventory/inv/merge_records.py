
import os
import arcpy
import json
import urllib
import urllib.request 
from urllib.parse import urlencode
import datetime as dt


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

SPECIES_LIST_CLEAN = 'https://services6.arcgis.com/WNXWcrlG6DXHeQ5W/arcgis/rest/services/Species_List/FeatureServer/0'
TASK_MONITOR = 'https://services6.arcgis.com/WNXWcrlG6DXHeQ5W/arcgis/rest/services/Task_Monitor/FeatureServer/0'

SR = srs = arcpy.SpatialReference(4326)  # WGS 1984

MAX_PHOTOS = 2

IGNORE_IS_COPIED = False   # True if doing a complete refresh

INPUTS = [ 
            {
                'name': 'Internal',
                'location': 'https://gis.mortonarb.org/server/rest/services/Hosted/service_d8b3fda9400f4053aa5c90c400d6c07d/FeatureServer/0',
                'field_names': ['shape@', 'objectid', 'tree_dbh', 'multistem', 'common_name', 'latin_name', 'date_', 'latin_common', 'created_user', 'notes', 'tree_dbh', 'cultivar', 'is_copied', 'last_edited_date'],
                'oid_field': 'objectid',
                'id_prefix': 'I',
            },
            # {
            #     'name': 'External - OBSOLETE',
            #     'location': 'https://gis.mortonarb.org/server/rest/services/Hosted/service_b97f296ee4444209b2904f56df3cab1a/FeatureServer/0',
            #     'field_names': ['shape@', 'objectid', 'tree_dbh', 'multistem', 'common_name', 'latin_name', 'date_', 'latin_common', 'created_user', 'notes', 'tree_dbh', 'cultivar', 'is_copied', 'multistem', 'new_existing', 'certainty'],
            #     'oid_field': 'objectid',    
            #     'id_prefix': 'E',
            # },         
            # {
            #     'name': 'Old_Data',
            #     'location': os.path.join(BASE_DIR, r'data\Old_Data\OldData_DeleteIdentical.shp'),
            #     'field_names': ['shape@', 'FID', 'CommonName', 'Latin', 'Cultivar', 'dbh', 'Date', 'Condition'],
            #     'oid_field': 'FID',  
            #     'id_prefix': 'O',
            # },         
        ]

OUTPUT_ITEM_URL = 'https://services6.arcgis.com/WNXWcrlG6DXHeQ5W/arcgis/rest/services/Trees/FeatureServer/0' # AGOL
STORIES_ITEM_URL = 'https://services6.arcgis.com/WNXWcrlG6DXHeQ5W/arcgis/rest/services/Inventory_Stories/FeatureServer/0'

OUTPUT_STRING_MAX_LENS = {f.name: f.length for f in arcpy.ListFields(OUTPUT_ITEM_URL) if f.type=='String'}

def run():
    # Map common names to scientific name and vice versa
    common_to_scientific_name = dict()
    scientific_to_common_name = dict()
    with arcpy.da.SearchCursor(SPECIES_LIST_CLEAN, ['common_name', 'scientific_name', 'combined']) as cursor:
        for common_name, scientific_name, combined in cursor:
            common_to_scientific_name[common_name] = scientific_name
            scientific_to_common_name[scientific_name] = common_name
                
    # Process the new records    
    for input_ in INPUTS:
        output = list()

        with arcpy.da.SearchCursor(input_['location'], input_['field_names'], __get_where_clause(input_), spatial_reference=SR) as input_cursor:
            for row in input_cursor:   
                if input_['name'] == "Internal":
                    output.append(__convert_internal_survey (input_, row, scientific_to_common_name, common_to_scientific_name, IGNORE_IS_COPIED))
                elif input_['name'] == "Old_Data":
                    output.append(__convert_old_data_survey (input_, row))
                else:
                    raise Exception ("{dt.datetime.now():%c}: Unrecognized data name")
                    
        if len(output) > 0:
            print (f"{dt.datetime.now():%c}: Writing {len(output)} {input_['name']} records")
            with arcpy.da.InsertCursor(OUTPUT_ITEM_URL, list(output[0]['output_record'].keys())) as output_cursor:
                for o in output:                              
                    output_cursor.insertRow(list(__truncate_strings (o['output_record']).values()))
                    __write_is_copied (input_, o['input_oid'])

    # Process changed internal survey records
    input_ = [i for i in INPUTS if i['name'] == 'Internal'][0]
    # Were there any changes to the internal survey in the past hour?
    most_recent = max([r[0] for r in arcpy.da.SearchCursor(input_['location'], ['last_edited_date'])])
    if (most_recent > dt.datetime.utcnow() - dt.timedelta(hours=1)):
        # Read in all of the internal survey records and convert them to the merged format
        internal_survey_records = dict()
        with arcpy.da.SearchCursor(input_['location'], [input_['field_names']]) as cursor:
            for row in cursor:   
                cvt = __convert_internal_survey (input_, row, scientific_to_common_name, common_to_scientific_name, False)
                internal_survey_records[cvt['input_oid']] = cvt['output_record']
        # Fields to sync when they change:
        change_sync_fields = [  'shape@',
                                'common_name',
                                'scientific_name',
                                'cultivar',
                                'dbh', 
                                'notes',
                                'submitter_name',
                                'multi_stem',
                                'new_or_existing',
                                'certainty',
                                'latitude',
                                'longitude',
                                ]
        
        # Check each merged record so see if the associated internal survey record has been updated
        with arcpy.da.UpdateCursor(OUTPUT_ITEM_URL, change_sync_fields + ['tree_id', 'int_srvy_last_edited_date', 'int_srvy_oid'], "tree_id LIKE 'I_%'") as update_cursor:
            for row in update_cursor:  
                changes = list()
                merged_record = dict(zip(change_sync_fields + ['tree_id', 'int_srvy_last_edited_date', 'int_srvy_oid'], row)) 
                if merged_record['int_srvy_last_edited_date'] < internal_survey_records[merged_record['int_srvy_oid']]['int_srvy_last_edited_date']:
                    print (f"Edited internal oid: {merged_record['int_srvy_oid']}") 
                    for f in change_sync_fields:
                        before = merged_record[f] 
                        after = internal_survey_records[merged_record['int_srvy_oid']][f]
                        if after is None:
                            merged_record[f] = before
                        else:
                            if before != after:
                                print (f"Field: {f} Before: {before} After: {after}")
                                changes.append( (f, before, after) )
                            merged_record[f] = after
                    merged_record['int_srvy_last_edited_date'] = internal_survey_records[merged_record['int_srvy_oid']]['int_srvy_last_edited_date']
                    update_cursor.updateRow(list(merged_record.values()))

                if len(changes) > 0:
                    __create_internal_change_story (changes, merged_record['tree_id'])
                                                                                      

    __update_task_monitor ()
    return

def __convert_internal_survey (input_, row, scientific_to_common_name, common_to_scientific_name, is_reviewed):
    input_record = dict(zip(input_['field_names'], row))   
    photos = __get_photos (input_record, input_['location'])
    return {
            'input_oid': input_record['objectid'], 
            'output_record': { 
                'shape@':           input_record['shape@'],
                'common_name':      __get_common_name (input_record, scientific_to_common_name),
                'scientific_name':  __get_scientific_name (input_record, common_to_scientific_name),
                'cultivar':         input_record['cultivar'] if input_record['cultivar'] is not None and len(input_record['cultivar']) > 0 else None,
                'dbh':              input_record['tree_dbh'],
                'date_observed':    input_record['date_'],
                'notes':            input_record['notes'] if input_record['notes'] is not None and len(input_record['notes']) > 0 else None,
                'submitter_name':   input_record['created_user'] if input_record['created_user'] is not None and len(input_record['created_user']) > 0 else "CRTI",
                'photo_1':          photos[0] if len(photos)==1 else None,                   
                'photo_2':          photos[1] if len(photos)==2 else None,
                "tree_id":          f"{input_['id_prefix']}_{input_record['objectid']:08}",             
                'multi_stem':       input_record['multistem'].capitalize() if ('multistem' in input_['field_names'] and input_record['multistem'] is not None) else None,
                'new_or_existing':  input_record['new_existing'] if 'new_existing' in input_['field_names'] else None,
                'certainty':        input_record['certainty'] if 'certainty' in input_['field_names'] else None,
                'longitude':        input_record['shape@'].centroid.X,
                'latitude':         input_record['shape@'].centroid.Y,
                'is_reviewed':      is_reviewed,
                'int_srvy_last_edited_date': input_record['last_edited_date'],
                'int_srvy_oid':     input_record['objectid'],
                }} 

def __convert_old_data_survey (input_, row):
    input_record = dict(zip(input_['field_names'], row))   
    return {
            'input_oid': input_record['FID'], 
            'output_record': { 
                'shape@':           input_record['shape@'],
                'common_name':      input_record['CommonName'],
                'scientific_name':  input_record['Latin'],
                'cultivar':         input_record['Cultivar'].strip(),
                'dbh':              input_record['dbh']  if input_record['dbh'] != 0  else None,
                'date_observed':    input_record['Date']  if input_record['Date'] != 0  else None,
                'notes':            None,
                'submitter_name':   None,
                'photo_1':          None,                   
                'photo_2':          None,
                "tree_id":          f"{input_['id_prefix']}_{input_record['FID']:08}",             
                'multi_stem':       None,
                'new_or_existing':  None,
                'certainty':        None,
                'longitude':        input_record['shape@'].centroid.X,
                'latitude':         input_record['shape@'].centroid.Y,
                'is_reviewed':       True,
                }}


def __create_internal_change_story (changes,tree_id):   
    with arcpy.da.InsertCursor(STORIES_ITEM_URL, ['title', 'story', 'submitter', 'tree_id', 'is_reviewed']) as output_cursor:
        html = '<table style="margin: 0px auto;"><tr><th>Field</th><th>Old Value</th><th>New Value</th></tr>'
        for change in changes:
            html = html + f'<tr><td>{change[0]}</td><td>{change[1]}</td><td>{change[2]}</td></tr>'
        html = html +'</table>'                            
        output_cursor.insertRow(['Inspection/Update', html, 'CRTI', tree_id, True])
    return
    

def __update_task_monitor ():
    with arcpy.da.UpdateCursor(TASK_MONITOR, ['last_run']) as cursor:
        for last_run in cursor:
            cursor.updateRow([dt.datetime.utcnow()])
            break
    return
    

def __write_is_copied (input_, input_oid_value):
    if input_['name'] == "Internal":
        with arcpy.da.UpdateCursor(input_['location'], [input_['oid_field'], 'is_copied']) as cursor:
            for oid, is_copied in cursor:
                if oid == input_oid_value:
                    cursor.updateRow([oid, 1])
                    break
    return


def __get_where_clause (input_spec):
    if IGNORE_IS_COPIED or input_spec['name'] != "Internal":
        return None
    else:        
        return 'is_copied IS NULL or is_copied <> 1' 


def __truncate_strings (output_record):
    for k in [k for k in OUTPUT_STRING_MAX_LENS.keys() if k in output_record.keys() and output_record[k] is not None]:
        output_record[k] = output_record[k][0:OUTPUT_STRING_MAX_LENS[k]] 
    return output_record
    

def __get_common_name (input_record, scientific_to_common_name):
    if input_record['latin_common'] == 'common':
        return input_record['common_name']
    if input_record['latin_common'] == 'latin':
        try:
            return scientific_to_common_name[input_record['latin_name']]
        except:
            pass
    return None
    

def __get_scientific_name (input_record, common_to_scientific_name):
    if input_record['latin_common'] == 'latin':
        return input_record['latin_name']
    if input_record['latin_common'] == 'common':
        try:
            return common_to_scientific_name[input_record['common_name']]
        except:
            pass
    return None    
    

def __get_photos (input_record, url):
    photos = list()
    url = f"{url}/{input_record['objectid']}/attachments"
    req = urllib.request.Request(url, urlencode({'f': 'json'}))
    req.data = req.data.encode('utf-8')
    response = urllib.request.urlopen(req) 
    data = json.load(response) 
    for i in range (0, MAX_PHOTOS-1):
        try:
            photos.append(url + '/' + str(data['attachmentInfos'][i]['attachmentid']))
        except:
            pass
    return photos


if __name__ == '__main__':
    run()
