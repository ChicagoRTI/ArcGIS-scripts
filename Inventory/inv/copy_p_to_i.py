import arcpy
from arcgis.gis import GIS
from arcgis.features import FeatureLayer
from datetime import datetime

# Copy "old" survey records to internal survey feature class. This should only need to be run once

START_OID = 99999999

INTERNAL_SURVEY_URL = 'https://gis.mortonarb.org/server/rest/services/Hosted/service_d8b3fda9400f4053aa5c90c400d6c07d/FeatureServer/0'
OLD_DATA_URL = 'https://gis.mortonarb.org/server/rest/services/Hosted/survey123_06e7000db25046e89596e25ffde74ef8/FeatureServer/0'


OLD_FIELDS = ['shape@', 'objectid', 'tree_species', 'tree_dbh', '_date', 'notes', 'field_9', 'cultivar', 'percent_branch_dieback_or_missi', 'overall_condition']
INTERNAL_FIELDS = ['shape@', 'latin_common', 'latin_name', 'common_name', 'cultivar', 'tree_dbh', 'date_', 'notes', 'percent_dieback_missingcrown', 'overall_condition', 'is_copied', 'id']


def run():
    
    url = 'https://gis.mortonarb.org/portal/home/'
    gis = GIS(url=url)
    
    old_data_fl =  FeatureLayer(OLD_DATA_URL, gis)
    old_data_attachment_mgr = old_data_fl.attachments
    
    new_data_fl =  FeatureLayer(INTERNAL_SURVEY_URL, gis)
    new_data_attachment_mgr = new_data_fl.attachments

    print ("Retrieving old data")
    old_data_features = old_data_fl.query(where="1=1").features
    
    
    with arcpy.da.InsertCursor(INTERNAL_SURVEY_URL, INTERNAL_FIELDS) as insert_cursor:
        for old_data_feature in old_data_features:
            o_attributes = old_data_feature.attributes
            o_oid = o_attributes['objectid']
            
            if o_oid >= START_OID:
                print (f"Processing old record {o_oid}")
                
                ### NEED TO COPY SHAPE
                o_geo = old_data_feature.geometry
                o_pt = arcpy.PointGeometry(arcpy.Point(o_geo['x'], o_geo['y']), spatial_reference=arcpy.SpatialReference(o_geo['spatialReference']['latestWkid']))
                
                new_data = [    o_pt,
                                "common" if o_attributes['tree_species'] is None else 'latin',
                                o_attributes['tree_species'],
                                o_attributes['field_9'],
                                o_attributes['cultivar'],
                                o_attributes['tree_dbh'],
                                datetime.fromtimestamp(o_attributes['_date']/1000),
                                o_attributes['notes'],
                                o_attributes['percent_branch_dieback_or_missi'],
                                o_attributes['overall_condition'],
                                True,
                                'P'
                                      ]
                
                n_oid = insert_cursor.insertRow (new_data)
                print (f"Inserted new record {n_oid}")
                
                for attachment in  old_data_attachment_mgr.get_list(o_oid):
                    print (f"Downloading attachment {attachment['id']}")
                    fn = old_data_attachment_mgr.download(oid=o_oid, attachment_id=attachment['id'])
                    
                    print ("Uploading attachment")
                    rc = new_data_attachment_mgr.add(n_oid, fn[0]) 
                    print (rc['addAttachmentResult'])
    return
    

#### CODE TO FIX DOMAIN MISMATCH
# def run(x):
#     if survey_level == 0:
#         return x
#     if x.startswith('Good'):
#         return 'Good: <10% dieback, missing crown, visible structural damage, and injury from diseases and pests'
#     elif x.startswith('Excellent'):
#         return 'Excellent: no missing crown, dieback, visible damage, or disease and pest presence'
#     elif x.startswith('Fair'):
#         return 'Fair: 10%–25%  dieback, missing crown, visible structural damage, and injury from diseases and pests'
#     elif x.startswith('Poor'):
#         return 'Poor: 25%-50%  dieback, missing crown, visible structural damage, and injury from diseases and pests'
#     elif x.startswith('Critical'):
#         return 'Critical: 50%-75%  dieback, missing crown, visible structural damage, and injury from diseases and pests'
#     elif x.startswith('Dying/Dead'):
#         return 'Dying/Dead: >75%  dieback, missing crown, visible structural damage, and injury from diseases and pests'
#     else:
#         return x

# def run(x,y):
#     if y == 0:
#         return x
#     if 'excellent' in x:
#         return '<1% (excellent)'
#     elif 'good' in x:
#         return '1-10% (good)'
#     elif 'fair' in x:
#         return '11-25% (fair)'
#     elif 'poor' in x:
#         return '26-50% (poor)'
#     elif 'critical' in x:
#         return '51-75% (critical)'
#     elif 'dying' in x:
#         return '76-99% (dying)'
#     elif 'dead' in x:
#         return '100% (dead)'
#     else:
#         return x
    

    return




if __name__ == '__main__':

    run()

