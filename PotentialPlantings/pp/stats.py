import arcpy
import os

import pp.common as pp_c

import pp.logger
logger = pp.logger.get('pp_log')



def prepare_fc ():
    if not arcpy.Exists(pp_c.STATS_FC):       
        pp_c.log_debug ("Creating '%s'" % pp_c.STATS_FC)
        # Make a copy of the community feature class and reproject it
        communities_fc = arcpy.conversion.FeatureClassToFeatureClass(pp_c.MUNI_COMMUNITY_AREA, arcpy.env.scratchGDB, 'communities')[0]
        arcpy.management.Project(communities_fc, pp_c.STATS_FC, arcpy.Describe(pp_c.TREES_TEMPLATE_FC).spatialReference)
    
        # Add the stats fields
        for name, type_ in pp_c.COMMUNITY_STATS_SPEC + pp_c.DERIVED_STATS + pp_c.SPACE_STATS_SPEC + pp_c.TREE_STATS_SPEC:
            arcpy.AddField_management(pp_c.STATS_FC, name, type_)
         # Fill in the community_id field  
        arcpy.management.CalculateField(pp_c.STATS_FC, pp_c.STATS_COMMUNITY_COL, '!OBJECTID!')
        # Fill in the acres field  
        arcpy.management.CalculateField(pp_c.STATS_FC, 'acres', "!shape.area@acres!")
        # Map community id to name
        arcpy.management.AssignDomainToField(pp_c.STATS_FC, pp_c.STATS_COMMUNITY_COL, pp_c.COMMUNITY_DOMAIN_NAME)    
            
        pp_c.delete ([communities_fc])
    return


def prepare_community_stats_tbl (community, community_id, fc_type, stats_spec):
    stats_tbl = pp_c.get_community_fc_name (community, fc_type)
    if arcpy.Exists(stats_tbl):
        arcpy.Delete_management(stats_tbl)
    arcpy.CreateTable_management(os.path.dirname(stats_tbl), os.path.basename(stats_tbl))
    arcpy.AddField_management(stats_tbl, pp_c.STATS_COMMUNITY_COL, 'SHORT')
    for name, type_ in stats_spec:
        arcpy.AddField_management(stats_tbl, name, type_)
    with arcpy.da.InsertCursor(stats_tbl, [pp_c.STATS_COMMUNITY_COL] + [s[0] for s in stats_spec]) as cursor:
        cursor.insertRow([community_id] + [0]*len(stats_spec))
    return stats_tbl
    

def update_stats (tbl, community_id, stats, stats_spec):
    field_names = [f[0] for f in stats_spec]
    with arcpy.da.UpdateCursor(tbl, field_names, '%s = %i' % (pp_c.STATS_COMMUNITY_COL, community_id)) as cursor:
        for attr_vals in cursor:
            cursor.updateRow(stats)
    return


def update_derived_stats (community_id):
    field_names = ['acres', 'small', 'medium', 'large', 'percent_canopy', 'percent_buildings', 'percent_other', 'trees', 'trees_per_acre']
    with arcpy.da.UpdateCursor(pp_c.STATS_FC, field_names, '%s = %i' % (pp_c.STATS_COMMUNITY_COL, community_id)) as cursor:
        for acres, small, medium, large, percent_canopy, percent_buildings, percent_other, trees, trees_per_acre in cursor:
            trees = small + medium + large
            trees_per_acre = trees/acres   
            percent_other = 100.0 - percent_canopy - percent_buildings
            cursor.updateRow([acres, small, medium, large, percent_canopy, percent_buildings, percent_other, trees, trees_per_acre])
    return
