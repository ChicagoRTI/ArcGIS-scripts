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
        for name, type_ in pp_c.COMMUNITY_STATS_SPEC + pp_c.TREE_STATS_SPEC + pp_c.DERIVED_STATS:
            arcpy.AddField_management(pp_c.STATS_FC, name, type_)
         # Fill in the community_id field  
        arcpy.management.CalculateField(pp_c.STATS_FC, pp_c.STATS_COMMUNITY_COL, '!OBJECTID!')
        # Fill in the acres field  
        arcpy.management.CalculateField(pp_c.STATS_FC, 'acres', "!shape.area@acres!")
        # Join in the land cover information for each community
        arcpy.management.JoinField(pp_c.STATS_FC, pp_c.STATS_COMMUNITY_NAME_COL, pp_c.COMMUNITY_LAND_COVER_TBL, pp_c.LAND_COVER_COMMUNITY_NAME_COL, [s[0] for s in pp_c.LAND_COVER_STATS])
        arcpy.management.CalculateField(pp_c.STATS_FC, 'Canopy', '!Canopy!*100', "PYTHON3", "", "FLOAT")
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

        
    
def __read_community_stats (community, community_id, fc_type, stats_spec):
    community_stats_tbl = pp_c.get_community_fc_name (community, fc_type)
    if arcpy.Exists (community_stats_tbl):
        with arcpy.da.SearchCursor(community_stats_tbl, [s[0] for s in stats_spec]) as cursor:
            for attrs in cursor:
                return attrs
    return [0] * len(stats_spec)
    

def update_stats (tbl, community_id, stats, stats_spec):
    field_names = [f[0] for f in stats_spec]
    with arcpy.da.UpdateCursor(tbl, field_names, '%s = %i' % (pp_c.STATS_COMMUNITY_COL, community_id)) as cursor:
        for attr_vals in cursor:
            cursor.updateRow(stats)
    return


def combine_stats (community_specs):
    for community, acres, community_id in community_specs:
        pp_c.log_debug ('Updating final stats for %s' % community)
        
        # # Update space stats
        # space_stats = __read_community_stats (community, community_id, pp_c.COMMUNITY_SPACE_STATS_TBL, pp_c.SPACE_STATS_SPEC)
        # update_stats (pp_c.STATS_FC, community_id, space_stats, pp_c.SPACE_STATS_SPEC)

        # Update tree stats
        tree_stats = __read_community_stats (community, community_id, pp_c.COMMUNITY_TREE_STATS_TBL, pp_c.TREE_STATS_SPEC)
        update_stats (pp_c.STATS_FC, community_id, tree_stats, pp_c.TREE_STATS_SPEC)

        # Update derived stats
        field_names = ['acres', 'small', 'medium', 'large', 'Canopy', 'trees', 'trees_per_acre', 'canopy_y0', 'canopy_y5', 'canopy_y10', 'canopy_y15', 'canopy_y20', 'canopy_y25']
        with arcpy.da.UpdateCursor(pp_c.STATS_FC, field_names, '%s = %i' % (pp_c.STATS_COMMUNITY_COL, community_id)) as cursor:
            for acres, small, medium, large, percent_canopy,  trees, trees_per_acre, cy0, cy5, cy10, cy15, cy20, cy25 in cursor:
                existing_canopy_acres = acres * percent_canopy / 100.0
                trees = small + medium + large
                trees_per_acre = trees/acres   
                canopy_growth = compute_canopy_growth (acres, percent_canopy, small, medium, large)
                cursor.updateRow([acres, small, medium, large, percent_canopy, trees, trees_per_acre] + [(existing_canopy_acres + canopy_growth[i])/acres*100 for i in range(0,26,5)])
    return


def compute_canopy_growth (total_acres, percent_canopy, small, medium, large):
    growth_years = 26    
    growth_spec = {pp_c.SMALL: {'sited_trees': small, 'start_radius': 2 * 0.3048, 'cagr': None},
                 pp_c.MEDIUM: {'sited_trees': medium, 'start_radius': 3 * 0.3048, 'cagr': None},
                 pp_c.BIG: {'sited_trees': large, 'start_radius': 4 * 0.3048, 'cagr': None}}
           

    # Set the baseline (year 0) acres for each canopy size
    projected_growth = list()
    projected_growth.append(dict())
    for size in growth_spec.keys():
        projected_growth[0][size] = 0.000247105 *  (growth_spec[size]['sited_trees']  * (3.141592653589793 * (growth_spec[size]['start_radius'] **2))) 
        
    # Compute compound growth rate
    for size in growth_spec.keys():
        start_acres = projected_growth[0][size]
        target_acres = 0.000247105 *  (growth_spec[size]['sited_trees'] * (3.141592653589793 * (pp_c.TREE_RADIUS[size] **2)))
        growth_spec[size]['cagr'] = pow(target_acres/start_acres, 1/growth_years) - 1

    # Compute annual total acres
    annual_totals = [sum(projected_growth[0].values())]
    for i in range (1,growth_years):
        projected_growth.append(dict())
        for size in (pp_c.SMALL, pp_c.MEDIUM, pp_c.BIG):
            projected_growth[i][size] = projected_growth[i-1][size] + projected_growth[i-1][size] * growth_spec[size]['cagr']
        annual_totals.append (sum(projected_growth[i].values()))
    return annual_totals

# def combine_stats (community_specs):
#     for community, acres, community_id in community_specs:
#         pp_c.log_debug ('Updating final stats for %s' % community)
#         # Update space stats
#         space_stats = __read_community_stats (community, community_id, pp_c.COMMUNITY_SPACE_STATS_TBL, pp_c.SPACE_STATS_SPEC)
#         update_stats (pp_c.STATS_FC, community_id, space_stats, pp_c.SPACE_STATS_SPEC)

#         # Update tree stats
#         tree_stats = __read_community_stats (community, community_id, pp_c.COMMUNITY_TREE_STATS_TBL, pp_c.TREE_STATS_SPEC)
#         update_stats (pp_c.STATS_FC, community_id, tree_stats, pp_c.TREE_STATS_SPEC)

#         # Update derived stats
#         field_names = ['acres', 'small', 'medium', 'large', 'percent_canopy', 'percent_buildings', 'percent_other', 'trees', 'trees_per_acre', 'canopy_y0', 'canopy_y5', 'canopy_y10', 'canopy_y15', 'canopy_y20', 'canopy_y25']
#         with arcpy.da.UpdateCursor(pp_c.STATS_FC, field_names, '%s = %i' % (pp_c.STATS_COMMUNITY_COL, community_id)) as cursor:
#             for acres, small, medium, large, percent_canopy, percent_buildings, percent_other, trees, trees_per_acre, cy0, cy5, cy10, cy15, cy20, cy25 in cursor:
#                 trees = small + medium + large
#                 trees_per_acre = trees/acres   
#                 percent_other = 100.0 - percent_canopy - percent_buildings
#                 canopy_growth = compute_canopy_growth (acres, percent_canopy, small, medium, large)
#                 cursor.updateRow([acres, small, medium, large, percent_canopy, percent_buildings, percent_other, trees, trees_per_acre] + [canopy_growth[i] for i in range(0,26,5)])
#     return


# def compute_canopy_growth (total_acres, percent_canopy, small, medium, large):
#     growth_years = 26    
#     growth_spec = {pp_c.SMALL: {'sited_trees': small, 'start_radius': 2 * 0.3048, 'cagr': None},
#                  pp_c.MEDIUM: {'sited_trees': medium, 'start_radius': 3 * 0.3048, 'cagr': None},
#                  pp_c.BIG: {'sited_trees': large, 'start_radius': 4 * 0.3048, 'cagr': None}}
           

#     # Set the baseline (year 0) acres for each canopy size
#     projected_growth = list()
#     projected_growth.append(dict())
#     for size in growth_spec.keys():
#         projected_growth[0][size] = 0.000247105 *  (growth_spec[size]['sited_trees']  * (3.141592653589793 * (growth_spec[size]['start_radius'] **2))) 
        
#     # Compute compound growth rate
#     for size in growth_spec.keys():
#         start_acres = projected_growth[0][size]
#         target_acres = 0.000247105 *  (growth_spec[size]['sited_trees'] * (3.141592653589793 * (pp_c.TREE_RADIUS[size] **2)))
#         growth_spec[size]['cagr'] = pow(target_acres/start_acres, 1/growth_years) - 1

#     # Compute annual total acres
#     existing_canopy_acres = total_acres * percent_canopy / 100.0
#     annual_totals = [existing_canopy_acres + sum(projected_growth[0].values())]
#     for i in range (1,growth_years):
#         projected_growth.append(dict())
#         for size in (pp_c.SMALL, pp_c.MEDIUM, pp_c.BIG):
#             projected_growth[i][size] = projected_growth[i-1][size] + projected_growth[i-1][size] * growth_spec[size]['cagr']
#         annual_totals.append (existing_canopy_acres + sum(projected_growth[i].values()))
#     return annual_totals
    
