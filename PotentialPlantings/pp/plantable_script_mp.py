import arcpy
import os
import multiprocessing
import shutil

import pp.common as pp_c

import pp.spaces
import pp.trees
import pp.stats

import pp.logger


def run():
    pp_c.log_info ("Logging to %s" % pp.logger.LOG_FILE)
    
    arcpy.env.overwriteOutput = True
    
    if os.path.isdir(pp_c.TEMP_DIR):
        shutil.rmtree(pp_c.TEMP_DIR)
    
    os.makedirs(pp_c.TEMP_DIR, exist_ok=True)
    os.makedirs(pp_c.COMMUNITIES_DIR, exist_ok=True)

    # Prepare the output databases
    for workspace in [pp_c.SPACES_GDB, pp_c.TREES_AND_STATS_GDB]:
        if not arcpy.Exists(workspace):
            raise Exception ("%s geodatabase does not exist" % (workspace))
        if pp_c.IS_SCRATCH_OUTPUT_DATA: 
            arcpy.env.workspace = workspace
            pp_c.delete (arcpy.ListFeatureClasses())
        pp_c.create_domains (workspace, pp_c.DOMAIN_ASSIGNMENTS[workspace])
    
    # Prepare the output feature classes            
    pp.spaces.prepare_fc ()
    pp.trees.prepare_fc ()
    pp.stats.prepare_fc ()
                  
    community_specs = __get_communities(pp_c.SUBSET_START_POINT, pp_c.SUBSET_COUNT, pp_c.SUBSET_LIST)
    
    if pp_c.PROCESSORS > 1:
        p = multiprocessing.Pool(pp_c.PROCESSORS)
        p.map(create_spaces_and_trees, community_specs, 1)
        p.close()        
    else:
        # Process each community past the alphabetical starting point
        for community_spec in community_specs:                       
            create_spaces_and_trees (community_spec)
                           
    if pp_c.IS_COMBINE_SPACES:              
        pp.spaces.combine_spaces_fcs (community_specs)
                
    if pp_c.IS_COMBINE_TREES:              
        pp.trees.combine_trees_fcs (community_specs)   
        
    pp.stats.combine_stats (community_specs)        
                    
    pp_c.log_info('Complete: %s' % ([c[0] for c in community_specs]))
    return


def create_spaces_and_trees (community_spec):
    try:       
        arcpy.env.outputZFlag = "Disabled"
        arcpy.env.outputMFlag = "Disabled"
        arcpy.overwriteOutput = True
        
        __prepare_community_gdb (community_spec) 
        
        if pp_c.IS_CREATE_SPACES:
            pp.spaces.find_spaces (community_spec)
                           
        if pp_c.IS_CREATE_TREES:          
            pp.trees.site_trees (community_spec)       


        pp_c.log_info('Complete:', community_spec[0])
        return
    
    except Exception as ex:
      pp_c.log_debug ('Exception: %s' % (str(ex)))
      raise ex
        
              
def __get_communities (start_point, count, list_):
    listed_communities = list(set([c.strip() for c in list_.split(',')]))
    
    communities = []
    with arcpy.da.SearchCursor(pp_c.MUNI_COMMUNITY_AREA, ['OBJECTID', 'COMMUNITY', 'SHAPE@']) as cursor:
        for attr_vals in cursor:
            communities.append( (attr_vals[1], int(attr_vals[2].getArea('PLANAR', 'ACRES')), attr_vals[0]) )

    community_names = [c[0] for c in communities]
    if len(community_names) != len(set(community_names)):
        raise Exception ("Duplicate community names: %s" % str(community_names))
        
    communities_sorted = [c for c in sorted(communities, key=lambda x: x[0].lower()) if c[0].lower() >= start_point.lower()][0:count]        
    listed_communities2 = [c for c in communities if c[0] in listed_communities]
    return communities_sorted + sorted(listed_communities2, key=lambda x: x[0].lower())


def __prepare_community_gdb (community_spec):
    community, acres, community_id = community_spec
    community_gdb = pp_c.get_community_gdb (community)
    if not arcpy.Exists(community_gdb):
            arcpy.CreateFileGDB_management(os.path.dirname(community_gdb), os.path.basename(community_gdb))
    
    

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


