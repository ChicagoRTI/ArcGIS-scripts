# -*- coding: utf-8 -*-
"""
Created on Tue Mar 20 11:07:22 2018

@author: Don
"""
# To run from Spyder iPython console:
#   runfile('D:/CRTI/python_projects/ArcGIS-scripts/CRTI Python Toolkit/merge_fence_sitters.py', wdir='D:/CRTI/python_projects/ArcGIS-scripts/CRTI Python Toolkit', args="'C:\Users\Don\Documents\ArcGIS\scratch.gdb\merged_tiles_clumped' 'C:\Users\Don\Documents\ArcGIS\scratch.gdb\merged_tiles_clumped_test'")
#
# To run under ArcGIS python:
#   cd D:\CRTI\python_projects\ArcGIS-scripts\CRTI Python Toolkit\
#   C:\Python27_ArcGIS\ArcGIS10.6\python -m merge_fence_sitters "D:/CRTI/GIS data/DP_sample_area_w_clumps/original/DP_sample_area_w_clumps.shp" "D:/CRTI/GIS data/DP_sample_area_w_clumps/work/DP_sample_area_w_clumps.shp"

# Make sure the ArcGIS components are in the system path (from C:\Program Files (x86)\ArcGIS\Desktop10.6\Support\Python/Desktop10.6.pth)
import sys
import os
import math
import common_functions
common_functions.add_arcgis_to_sys_path()
import arcpy
import multiprocessing

_threads = multiprocessing.cpu_count()

def log (message):
    common_functions.log(message)
    return
        
def weighted_mean (measure_1, weight_1, measure_2, weight_2):
    return ((measure_1*weight_1) + (measure_2*weight_2)) / (weight_1 + weight_2)


# Input tuple is <input feature class, clumped tile pair list, logfile>
def process_clumps_mp (tuple):
    # Unpack the input tuple
    fc, clumped_tile_pairs, log_file = tuple
    sr = arcpy.Describe(fc).spatialReference
    common_functions.log_mp (log_file, 'Ready to process ' + str(len(clumped_tile_pairs)) + ' clumps')

    i=0
    for clump_id, tile_pairs in clumped_tile_pairs.iteritems():
        # Process the clump
        i += 1
        common_functions.log_progress_mp(log_file, "Processing clump " + str(clump_id), len(clumped_tile_pairs), i)
        for tile_pair in tile_pairs:
            # Process the tile pair within the clump
            tile_id_a = tile_pair[0]
            tile_id_b = tile_pair[1]
            
            trees_a = dict()
            trees_b = dict()
            
            attr_list = ['SHAPE@',     # 0
                    'PolygonId',   # 1
                    'TileId',      # 2
                    'Area',        # 3
                    'Border_len',  # 4
                    'Border_tre',  # 5
                    'Compactnes',  # 6
                    'nDSM_max',    # 7
                    'nDSM_mean',   # 8
                    'nDSM_min',    # 9
                    'RelBord_tr',    # 10
                    'ShapeIndex']    # 11
            SHAPE=0
            PolygonId=1
            TileId=2
            Area=3
            Border_len=4
            Border_tre=5
            Compactnes=6
            nDSM_max=7
            nDSM_mean=8
            nDSM_min=9
            RelBord_tr=10
            ShapeIndex=11
            
            query = '("TileId"=' + str(tile_id_a) + " OR " + '"TileId"=' + str(tile_id_b) + ") AND (" + '"ClumpId"=' + str(clump_id) + ')'
            with arcpy.da.UpdateCursor(fc, attr_list, query, sr, False) as cursor:
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
        #                attrs[Border_len] = convert_units (tree_a[SHAPE].length, sr.linearUnitTileId, "Feet", False)
        #                attrs[Border_tre] =  weighted_mean (tree_a[Border_tre], tree_a[Area], tree_b[Border_tre], tree_b[Area])                
                        attrs[Border_len] =  tree_a[Border_len] + tree_b[Border_len] - (2*shared_fence_len)
                        attrs[Border_tre] =  tree_a[Border_tre] + tree_b[Border_tre] - (2*shared_fence_len)                
                        attrs[RelBord_tr] =  attrs[Border_tre] / attrs[Border_len]
                        attrs[Compactnes] = (4 * math.pi * attrs[Area]) / math.pow(attrs[Border_len],2)
                        attrs[nDSM_max] = max(tree_a[nDSM_max], tree_b[nDSM_max])
                        attrs[nDSM_mean] = weighted_mean (tree_a[nDSM_mean], tree_a[Area], tree_b[nDSM_mean], tree_b[Area])
                        attrs[nDSM_min] = min(tree_a[nDSM_min], tree_b[nDSM_min])
                        attrs[ShapeIndex] =  attrs[Border_len] / (4 * math.sqrt(attrs[Area]))
                        cursor.updateRow(attrs)
        #                print 'Joined: ' + str(attrs[PolygonId]) + ' and ' + str(tree_b[PolygonId])
                    if (attrs[TileId] == tile_id_b) and (str(attrs[PolygonId]) in delete_polygons):
                        cursor.deleteRow()
        #                print 'Deleted: ' + str(attrs[PolygonId])
            del cursor
    return;

def prepare_mp_tuples (fc_input, clumped_tile_pairs,temporary_assets):
    log('Preparing to launch ' + str(_threads) + ' worker processes')
    mp_tuples = list()
       
    # Sort the list of clump ids then create a chunk for eash thread
    clump_ids = sorted(clumped_tile_pairs.keys())
    chunk_size = int(math.ceil(len(clumped_tile_pairs)/float(_threads)))
    chunked_clump_ids = [clump_ids[i * chunk_size:(i + 1) * chunk_size] for i in range((len(clump_ids) + chunk_size - 1) // chunk_size )]
    
    # Create a feature class in a new geodatabase for each thread
    for i in range(_threads):
        # Create an empty feature class in a new geodatabase for this thread
        db_name_mp = os.path.join(os.path.dirname(arcpy.env.scratchGDB), 'scratch_TEMP_' + str(i) + '.gdb')
        fc_input_mp = os.path.join(db_name_mp, 'mp_fence_sitters_merge')
        if not arcpy.Exists(db_name_mp):
            log('Creating file geodatabase ' + db_name_mp)
            arcpy.CreateFileGDB_management(os.path.dirname(db_name_mp), os.path.basename(db_name_mp))
        
        # Subset the dictionary for this thread
        clumped_tile_pairs_mp = dict((k, clumped_tile_pairs[k]) for k in chunked_clump_ids[i] if k in clumped_tile_pairs)
        
        # Populate the feature class for this thread
        log('Populating feature class for worker process ' + str(i))
        query = '("ClumpId">=' + str(chunked_clump_ids[i][0]) + " AND " + '"ClumpId"<=' + str(chunked_clump_ids[i][len(chunked_clump_ids[i])-1]) + ')'
        arcpy.FeatureClassToFeatureClass_conversion(fc_input, os.path.dirname(fc_input_mp), os.path.basename(fc_input_mp), query)
        temporary_assets += [fc_input_mp, db_name_mp]
        # Append to the return list
        mp_tuples.append((fc_input_mp, clumped_tile_pairs_mp, common_functions.log_mp_fn))
        
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
    for clump, tiles in clumps.iteritems():
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
        common_functions.create_index (fc_input, ['TileId', 'ClumpId'], 'TileClumpIdx')  
        common_functions.create_index (fc_input, ['ClumpId'], 'ClumpIdx')  

        # Extract the non-fence sitters to reduce the working set. They are irrelevant to this step
        log ("Reducing working set - copy non fence sitters to " + fc_output)
        arcpy.FeatureClassToFeatureClass_conversion(fc_input, os.path.dirname(fc_output), os.path.basename(fc_output), '"ClumpId" IS NULL')

        # Extract the fence sitters to  new feature class.
        fence_sitters_only = os.path.join('in_memory', 'fence_sitters_only')
        log ("Reducing working set - copy fence sitters to " + fence_sitters_only)
        arcpy.FeatureClassToFeatureClass_conversion(fc_input, os.path.dirname(fence_sitters_only), os.path.basename(fence_sitters_only), '"ClumpId" IS NOT NULL')
        temporary_assets += [fence_sitters_only]
        
        # Get the list of clumps along with the tile pairs in each
        clumped_tile_pairs = get_clumped_tile_pairs (fence_sitters_only, sr)

        # Create the lists tuples that are passed as input to the multiprocessing functions 
        mp_tuples = prepare_mp_tuples (fence_sitters_only, clumped_tile_pairs, temporary_assets)

        # Launch the worker threads. Each will update its own feature class to avoid lock conflicts
        log('Logging multiprocess activity to ' + common_functions.log_mp_fn)
        p = multiprocessing.Pool(_threads)
        p.map(process_clumps_mp, mp_tuples)
        p.close()

        
        # Reassemble the feature classes
        for tuple in mp_tuples:
            fc_input_mp, clumped_tile_pairs, log_file = tuple
            log('Appending ' + fc_input_mp + ' to ' + fc_output)
            arcpy.Append_management(fc_input_mp, fc_output)


    finally:
        # Clean up    
        for temporary_asset in temporary_assets:    
            log('Deleting ' + temporary_asset)
            arcpy.Delete_management(temporary_asset)
        log("Done")



if __name__ == '__main__':
     merge(sys.argv[1], sys.argv[2])
    
    



