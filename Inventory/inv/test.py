import os
import arcpy
import datetime as dt

INTERNAL_SURVEY_URL = 'https://gis.mortonarb.org/server/rest/services/Hosted/service_d8b3fda9400f4053aa5c90c400d6c07d/FeatureServer/0'
CANOPY_COUNT_TREES_URL = 'https://services6.arcgis.com/WNXWcrlG6DXHeQ5W/arcgis/rest/services/Trees/FeatureServer/0'

def run():
    print (f"{dt.datetime.now():%c}: Started")  
    
    oid_to_last_edited = dict()
    with arcpy.da.SearchCursor(INTERNAL_SURVEY_URL, ['objectid', 'last_edited_date']) as cursor:
        for oid, last_edited_date in cursor:
            oid_to_last_edited[oid] = last_edited_date
    
    with arcpy.da.UpdateCursor(CANOPY_COUNT_TREES_URL, ['tree_id', 'int_srvy_last_edited_date', 'int_srvy_oid']) as cursor:
        for tree_id, int_srvy_last_edited_date, int_srvy_oid in cursor:
            rec_type = tree_id[0]
            if rec_type == 'I' and int_srvy_last_edited_date is None:
                rec_oid = int(tree_id[2:])
                print (f"oid: {rec_oid}  date: {oid_to_last_edited[rec_oid]}")
                cursor.updateRow([tree_id, oid_to_last_edited[rec_oid], rec_oid])
    # inv.approve_records.run()
    # inv.merge_records.run()
    
    print (f"{dt.datetime.now():%c}: Finished")
    return




if __name__ == '__main__':
    run()

