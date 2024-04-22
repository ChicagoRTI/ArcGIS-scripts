
import os
import arcpy
import datetime as dt


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

REVIEWS = 'https://services6.arcgis.com/WNXWcrlG6DXHeQ5W/arcgis/rest/services/service_26c7ea6a64b14374b5af866612037013/FeatureServer/0'
TREES = 'https://services6.arcgis.com/WNXWcrlG6DXHeQ5W/arcgis/rest/services/Trees/FeatureServer/0'
STORIES = 'https://services6.arcgis.com/WNXWcrlG6DXHeQ5W/arcgis/rest/services/Inventory_Stories/FeatureServer/0'


FCS = [TREES, STORIES]


def run():
    num_approved = 0
    
    most_recent_review_date = arcpy.da.SearchCursor(REVIEWS, ['review_date'], sql_clause=(None,'ORDER BY review_date DESC')).next()[0]
    
    for fc in FCS:
        with arcpy.da.UpdateCursor(fc, ['is_reviewed', 'created_date'], where_clause='is_reviewed<>1') as cursor:
            for is_reviewed, created_date in cursor:
                if created_date < most_recent_review_date:
                    num_approved += 1
                    cursor.updateRow([1, created_date])

    if num_approved > 0:
        print (f"{num_approved} records approved")
        
    return


if __name__ == '__main__':
    run()
