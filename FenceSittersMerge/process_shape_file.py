# -*- coding: utf-8 -*-
"""
Created on Tue Mar 20 11:07:22 2018

@author: Don
"""
# To run from Spyder iPython console:
#   runfile('D:/CRTI/python_projects/ArcGIS-scripts/FenceSittersMerge/process_shape_file.py', wdir='D:/CRTI/python_projects/ArcGIS-scripts/FenceSittersMerge', args="'D:/CRTI/GIS data/DP_sample_area_w_clumps/original/DP_sample_area_w_clumps.shp' 'D:/CRTI/GIS data/DP_sample_area_w_clumps/work/DP_sample_area_w_clumps.shp'")
#
# To run under ArcGIS python:
#   cd D:\CRTI\python_projects\ArcGIS-scripts\FenceSittersMerge\
#   C:\Python27_ArcGIS\ArcGIS10.6\python -m process_shape_file "D:/CRTI/GIS data/DP_sample_area_w_clumps/original/DP_sample_area_w_clumps.shp" "D:/CRTI/GIS data/DP_sample_area_w_clumps/work/DP_sample_area_w_clumps.shp"

# Make sure the ArcGIS components are in the system path (from C:\Program Files (x86)\ArcGIS\Desktop10.6\Support\Python/Desktop10.6.pth)
import sys
import math
__arc_gis_dir = "C:\\Program Files (x86)\\ArcGIS\\Desktop10.6\\"
__arc_gis_path = [__arc_gis_dir + "bin",
                __arc_gis_dir + "ArcPy",
                __arc_gis_dir + "ArcToolBox\Scripts"]
for p in __arc_gis_path: 
    if p not in sys.path: sys.path += [p]


import arcpy

# Get the input arguments
__fc_input = sys.argv[1]
__fc_output = sys.argv[2]

print (__fc_input)
print (__fc_output)

__fc_mem = "in_memory\\fence_sitters"
__sr = arcpy.Describe(__fc_input).spatialReference


#def convert_units (measure, from_unit, to_unit, is_square):
#    c_val = 0
#    if from_unit == "Meter" and to_unit == "Feet":
#        c_val = 3.048
#    if is_square:
#        c_val = c_val * c_val
#    return measure * c_val

        
def weighted_mean (measure_1, weight_1, measure_2, weight_2):
    return ((measure_1*weight_1) + (measure_2*weight_2)) / (weight_1 + weight_2)


def process_clumped_tile_pair (clump_id, tile_pair):
    tile_id_a = tile_pair[0]
    tile_id_b = tile_pair[1]
    
    trees_a = dict()
    trees_b = dict()
    
    attr_list = ['SHAPE@',     # 0
            'FID_1',    # 1
            'NAME',        # 2
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
    FID_1=1
    NAME=2
    Area=3
    Border_len=4
    Border_tre=5
    Compactnes=6
    nDSM_max=7
    nDSM_mean=8
    nDSM_min=9
    RelBord_tr=10
    ShapeIndex=11
    
    query = '("NAME"=\'' + tile_id_a + "' OR " + '"NAME"=\'' + tile_id_b + "') AND (" + '"Fence"=1) AND ("ClumpID"=' + str(clump_id) + ')'
    
    ####################################################################### 
    # Create polygon object for all fence sitters
    with arcpy.da.SearchCursor(__fc_mem, attr_list, query, __sr, False) as cursor:
        for attrs in cursor:
            # Figure out which side of the fence it is on
            oid =  str(attrs[FID_1])
            if attrs[NAME] == tile_id_a:
                trees_a[oid] = attrs
            else:
                trees_b[oid] = attrs
    del cursor
    
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
    with arcpy.da.UpdateCursor(__fc_mem, attr_list, query ,__sr, False) as cursor:
        for attrs in cursor:
            # Check if the current tree needs to be joined or delted
            if (attrs[NAME] == tile_id_a) and (str(attrs[FID_1]) in union_polygons.keys()):
                # Update the tree attributes
                tree_a = trees_a[str(attrs[FID_1])]
                tree_b = trees_b[union_polygons[str(attrs[FID_1])]]
                shared_fence_len = tree_a[SHAPE].intersect(tree_b[SHAPE],2).length
                attrs[SHAPE] = tree_a[SHAPE].union(tree_b[SHAPE])
                attrs[Area] = tree_a[Area] + tree_b[Area]                
#                attrs[Border_len] = convert_units (tree_a[SHAPE].length, __sr.linearUnitName, "Feet", False)
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
#                print 'Joined: ' + str(attrs[FID_1]) + ' and ' + str(tree_b[FID_1])
            if (attrs[NAME] == tile_id_b) and (str(attrs[FID_1]) in delete_polygons):
                cursor.deleteRow()
#                print 'Deleted: ' + str(attrs[FID_1])
    del cursor
    return;



def get_clumped_tile_pairs ():
    
    attr_list = ['NAME',        # 0
                 'ClumpID']     # 1
    NAME=0
    ClumpID=1
    
    # Create a list of clumps, along with the tail pairs in each
    clumps = dict()
    query = '("ClumpID">0)'     
    # Read in all polygons that are in a clump (which implies they are fence sitters)       
    with arcpy.da.SearchCursor(__fc_mem, attr_list, query, __sr, False) as cursor:
        for attrs in cursor:
            tile_id = attrs[NAME]
            clump_id = attrs[ClumpID]
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

    return clumped_tile_pairs

def main_process_shape_file ():
    # Copy the input feature class to memory 
    arcpy.env.workspace = "in_memory" 
    if arcpy.Exists(__fc_mem):
        arcpy.Delete_management(__fc_mem)
    if arcpy.Exists(__fc_output):
        arcpy.Delete_management(__fc_output)
    arcpy.CopyFeatures_management(__fc_input, __fc_mem)
    
    # Get the list of clumps along with the tile pairs in each
    clumped_tile_pairs = get_clumped_tile_pairs ()
    
    # Process the set of tile pairs in each clump
    i=0
    for clump, tile_pairs in clumped_tile_pairs.iteritems():
        i += 1
        print ("Processing clump " + str(clump) + " (" + str(i) + " of " + str(len(clumped_tile_pairs)) + ")")
        for tile_pair in tile_pairs:
            process_clumped_tile_pair(clump, tile_pair)
            
    # Copy the in-memory feature class back to disk
    print ("Writing results to " + __fc_output)
    arcpy.CopyFeatures_management(__fc_mem, __fc_output)
    arcpy.Delete_management(__fc_mem)



if __name__ == '__main__':
     main_process_shape_file()
    
    



