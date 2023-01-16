
import sys
import os
import math
import fs.common_functions
import arcpy
import multiprocessing
import traceback

_threads = multiprocessing.cpu_count()

def log (message):
    fs.common_functions.log(message)
    return

def log_progress (message, max_range, step_count, threads=1):
    fs.common_functions.log_progress (message, max_range, step_count, threads)
    return
        
def weighted_mean (measure_1, weight_1, measure_2, weight_2):
    return ((measure_1*weight_1) + (measure_2*weight_2)) / (weight_1 + weight_2)


# This function gets called on a new process, processes its assigned set of clumps and writes
# the results out to a feature class where the parent process can find it
#
# Input tuple is <input feature class, clumped tile pair list, min_clump_id, max_clump_id>
def process_clumps_mp (tuple):
    try:
        # Unpack the input tuple
        fc_input, fc_output, clumped_tile_pairs, min_clump_id, max_clump_id, scratch_ws = tuple
        
        arcpy.env.overwriteOutput = True
        arcpy.env.scratchWorkspace = scratch_ws
        sr = arcpy.Describe(fc_input).spatialReference
        log ('Ready to process ' + str(len(clumped_tile_pairs)) + ' clumps')
    
        # Only the name of the output database and feature class are passed in, we have to create them
        db_name = os.path.dirname(fc_output)
        if not arcpy.Exists(db_name):
            log('Creating file geodatabase ' + db_name)
            arcpy.CreateFileGDB_management(os.path.dirname(db_name), os.path.basename(db_name))
            
        # Populate an in-memory output feature class for this thread. At the end we copy the results to the caller specified feature class
        in_mem_fc_ouput = 'in_memory\\' + arcpy.Describe(fc_input).baseName
        query = '("ClumpId">=' + str(min_clump_id) + " AND " + '"ClumpId"<=' + str(max_clump_id) + ')'
        arcpy.FeatureClassToFeatureClass_conversion(fc_input, os.path.dirname(in_mem_fc_ouput), os.path.basename(in_mem_fc_ouput), query)

        log ('Copied %s records from %s to %s' % (arcpy.GetCount_management(in_mem_fc_ouput), fc_input, in_mem_fc_ouput))        

    
        i=0
        for clump_id, tile_pairs in clumped_tile_pairs.items():
            # Process the clump
            i += 1
            log_progress("Processing clump " + str(clump_id), len(clumped_tile_pairs), i, _threads)
            for tile_pair in tile_pairs:
                # Process the tile pair within the clump
                tile_id_a = tile_pair[0]
                tile_id_b = tile_pair[1]
                
                trees_a = dict()
                trees_b = dict()

                attr_list = ['SHAPE@',      # 0
                        'Area',             # 1
                        'Max_Ht',           # 2
                        'Mean_Blue',        # 3
                        'Mean_Green',       # 4
                        'Mean_Ht',          # 5
                        'Mean_Intst',       # 6
                        'Mean_NDVI',        # 7
                        'Mean_NIR',         # 8
                        'Mean_Nm_Rt',       # 9
                        'Mean_Red',         # 10
                        'Perimeter',        # 11
                        'Pt_Density',       # 12
                        'Radius_Th',        # 13
                        'Rel_Bdr_Tr',       # 14
                        'Std_Dev_Ht',       # 15
                        'TileId',           # 16
                        'PolygonId',        # 17
                        ]
                        

                SHAPE=0
                Area=1
                Max_Ht=2
                Mean_Blue=3
                Mean_Green=4
                Mean_Ht=5
                Mean_Intst=6
                Mean_NDVI=7
                Mean_NIR=8
                Mean_Nm_Rt=9
                Mean_Red=10
                Perimeter=11
                Pt_Density=12
                Radius_Th=13
                Rel_Bdr_Tr=14
                Std_Dev_Ht=15
                TileId=16
                PolygonId=17
                
                
                query = '("TileId"=' + str(tile_id_a) + " OR " + '"TileId"=' + str(tile_id_b) + ") AND (" + '"ClumpId"=' + str(clump_id) + ')'
                with arcpy.da.UpdateCursor(in_mem_fc_ouput, attr_list, query, sr, False) as cursor:
                    ####################################################################### 
                    # Create polygon object for all fence sitters
                    for attrs in cursor:
                        # Figure out which side of the fence it is on
                        oid =  str(attrs[PolygonId])
                        if attrs[TileId] == tile_id_a:
                            trees_a[oid] = attrs
                        else:
                            trees_b[oid] = attrs
                    
                    ####################################################################### 
                    # Create a "scorecard" for each pair of fence sitters       
                    scores = list()
                    for oid_a, tree_a in trees_a.items():
                        for oid_b, tree_b in trees_b.items():
                            if (tree_a[SHAPE].touches(tree_b[SHAPE])):
                                # Calculate the score (shared fence to total area ratio) and append it to the list
                                score = tree_a[SHAPE].intersect(tree_b[SHAPE],2).length / (tree_a[SHAPE].area + tree_b[SHAPE].area)
                                if score > 0:
                                    scores.append([oid_a, oid_b, score])
                    scores = sorted(scores, key=lambda x: x[2], reverse=True)
                    
                    #######################################################################        
                    # From the scores, figure out which polygons to join and which to delete
                    union_polygons = dict()
                    delete_polygons = set()
                    for score in scores: 
                        oid_a = score[0]
                        oid_b = score[1]
                        if ( (oid_a not in union_polygons.keys()) and (oid_b not in delete_polygons) ):
                            union_polygons[oid_a] = oid_b
                            delete_polygons.add(oid_b)
                
                    #######################################################################        
                    # Update the shapefile. Replace the A side with the union, then delete the B side
                    cursor.reset()
                    for attrs in cursor:
                        # Check if the current tree needs to be joined or delted
                        if (attrs[TileId] == tile_id_a) and (str(attrs[PolygonId]) in union_polygons.keys()):
                            # Update the tree attributes
                            tree_a = trees_a[str(attrs[PolygonId])]
                            tree_b = trees_b[union_polygons[str(attrs[PolygonId])]]
                            shared_fence_len = tree_a[SHAPE].intersect(tree_b[SHAPE],2).length
                            attrs[SHAPE] = tree_a[SHAPE].union(tree_b[SHAPE])
                            attrs[Area] = tree_a[Area] + tree_b[Area]     
                            attrs[Max_Ht] = max(tree_a[Max_Ht], tree_b[Max_Ht])
                            attrs[Mean_Blue] = weighted_mean (tree_a[Mean_Blue], tree_a[Area], tree_b[Mean_Blue], tree_b[Area])     
                            attrs[Mean_Green] = weighted_mean (tree_a[Mean_Green], tree_a[Area], tree_b[Mean_Green], tree_b[Area])     
                            attrs[Mean_Ht] = weighted_mean (tree_a[Mean_Ht], tree_a[Area], tree_b[Mean_Ht], tree_b[Area])     
                            attrs[Mean_Intst] = weighted_mean (tree_a[Mean_Intst], tree_a[Area], tree_b[Mean_Intst], tree_b[Area])     
                            attrs[Mean_NDVI] = weighted_mean (tree_a[Mean_NDVI], tree_a[Area], tree_b[Mean_NDVI], tree_b[Area])     
                            attrs[Mean_NIR] = weighted_mean (tree_a[Mean_NIR], tree_a[Area], tree_b[Mean_NIR], tree_b[Area])     
                            attrs[Mean_Nm_Rt] = weighted_mean (tree_a[Mean_Nm_Rt], tree_a[Area], tree_b[Mean_Nm_Rt], tree_b[Area])     
                            attrs[Mean_Red] = weighted_mean (tree_a[Mean_Red], tree_a[Area], tree_b[Mean_Red], tree_b[Area])     
                            attrs[Perimeter] =  tree_a[Perimeter] + tree_b[Perimeter] - (2*shared_fence_len)
                            attrs[Pt_Density] = weighted_mean (tree_a[Pt_Density], tree_a[Area], tree_b[Pt_Density], tree_b[Area])     
                            attrs[Radius_Th] = None
                            attrs[Rel_Bdr_Tr] = None
                            attrs[Std_Dev_Ht] = weighted_mean (tree_a[Std_Dev_Ht], tree_a[Area], tree_b[Std_Dev_Ht], tree_b[Area])     

                            cursor.updateRow(attrs)
            #                print 'Joined: ' + str(attrs[PolygonId]) + ' and ' + str(tree_b[PolygonId])
                        if (attrs[TileId] == tile_id_b) and (str(attrs[PolygonId]) in delete_polygons):
                            cursor.deleteRow()
            #                print 'Deleted: ' + str(attrs[PolygonId])
                del cursor
    
        # Write the results to the caller-specified feature class
        log ('Populating output feature class with %s records' % (arcpy.GetCount_management(in_mem_fc_ouput)))        
        arcpy.CopyFeatures_management(in_mem_fc_ouput, fc_output)
        arcpy.Delete_management(in_mem_fc_ouput)
        log ('Worker process ending')
    
    except Exception as e:
        log("Exception: " + str(e))
        log(traceback.format_exc())
        arcpy.AddError(str(e))
        raise  
    return;

def prepare_mp_tuples (fc_input, clumped_tile_pairs, temporary_assets):
    mp_tuples = list()
       
    # Sort the list of clump ids then create a chunk for eash thread
    clump_ids = sorted(clumped_tile_pairs.keys())
    chunk_size = int(math.ceil(len(clumped_tile_pairs)/float(_threads)))
    chunked_clump_ids = [clump_ids[i * chunk_size:(i + 1) * chunk_size] for i in range((len(clump_ids) + chunk_size - 1) // chunk_size )]
    
    # Generate the input tuple for each thread
    for i in range(_threads):
        # Subset the dictionary for this thread
        clumped_tile_pairs_mp = dict((k, clumped_tile_pairs[k]) for k in chunked_clump_ids[i] if k in clumped_tile_pairs)        
        # Create the feature class names for this thread (where the thread strores its output)
        min_clump_id = chunked_clump_ids[i][0]
        max_clump_id = chunked_clump_ids[i][len(chunked_clump_ids[i])-1]
        fc_output = os.path.join(os.path.dirname(arcpy.env.scratchGDB), 'scratch_TEMP_' + str(i) + '.gdb','mp_fence_sitters_merge')
        temporary_assets += [fc_output, os.path.dirname(fc_output)]
        # Create the tuple and add it to the list
        mp_tuples.append((fc_input, fc_output, clumped_tile_pairs_mp, min_clump_id, max_clump_id, arcpy.env.scratchWorkspace))
        
    return mp_tuples



def get_clumped_tile_pairs (fc, sr):
    
    attr_list = ['TileId',        # 0
                 'ClumpId']       # 1
    TileId=0
    ClumpId=1
    
    # Create a list of clumps, along with the tail pairs in each
    clumps = dict()
    query = ''     
    # Read in all polygons that are in a clump (which implies they are fence sitters)       
    with arcpy.da.SearchCursor(fc, attr_list, query, sr, False) as cursor:
        for attrs in cursor:
            tile_id = attrs[TileId]
            clump_id = attrs[ClumpId]
            if (clump_id not in clumps):
                clumps[clump_id] = set([tile_id])
            else:
                clumps[clump_id].add(tile_id)
                            
    del cursor
    
    # Get a list of pairwise combinations for the tiles in each clump
    clumped_tile_pairs = dict()
    for clump, tiles in clumps.items():
        tiles = list(tiles)
        if len(tiles) > 1:
            clumped_tile_pairs[clump] = list()
            for i, tile in enumerate(tiles):
                for j in range(i+1, len(tiles)):
                    clumped_tile_pairs[clump].append([tile,tiles[j]])

    log ("Discovered " + str(len(clumped_tile_pairs)) + " clumps")
    return clumped_tile_pairs





def merge (fc_input, fc_output):
    arcpy.env.overwriteOutput = True
    temporary_assets = list()
    try:              
        sr = arcpy.Describe(fc_input).spatialReference
        # Create indexes on the queried fields 
        fs.common_functions.create_index (fc_input, ['ClumpId'], 'ClumpIdx')  

        # Extract the non-fence sitters to reduce the working set. They are irrelevant to this step
        log ("Reducing working set - copy non fence sitters to " + fc_output)
        arcpy.FeatureClassToFeatureClass_conversion(fc_input, os.path.dirname(fc_output), os.path.basename(fc_output), '"ClumpId" IS NULL')

        # Extract the fence sitters to  new feature class.
        fence_sitters_only = os.path.join(os.path.dirname(fc_output), 'fence_sitters_only')
        fence_sitters_only = os.path.join(arcpy.env.scratchGDB, 'fence_sitters_only')
        log ("Reducing working set - copy fence sitters to " + fence_sitters_only)
        arcpy.FeatureClassToFeatureClass_conversion(fc_input, os.path.dirname(fence_sitters_only), os.path.basename(fence_sitters_only), '"ClumpId" IS NOT NULL')
        fs.common_functions.create_index (fence_sitters_only, ['ClumpId'], 'ClumpIdx')  
        temporary_assets += [fence_sitters_only]
        
        # Get the list of clumps along with the tile pairs in each
        clumped_tile_pairs = get_clumped_tile_pairs (fence_sitters_only, sr)

        # Create the lists tuples that are passed as input to the multiprocessing functions 
        mp_tuples = prepare_mp_tuples (fence_sitters_only, clumped_tile_pairs, temporary_assets)

        # Launch the worker threads. Each will update its own feature class to avoid lock conflicts
        log('Launching ' + str(_threads) + ' worker processes')
        p = multiprocessing.Pool(_threads)
        p.map(process_clumps_mp, mp_tuples)
        p.close()
        
        # Reassemble the feature classes
        for tuple in mp_tuples:
            fc_input, fc_output_mp, clumped_tile_pairs, min_clump_id, max_clump_id, scratch_ws = tuple
            log('Appending %s records from ' % (arcpy.GetCount_management(fc_output_mp)) + fc_output_mp + ' to ' + fc_output)
            arcpy.Append_management(fc_output_mp, fc_output)


    finally:
        # Clean up    
        for temporary_asset in temporary_assets:    
            # log('Deleting ' + temporary_asset)
            arcpy.Delete_management(temporary_asset)
        log("Done")



if __name__ == '__main__':
     merge(sys.argv[1], sys.argv[2])
    
    



