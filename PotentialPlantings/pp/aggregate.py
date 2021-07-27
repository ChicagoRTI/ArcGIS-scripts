import os
import arcpy

import pp.logger
logger = pp.logger.get('pp_log')

DB_DIR = r'C:\Users\dmorrison\AppData\Roaming\ESRI\Desktop10.6\ArcCatalog\ROW Habitat (SDE).SDE'


COMMUNITY_VIEW = os.path.join(DB_DIR, 'PP_TEST_v_aggregate_communities')


OUT_FC = os.path.join(DB_DIR, 'PP_TEST_aggregate_communities')
OUT_FC_TEMPLATE = os.path.join(DB_DIR, 'PP_TEST_aggregate_communities_TEMPLATE')


def run():
    
    if arcpy.Exists(OUT_FC):
        arcpy.Delete_management(OUT_FC)
    arcpy.CreateFeatureclass_management(os.path.dirname(OUT_FC),
                                        os.path.basename(OUT_FC),
                                        "POLYGON",
                                        OUT_FC_TEMPLATE,
                                        "DISABLED", 
                                        "DISABLED", 
                                        OUT_FC_TEMPLATE)


    communities = list()
    with arcpy.da.SearchCursor(COMMUNITY_VIEW, ['SHAPE@', 'community', 'trees']) as cursor:
        for attrs in cursor:
            communities.append(attrs)
    
 
    with arcpy.da.InsertCursor(OUT_FC, ['SHAPE@', 'community', 'trees_per_acre']) as cursor:
        for shape, community, trees in communities:
            if trees > 0:
                trees_per_acre = trees / shape.getArea('PLANAR', 'ACRES')
            else:
                trees_per_acre = 0
            cursor.insertRow([shape, community, trees_per_acre])
    
    pass

if __name__ == '__main__':
    run()
