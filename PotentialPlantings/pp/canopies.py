
import arcpy
import os

import pp.stats
import pp.common as pp_c


import pp.logger
logger = pp.logger.get('pp_log')


def create_canopies (community_spec):
    try:
        
        # Process the input community
        community_name, acres, community_id = community_spec
        pp_c.log_info('Generating canopies', community_name)
        
        input_fc = pp_c.get_community_fc_name (community_name, pp_c.COMMUNITY_TREES_FC)
        output_fc = pp_c.get_community_fc_name (community_name, pp_c.COMMUNITY_CANOPIES_FC)
        
        intermediate_output_gdb =  pp_c.prepare_intermediate_output_gdb (pp_c.USE_IN_MEM)
        trees_buffered = pp_c.get_intermediate_name (intermediate_output_gdb, 'tbuffered_int', community_id, pp_c.USE_IN_MEM)
    
        pp_c.log_debug ('Populate the "radius" field', community_name)   
        arcpy.management.CalculateField(input_fc, 'radius', "get_radius(!code!)", "PYTHON3", r"""def get_radius (code):
            if code == 0:
                return %1.2f
            elif code == 1:
                return %1.2f
            else:
                return %1.2f""" % (pp_c.TREE_RADIUS[pp_c.SMALL], pp_c.TREE_RADIUS[pp_c.MEDIUM], pp_c.TREE_RADIUS[pp_c.BIG]), "FLOAT")  
 
        pp_c.log_debug ('Buffer the points', community_name)   
        arcpy.analysis.Buffer(input_fc, trees_buffered, "radius", "FULL", "ROUND", "NONE", None, "PLANAR")

        arcpy.management.DeleteField(input_fc, 'radius') 
        
        pp_c.log_debug ('Writing community canopies', community_name)   
        sr = arcpy.Describe(pp_c.CANOPIES_TEMPLATE_FC).spatialReference
        arcpy.CreateFeatureclass_management(os.path.dirname(output_fc), os.path.basename(output_fc), 'POLYGON', pp_c.CANOPIES_TEMPLATE_FC, "DISABLED", "DISABLED", sr)        
        arcpy.management.Append(trees_buffered, output_fc, "NO_TEST")

        pp_c.delete( [trees_buffered] )        
           
    except Exception as ex:
      pp_c.log_debug ('Exception: %s' % (str(ex)))
      raise ex

def prepare_fc ():
    if not arcpy.Exists(pp_c.CANOPIES_FC):
        pp_c.log_debug ("Creating '%s'" % pp_c.CANOPIES_FC)
        sr = arcpy.Describe(pp_c.CANOPIES_TEMPLATE_FC).spatialReference
        arcpy.CreateFeatureclass_management(os.path.dirname(pp_c.CANOPIES_FC), os.path.basename(pp_c.CANOPIES_FC), 'POLYGON', pp_c.CANOPIES_TEMPLATE_FC, "DISABLED", "DISABLED", sr)
        arcpy.management.AssignDomainToField(pp_c.CANOPIES_FC, pp_c.CANOPIES_LANDUSE_COL, pp_c.LANDUSE_DOMAIN_NAME)
        arcpy.management.AssignDomainToField(pp_c.CANOPIES_FC, pp_c.CANOPIES_PUBLIC_PRIVATE_COL, pp_c.PUBLIC_PRIVATE_DOMAIN_NAME)
        arcpy.management.AssignDomainToField(pp_c.CANOPIES_FC, pp_c.CANOPIES_COMMUNITY_COL, pp_c.COMMUNITY_DOMAIN_NAME)    
        arcpy.management.AssignDomainToField(pp_c.CANOPIES_FC, pp_c.CANOPIES_SIZE_COL, pp_c.TREE_SIZE_DOMAIN_NAME) 
        
        

def combine_canopies_fcs (community_specs):
    pp_c.log_debug ('Combining canopies feature classes')
    
    community_specs = [c for c in community_specs if arcpy.Exists(pp_c.get_community_fc_name(c[0], pp_c.COMMUNITY_CANOPIES_FC))]
    
    communities  = [c[0] for c in community_specs]
    community_fcs = [pp_c.get_community_fc_name (c, pp_c.COMMUNITY_CANOPIES_FC) for c in communities]
    community_ids = [str(c[2]) for c in community_specs]
    
    out_fc = pp_c.CANOPIES_FC   
        
    if not pp_c.IS_SCRATCH_OUTPUT_DATA:
        pp_c.log_debug ('Deleting existing features in combined canopies feature class')
        where = "%s IN (%s)" % (pp_c.CANOPIES_COMMUNITY_COL, ','.join(community_ids))
        old_records = arcpy.SelectLayerByAttribute_management(out_fc, 'NEW_SELECTION', where)[0]
        arcpy.management.DeleteFeatures(old_records)

    if len(communities) > 10:
        pp_c.remove_indexes (out_fc, pp_c.CANOPIES_INDEX_SPEC)        
        
    pp_c.log_info ('Write to combined canopies feature class')
    arcpy.management.Append(community_fcs, out_fc)
    
    if len(communities) > 10:
        pp_c.add_indexes (out_fc, pp_c.CANOPIES_INDEX_SPEC) 
   
    return
