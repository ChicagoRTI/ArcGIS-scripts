# Requires python 3


import arcpy
import os
import math
import numpy as np


#OPENINGS_FC = r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\data\test.gdb\opening_single'
OPENINGS_FC = r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\data\test.gdb\openings'
NEG_BUFFERED_FC = r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\data\test.gdb\NEG_BUFFERed'
MATRIX_FC = r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\data\test.gdb\matrix'
MASK_FC = r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\data\test.gdb\mask'
MIN_DIAMETER = 5 * 0.3048
NEG_BUFFER = - (10 * 0.3048)


 


SMALL = 0
MEDIUM = 1
BIG = 2
VACANT = 100
OUTSIDE_POLYGON = 101
CANOPY = 102


TREE_CATEGORIES = [BIG, SMALL]

# This is the footprint dimension of each tree catetory. It is a multiple of 
# the MIN_DIAMETER and must be an odd number
TREE_FOOTPRINT_DIM = {SMALL:  3,
                      BIG:    5}

def run ():
                                   
    arcpy.management.DeleteFeatures(MATRIX_FC)
    arcpy.management.DeleteFeatures(MASK_FC)

    print ("Negative buffering")    
    arcpy.management.Delete(NEG_BUFFERED_FC)
    arcpy.GraphicBuffer_analysis(OPENINGS_FC, NEG_BUFFERED_FC, NEG_BUFFER)
    
    
    print ("Calculating points")    
    with arcpy.da.SearchCursor(NEG_BUFFERED_FC, ['OBJECTID', 'SHAPE@']) as cursor:
        for attrs in cursor:
            polygon = attrs[1]
            x_min, y_min, x_max, y_max = polygon.extent.XMin, polygon.extent.YMin, polygon.extent.XMax, polygon.extent.YMax 

            center = arcpy.Point((x_min+x_max)/2, (y_min+y_max)/2)
            tiers = math.ceil(max((x_max-x_min)/2, (y_max-y_min)/2) / MIN_DIAMETER)
            
            mask_row_dim, mask_col_dim = __get_mask_dim (polygon, center, tiers)
            mask = np.empty( (mask_row_dim, mask_col_dim), dtype=int)

            nw_corner = arcpy.Point (center.X - (mask_col_dim*MIN_DIAMETER)/2, center.Y + (mask_row_dim*MIN_DIAMETER)/2)            
            center_row, center_col = __point_to_mask (center, nw_corner)
            
            # The mask orgin is the NW corner and indexed row major as  [row][col]
            mask_row_dim, mask_col_dim = __get_mask_dim (polygon, center, tiers)

            points = __get_points (nw_corner, polygon, mask)

            for tree_category in TREE_CATEGORIES: 
                for tier_idx in range(0, tiers+1):
                    for row, col in __get_tier_vacancies (center_row, center_col, tier_idx, mask):        
                        fp = __get_footprint (row, col, TREE_FOOTPRINT_DIM[tree_category], mask)
                        if __is_footprint_clean (mask, *fp):                        
                            __occupy_footprint (mask, points, *fp, row, col, tree_category)


            with arcpy.da.InsertCursor(MATRIX_FC, ['SHAPE@', 'code']) as cursor:
                for row,col in [(r,c) for r,c in points.keys() if mask[r][c] <= BIG]:
                    cursor.insertRow([points[(row,col)], mask[row][col]])


            with arcpy.da.InsertCursor(MASK_FC, ['SHAPE@', 'code', 'row', 'col', 'x', 'y', 'dim']) as cursor:
                for r in range (0, mask_row_dim):
                    for c in range (0, mask_col_dim):
                        p = __mask_to_point (r, c, nw_corner)
                        cursor.insertRow([__mask_to_point (r, c, nw_corner), mask[r][c], r, c, p.X, p.Y, mask_row_dim])



def __get_mask_dim (polygon, center, tiers):
    max_dim = tiers*2 + 1
    nw_corner = arcpy.Point (center.X - tiers*MIN_DIAMETER, center.Y + tiers*MIN_DIAMETER)
    rows_outside_extent = 2 * math.floor( (nw_corner.Y - polygon.extent.YMax) / MIN_DIAMETER ) 
    cols_outside_extent = 2 * math.floor( (polygon.extent.XMin - nw_corner.X) / MIN_DIAMETER )     
    return max_dim - rows_outside_extent, max_dim - cols_outside_extent
    

def __get_points (nw_corner, polygon, mask):
    points = dict()
    mask_row_dim = mask.shape[0]
    mask_col_dim = mask.shape[1]
    for r in range (0, mask_row_dim):
        for c in range (0, mask_col_dim):
            point = __mask_to_point (r, c, nw_corner)
            if point.within(polygon):
                mask[r][c] = VACANT
                points[(r,c)] = point
            else:
                mask[r][c] = OUTSIDE_POLYGON
    return points



def __get_tier_vacancies (center_row, center_col, tier_idx, mask):
    mask_row_dim = mask.shape[0]
    mask_col_dim = mask.shape[1]
    top  = [(center_row - tier_idx, col)  for col in range (center_col - tier_idx, center_col + tier_idx + 1)]
    right= [(row, center_col + tier_idx)  for row in range (center_row - tier_idx, center_row + tier_idx + 1)]
    bot  = [(center_row + tier_idx, col)  for col in reversed(range (center_col - tier_idx, center_col + tier_idx + 1))]
    left = [(row, center_col - tier_idx)  for row in reversed(range (center_row - tier_idx, center_row + tier_idx + 1))]
    return [(row,col) for (row,col) in top + right + bot + left if row > 0 and row < mask_row_dim and col > 0 and col < mask_col_dim and mask[row, col] == VACANT]  

                     
    
def __mask_to_point (row, col, nw_corner):
    x = nw_corner.X + col*MIN_DIAMETER
    y = nw_corner.Y - row*MIN_DIAMETER
    return arcpy.Point(x,y)

def __point_to_mask (point, nw_corner):
    row = math.floor( (nw_corner.Y - point.Y) / MIN_DIAMETER)
    col = math.floor( (point.X - nw_corner.X) / MIN_DIAMETER)
    return row, col
    

def __get_footprint (row, col, tree_footprint_dim, mask):
    mask_row_dim = mask.shape[0]
    mask_col_dim = mask.shape[1]
    fp_row_origin = max(row - int((tree_footprint_dim - 1)/2), 0)
    fp_col_origin = max(col - int((tree_footprint_dim - 1)/2), 0)
    fp_row_dim = min(tree_footprint_dim, mask_row_dim-fp_row_origin)
    fp_col_dim = min(tree_footprint_dim, mask_col_dim-fp_col_origin)  
    return fp_row_origin, fp_col_origin, fp_row_dim, fp_col_dim


def __is_footprint_clean (mask, fp_row, fp_col, fp_row_dim, fp_col_dim):    
    for r in range (fp_row, fp_row + fp_row_dim):
        for c in range (fp_col, fp_col + fp_col_dim):
            if mask[r][c] != VACANT:
                return False
    return True


def __occupy_footprint (mask, points, fp_row, fp_col, fp_row_dim, fp_col_dim, planting_row, planting_col, tree_category):
    for r in range (fp_row, fp_row + fp_row_dim):
        for c in range (fp_col, fp_col + fp_col_dim):
            mask[r][c] = CANOPY
    mask[planting_row][planting_col] = tree_category


if __name__ == '__main__':
     run()
    
    



