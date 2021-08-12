import arcpy
import os
import multiprocessing
import shutil

import pp.common as pp_c

import pp.locate_trees
import pp.spaces

import pp.logger


def run():
    pp_c.log_info ("Logging to %s" % pp.logger.LOG_FILE)
    
    arcpy.env.overwriteOutput = True
    
    if os.path.isdir(pp_c.INTERMEDIATE_OUTPUT_DIR):
        shutil.rmtree(pp_c.INTERMEDIATE_OUTPUT_DIR)
    
    os.makedirs(pp_c.WORK_DIR, exist_ok=True)
    os.makedirs(pp_c.INTERMEDIATE_OUTPUT_DIR)
    os.makedirs(os.path.dirname(pp_c.COMBINED_OUTPUT_DIR), exist_ok=True)
    os.makedirs(os.path.dirname(pp_c.COMBINED_TREES_OUTPUT_GDB), exist_ok=True)
    os.makedirs(pp_c.COMMUNITY_OUTPUT_DIR, exist_ok=True)
    os.makedirs(pp_c.COMBINED_OUTPUT_DIR, exist_ok=True)

    pp.spaces.prepare_stats_fc ()
              
    community_specs = __get_communities(pp_c.SUBSET_START_POINT, pp_c.SUBSET_COUNT)
    
    if pp_c.IS_CREATE_SPACES:
        if pp_c.PROCESSORS > 1:
            p = multiprocessing.Pool(pp_c.PROCESSORS)
            p.map(pp.spaces.run_mp, community_specs, 1)
            p.close()        
        else:
            # Process each community past the alphabetical starting point
            for community_spec in community_specs:
                pp.spaces.run_mp (community_spec)
                
    if pp_c.IS_COMBINE_SPACES:              
        pp.spaces.combine_spaces_fcs (community_specs)
        
    if pp_c.IS_CREATE_TREES:
        for community_spec in community_specs:
            community_spaces_fc = pp.spaces.get_community_spaces_fc_name (community_spec[0])
            community_trees_fc = pp.spaces.get_community_trees_fc_name (community_spec[0])
            pp_c.delete ([community_trees_fc])           
            pp.locate_trees.run (community_spaces_fc, None, pp_c.TREE_TEMPLATE_FC, community_trees_fc)
            
                
    if pp_c.IS_COMBINE_TREES:              
        pp.spaces.combine_trees_fcs (community_specs)      
        
        
    if pp_c.IS_UPDATE_TREE_STATS:
        pp.spaces.compute_tree_stats ()
        
    
    pp_c.log_info('Complete: %s' % ([c[0] for c in community_specs]))
    return



    
        
def __get_communities (start_point, count):
    communities = []
    with arcpy.da.SearchCursor(pp_c.MUNI_COMMUNITY_AREA, ['OBJECTID', 'COMMUNITY', 'SHAPE@']) as cursor:
        for attr_vals in cursor:
            communities.append( (attr_vals[1], int(attr_vals[2].getArea('PLANAR', 'ACRES')), attr_vals[0]) )

    community_names = [c[0] for c in communities]
    if len(community_names) != len(set(community_names)):
        raise Exception ("Duplicate community names: %s" % str(community_names))
        
    communities_sorted = [c for c in sorted(communities, key=lambda x: x[0].lower()) if c[0].lower() >= start_point.lower()][0:count]        
    return communities_sorted




    

if __name__ == '__main__':
    
    run()
#    run ('B', 2)
#    run ('Albany Park', 1)
#    run ('', 9999)
    
    # if len(sys.argv) == 1:
    #     run('', 9999)
    # elif len(sys.argv) == 2:
    #     run(sys.argv[1], 9999)
    # else:
    #     run(sys.argv[1], int(sys.argv[2]))


