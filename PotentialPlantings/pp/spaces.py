import arcpy
import os

import pp.stats
import pp.common as pp_c

import pp.logger
logger = pp.logger.get('pp_log')


PROBLEM_COMMUNITIES = ['Joliet', 'Chicago Twshp']

      
def find_spaces (community_spec):
    try:
        
        # Process the input community
        community, acres, idx = community_spec
        pp_c.log_info('Finding spaces. %i acres' % (acres), community)
        
        use_in_mem = pp_c.USE_IN_MEM if community not in PROBLEM_COMMUNITIES else False
        
        intermediate_output_gdb =  pp_c.prepare_intermediate_output_gdb (use_in_mem)
    
        # canopy_clipped = pp_c.get_intermediate_name (intermediate_output_gdb, 'canopy_clipped', idx, use_in_mem)
        # plantable_region_clipped = pp_c.get_intermediate_name (intermediate_output_gdb, 'plantable_region_clipped', idx, use_in_mem)
        # buildings_clipped = pp_c.get_intermediate_name (intermediate_output_gdb, 'buildings_clipped', idx, use_in_mem)
        # minus_trees = pp_c.get_intermediate_name (intermediate_output_gdb, 'minus_trees', idx, use_in_mem)
        # minus_trees_buildings = pp_c.get_intermediate_name (intermediate_output_gdb, 'minus_trees_buildings', idx, use_in_mem)
        # plantable_poly = pp_c.get_intermediate_name (intermediate_output_gdb, 'plantable_poly', idx, use_in_mem)
        plantable_single_poly = pp_c.get_intermediate_name (intermediate_output_gdb, 'plantable_single_poly', idx, use_in_mem)
        plantable_muni = pp_c.get_intermediate_name (intermediate_output_gdb, 'plantable_muni', idx, use_in_mem)
        
        community_fc = pp_c.get_community_fc_name (community, pp_c.COMMUNITY_SPACES_FC)
        pp_c.delete ([community_fc])
                   
        pp_c.log_debug ('Getting community boundary', community)
        community_boundary = arcpy.SelectLayerByAttribute_management(pp_c.MUNI_COMMUNITY_AREA, 'NEW_SELECTION', "COMMUNITY = '%s'" % (community))[0]
    
        pp_c.log_debug ('Clipping %s' %(os.path.basename(pp_c.ALL_SPACES_FC)), community)
        arcpy.analysis.PairwiseClip(pp_c.ALL_SPACES_FC, community_boundary, plantable_single_poly, None)
    
        pp_c.log_debug ('Spatial join', community)        
        arcpy.SpatialJoin_analysis(plantable_single_poly, pp_c.MUNI_COMMUNITY_AREA, plantable_muni, "JOIN_ONE_TO_ONE", "KEEP_ALL", "", "INTERSECT", "", "")
        pp_c.delete( [plantable_single_poly] )
            
        pp_c.log_debug ('Add and populate the "CommunityID" field', community)   
        arcpy.management.CalculateField(plantable_muni, pp_c.SPACES_COMMUNITY_COL, '%i' % (idx), "PYTHON3", "", "SHORT")
        
        __save_community_spaces (plantable_muni, community_fc)
        pp_c.delete( [plantable_muni] )        

            
    except Exception as ex:
      pp_c.log_debug ('Exception: %s' % (str(ex)))
      raise ex
        
    return community_fc


def __trim_excess_fields (fc, keep_fields):
    all_fields = set([f.name.lower() for f in arcpy.ListFields(fc)])
    keep_fields = set([k.lower() for k in keep_fields])
    arcpy.DeleteField_management(fc, ';'.join(all_fields - keep_fields))
    return


def __save_community_spaces (in_fc, out_fc):
    sr = arcpy.Describe(pp_c.SPACES_TEMPLATE_FC).spatialReference
    arcpy.CreateFeatureclass_management(os.path.dirname(out_fc), os.path.basename(out_fc), 'POLYGON', pp_c.SPACES_TEMPLATE_FC, "DISABLED", "DISABLED", sr)        
#    arcpy.management.AlterField(in_fc, 'LandUse', 'land_use')
    arcpy.management.Append(in_fc, out_fc, "NO_TEST")
    return


def prepare_fc ():
    if not arcpy.Exists(pp_c.SPACES_FC):       
        pp_c.log_debug ("Creating '%s'" % pp_c.SPACES_FC)
        sr = arcpy.Describe(pp_c.SPACES_TEMPLATE_FC).spatialReference
        arcpy.CreateFeatureclass_management(os.path.dirname(pp_c.SPACES_FC), os.path.basename(pp_c.SPACES_FC), 'POLYGON', pp_c.SPACES_TEMPLATE_FC, "DISABLED", "DISABLED", sr)        
        arcpy.management.AssignDomainToField(pp_c.SPACES_FC, pp_c.SPACES_COMMUNITY_COL, pp_c.COMMUNITY_DOMAIN_NAME)         
    return   


def combine_spaces_fcs (community_specs):
    pp_c.log_debug ('Combining spaces feature classes')
    communities  = [c[0] for c in community_specs]
    community_fcs = [pp_c.get_community_fc_name (c, pp_c.COMMUNITY_SPACES_FC) for c in communities]
    community_ids = [str(c[2]) for c in community_specs]
    
    out_fc = pp_c.SPACES_FC   
                        
    if not pp_c.IS_SCRATCH_OUTPUT_DATA:        
        pp_c.log_debug ('Deleting existing features in combined spaces feature class')
        where = "%s IN (%s)" % (pp_c.SPACES_COMMUNITY_COL, ','.join(community_ids))
        old_records = arcpy.SelectLayerByAttribute_management(out_fc, 'NEW_SELECTION', where)[0]
        arcpy.management.DeleteFeatures(old_records)

    if len(communities) > 10:
        pp_c.remove_indexes (out_fc, pp_c.SPACES_INDEX_SPEC)
 
    pp_c.log_info ('Write to combined spaces feature class')
    arcpy.management.Append(community_fcs, out_fc)
    
    if len(communities) > 10:
        pp_c.add_indexes (out_fc, pp_c.SPACES_INDEX_SPEC)    
   
    return







    




