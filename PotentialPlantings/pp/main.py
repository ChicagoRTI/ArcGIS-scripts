# Requires python 3


import arcpy
import os
import math
import numpy as np
from datetime import datetime

import pp.logger.logger
logger = pp.logger.logger.get('pp_log')


WRITE_TO_DEBUG_MASK_FC = False

USE_NUMPY = False


#OPENINGS_FC = r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\data\test.gdb\opening_single'
OPENINGS_FC = r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\pp\data\test.gdb\openings'
NEG_BUFFERED_FC = r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\pp\data\test.gdb\NEG_BUFFERed'
MATRIX_FC = r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\pp\data\test.gdb\matrix'
MASK_FC = r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\pp\data\test.gdb\mask'
MIN_DIAMETER = 10 * 0.3048
NEG_BUFFER = - (10 * 0.3048)



SMALL = 0
MEDIUM = 1
BIG = 2
VACANT = 100
OUTSIDE_POLYGON = 101
CANOPY = 102


TREE_CATEGORIES = [BIG, MEDIUM, SMALL]

# This is the footprint dimension of each tree catetory. It is a multiple of 
# the MIN_DIAMETER and must be an odd number
TREE_FOOTPRINT_DIM = {SMALL:  1,
                      MEDIUM: 3,
                      BIG:    5}

def run ():
    logger.info ("Logging to %s" % pp.logger.logger.LOG_FILE)
    logger.debug  ("Using numpy? %s" % str(USE_NUMPY))    
    times = [0,0,0]    
    stats_totals = [0,0,0,0,0,0,0]             
                
    arcpy.management.DeleteFeatures(MATRIX_FC)
    arcpy.management.DeleteFeatures(MASK_FC)

    logger.debug  ("Negative buffering")    
    arcpy.management.Delete(NEG_BUFFERED_FC)
    arcpy.GraphicBuffer_analysis(OPENINGS_FC, NEG_BUFFERED_FC, NEG_BUFFER)
    
    
    logger.debug  ("Calculating points")
    __print_header ()
    with arcpy.da.SearchCursor(NEG_BUFFERED_FC, ['ORIG_FID', 'SHAPE@']) as cursor:
        for attrs in cursor:
            times[0] = datetime.now()
            oid = attrs[0]
            polygon = attrs[1]
            x_min, y_min, x_max, y_max = polygon.extent.XMin, polygon.extent.YMin, polygon.extent.XMax, polygon.extent.YMax 

            center = arcpy.Point((x_min+x_max)/2, (y_min+y_max)/2)
            tiers = math.ceil(max((x_max-x_min)/2, (y_max-y_min)/2) / MIN_DIAMETER)
            
            # The mask orgin is the NW corner and indexed row major as  [row][col]
            mask_row_dim, mask_col_dim = __get_mask_dim (polygon, center, tiers)
            if USE_NUMPY:
                mask = np.full( (mask_row_dim, mask_col_dim), VACANT, dtype=np.uint8)
            else:
                mask = [[VACANT for _ in range(mask_col_dim)] for _ in range(mask_row_dim)]

            nw_corner = arcpy.Point (center.X - (mask_col_dim*MIN_DIAMETER)/2, center.Y + (mask_row_dim*MIN_DIAMETER)/2)            
            center_row, center_col = __point_to_mask (center, nw_corner)

            points = dict()
            
            for tree_category in TREE_CATEGORIES: 
                for tier_idx in range(0, tiers+1):
                    for row, col in __get_tier_vacancies (center_row, center_col, tier_idx, mask):        
                        fp = __get_footprint (row, col, TREE_FOOTPRINT_DIM[tree_category], mask)
                        if __is_footprint_clean (mask, *fp):  
                            if is_point_in_polygon (row, col, polygon, nw_corner, mask, points):
                                __occupy_footprint (mask, *fp, row, col, tree_category)
            times[1] = datetime.now()


            with arcpy.da.InsertCursor(MATRIX_FC, ['SHAPE@', 'code']) as cursor:
                plantings = [(r,c) for r,c in points.keys() if mask[r][c] <= BIG]
                for row,col in plantings:
                    cursor.insertRow([points[(row,col)], mask[row][col]])
            times[2] = datetime.now()


            if WRITE_TO_DEBUG_MASK_FC:
                with arcpy.da.InsertCursor(MASK_FC, ['SHAPE@', 'code', 'row', 'col', 'x', 'y', 'dim']) as cursor:
                    for r in range (0, mask_row_dim):
                        for c in range (0, mask_col_dim):
                            p = __mask_to_point (r, c, nw_corner)
                            cursor.insertRow([__mask_to_point (r, c, nw_corner), mask[r][c], r, c, p.X, p.Y, mask_row_dim])

            __print_stats (polygon, oid, times, mask_row_dim*mask_col_dim, len(points), len(plantings), stats_totals)

    __print_totals (stats_totals)



def __print_header ():
    logger.info  ("{:>12s} {:>6s} {:>6s} {:>6s} {:>6s} {:>10s} {:>10s} {:>10s}".format('OID', 'SqMtrs', 'Grid', 'Points', 'Plants', 'Time 1', 'Time 2', 'Time ttl'))
    logger.info  ('--------------------')


def __print_stats (polygon, oid, times, mask_size, potential_sites, plantings, stats_totals):
    d_1 = (times[1]-times[0]).seconds + (times[1]-times[0]).microseconds / 1000000.0
    d_2 = (times[2]-times[1]).seconds + (times[2]-times[1]).microseconds / 1000000.0
    d_3 = (times[2]-times[0]).seconds + (times[2]-times[0]).microseconds / 1000000.0
    size = round(polygon.getArea('GEODESIC', 'SQUAREMETERS'))
    s = [size, mask_size, potential_sites, plantings, d_1, d_2, d_3]

    logger.info  ("{:>12d} {:>6d} {:>6d} {:>6d} {:>6d} {:>10.3f} {:>10.3f} {:>10.3f}".format(oid, *s))

    for i in range (len(stats_totals)):
        stats_totals[i] = stats_totals[i] + s[i]
   
    
def __print_totals (stats_totals):
    logger.info  ('--------------------')
    logger.info  ("{:>12s} {:>6d} {:>6d} {:>6d} {:>6d} {:>10.3f} {:>10.3f} {:>10.3f}".format('', *stats_totals))
    


def __get_mask_dim (polygon, center, tiers):
    max_dim = tiers*2 + 1
    nw_corner = arcpy.Point (center.X - tiers*MIN_DIAMETER, center.Y + tiers*MIN_DIAMETER)
    rows_outside_extent = 2 * math.floor( (nw_corner.Y - polygon.extent.YMax) / MIN_DIAMETER ) 
    cols_outside_extent = 2 * math.floor( (polygon.extent.XMin - nw_corner.X) / MIN_DIAMETER )     
    return max_dim - rows_outside_extent, max_dim - cols_outside_extent  # This does not change the center point
    


def __get_tier_vacancies (center_row, center_col, tier_idx, mask):
    mask_row_dim, mask_col_dim =  __get_mask_dims (mask)
    rows = range(max(0, center_row - tier_idx),  min(center_row + tier_idx+1, mask_row_dim))
    cols = range(max(0, center_col - tier_idx),  min(center_col + tier_idx+1, mask_col_dim))  
    top   = [(rows[0], col)  for col in cols           if mask[rows[0]][col]  == VACANT]
    right = [(row, cols[-1]) for row in rows           if mask[row][cols[-1]] == VACANT]
    bot   = [(rows[-1], col) for col in reversed(cols) if mask[rows[-1]][col] == VACANT]
    left  = [(row, cols[0])  for row in reversed(rows) if mask[row][cols[0]]  == VACANT]
    return top + right + bot + left  


def __get_mask_dims (mask):
    if USE_NUMPY:
        mask_row_dim = mask.shape[0]
        mask_col_dim = mask.shape[1]        
    else:
        mask_row_dim = len(mask)
        mask_col_dim = len(mask[0])
    return mask_row_dim, mask_col_dim

                        
def __mask_to_point (row, col, nw_corner):
    x = nw_corner.X + col*MIN_DIAMETER
    y = nw_corner.Y - row*MIN_DIAMETER
    return arcpy.Point(x,y)


def __point_to_mask (point, nw_corner):
    row = math.floor( (nw_corner.Y - point.Y) / MIN_DIAMETER)
    col = math.floor( (point.X - nw_corner.X) / MIN_DIAMETER)
    return row, col
    

def __get_footprint (row, col, tree_footprint_dim, mask):
    mask_row_dim, mask_col_dim =  __get_mask_dims (mask)
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


def is_point_in_polygon (row, col, polygon, nw_corner, mask, points):
    if mask[row][col] == OUTSIDE_POLYGON:
        return False
    else:
        point = __mask_to_point (row, col, nw_corner)
        if point.within(polygon):
            mask[row][col] = VACANT
            points[(row,col)] = point
            return True
        else:
            mask[row][col] = OUTSIDE_POLYGON
            return False
    

def __occupy_footprint (mask, fp_row, fp_col, fp_row_dim, fp_col_dim, planting_row, planting_col, tree_category):
    for r in range (fp_row, fp_row + fp_row_dim):
        for c in range (fp_col, fp_col + fp_col_dim):
            mask[r][c] = CANOPY
    mask[planting_row][planting_col] = tree_category


if __name__ == '__main__':
     run()
    
    



