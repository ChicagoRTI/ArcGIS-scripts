# Requires python 3


import arcpy
import os
import math
import numpy as np
from datetime import datetime

from libc.stdlib cimport malloc, free
from libc.string cimport memset

import pp.logger.logger
logger = pp.logger.logger.get('pp_log')


cdef bint WRITE_TO_DEBUG_MASK_FC = False


#cdef char* OPENINGS_FC = r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\pp\data\test.gdb\opening_single'
cdef char* OPENINGS_FC = r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\pp\data\test.gdb\openings'
cdef char* NEG_BUFFERED_FC = r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\pp\data\test.gdb\NEG_BUFFERed'
cdef char* MATRIX_FC = r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\pp\data\test.gdb\matrix'
cdef char* MASK_FC = r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\pp\data\test.gdb\mask'
cdef double MIN_DIAMETER = 10 * 0.3048
cdef double NEG_BUFFER = - (10 * 0.3048)


ctypedef unsigned char mask_t


cdef mask_t SMALL = 0
cdef mask_t MEDIUM = 1
cdef mask_t BIG = 2
cdef mask_t VACANT = 100
cdef mask_t OUTSIDE_POLYGON = 101 
cdef mask_t CANOPY = 102

 
cdef struct Footprint:
    int row_origin
    int col_origin
    int row_dim
    int col_dim
    

cdef struct Mask:
    int row_dim
    int col_dim
    int cells
    int bytes_
    mask_t* array_


cdef __mask_init (Mask* m, int rows, int cols):
    m.row_dim = rows
    m.col_dim = cols
    m.cells = rows * cols
    m.bytes_ = m.cells * sizeof(mask_t)
    m.array_ = <mask_t*> malloc(m.bytes_)           
    for i in range (m.cells):
        m.array_[i]= VACANT

cdef __mask_del (Mask* m):
    free (m.array_)
    
cdef inline int __mask_get (Mask* m, int r, int c):
    return m.array_[r*m.col_dim + c]

cdef inline void __mask_set (Mask* m, int r, int c, int v):
    m.array_[r*m.col_dim + c] = v
    
cdef void __mask_print (Mask* m):
    # logger.debug("%i %i %i %i %i" % (m.row_dim, m.col_dim, m.cells, m.bytes_, sizeof(int)))
    # logger.debug("%s" % str(m.array_[0]))
    # for r in range (m.row_dim):
    #     row = [__mask_get (m, r, c) for c in range(m.col_dim)]
    #     logger.debug("%s" % str(row))
    pass




TREE_CATEGORIES = [BIG, MEDIUM, SMALL]

# This is the footprint dimension of each tree catetory. It is a multiple of 
# the MIN_DIAMETER and must be an odd number
TREE_FOOTPRINT_DIM = {SMALL:  1,
                      MEDIUM: 3,
                      BIG:    5}

def run():
    run_cython()
    
    

cdef void run_cython ():
    cdef int tree_category, tier_idx, row, col, mask_row_dim, mask_col_dim, tiers, i, mask_cells, mask_bytes, center_row, center_col
    cdef Mask m
    cdef Footprint fp
    
    logger.info ("Logging to %s" % pp.logger.logger.LOG_FILE)
    logger.debug  ("Using numpy? %s" % "No - cython")
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
            
            __mask_init (&m, mask_row_dim, mask_col_dim)
            __mask_print (&m)

            nw_corner = arcpy.Point (center.X - (m.col_dim*MIN_DIAMETER)/2, center.Y + (m.row_dim*MIN_DIAMETER)/2)            
            center_row, center_col = __point_to_mask (center, nw_corner)

            points = dict()
            
            for tree_category in TREE_CATEGORIES: 
                for tier_idx in range(0, tiers+1):
                    for row, col in __get_tier_vacancies (center_row, center_col, tier_idx, &m):        
                        __get_footprint (row, col, TREE_FOOTPRINT_DIM[tree_category], &m, &fp)
                        if __is_footprint_clean (&m, &fp):  
                            if is_point_in_polygon (row, col, polygon, nw_corner, &m, points):
                                __occupy_footprint (&m, &fp, row, col, tree_category)
            times[1] = datetime.now()


            with arcpy.da.InsertCursor(MATRIX_FC, ['SHAPE@', 'code']) as cursor:
                plantings = [(r,c) for r,c in points.keys() if m.array_[r*m.col_dim + c] <= BIG]
                for row,col in plantings:
                    cursor.insertRow([points[(row,col)], m.array_[row*m.col_dim + col]])
            times[2] = datetime.now()


            if WRITE_TO_DEBUG_MASK_FC:
                with arcpy.da.InsertCursor(MASK_FC, ['SHAPE@', 'code', 'row', 'col', 'x', 'y', 'dim']) as cursor:
                    for r in range (0, m.row_dim):
                        for c in range (0, m.col_dim):
                            p = __mask_to_point (r, c, nw_corner)
                            cursor.insertRow([__mask_to_point (r, c, nw_corner), m.array_[r*m.col_dim + c], r, c, p.X, p.Y, mask_row_dim])

            __print_stats (polygon, oid, times, m.cells, len(points), len(plantings), stats_totals)
            __mask_del (&m)
            
    __print_totals (stats_totals)



cdef void __print_header ():
    logger.info  ("{:>12s} {:>6s} {:>6s} {:>6s} {:>6s} {:>10s} {:>10s} {:>10s}".format('OID', 'SqMtrs', 'Grid', 'Points', 'Plants', 'Time 1', 'Time 2', 'Time ttl'))
    logger.info  ('--------------------')


cdef void __print_stats (polygon, int oid, times, int mask_cells, potential_sites, plantings, stats_totals):
    d_1 = (times[1]-times[0]).seconds + (times[1]-times[0]).microseconds / 1000000.0
    d_2 = (times[2]-times[1]).seconds + (times[2]-times[1]).microseconds / 1000000.0
    d_3 = (times[2]-times[0]).seconds + (times[2]-times[0]).microseconds / 1000000.0
    size = round(polygon.getArea('GEODESIC', 'SQUAREMETERS'))
    s = [size, mask_cells, potential_sites, plantings, d_1, d_2, d_3]

    logger.info  ("{:>12d} {:>6d} {:>6d} {:>6d} {:>6d} {:>10.3f} {:>10.3f} {:>10.3f}".format(oid, *s))

    for i in range (len(stats_totals)):
        stats_totals[i] = stats_totals[i] + s[i]
   
    
cdef void __print_totals (stats_totals):
    logger.info  ('--------------------')
    logger.info  ("{:>12s} {:>6d} {:>6d} {:>6d} {:>6d} {:>10.3f} {:>10.3f} {:>10.3f}".format('', *stats_totals))
    


cdef __get_mask_dim (polygon, center, int tiers):
    cdef int max_dim, rows_outside_extent, cols_outside_extent
    max_dim = tiers*2 + 1
    nw_corner = arcpy.Point (center.X - tiers*MIN_DIAMETER, center.Y + tiers*MIN_DIAMETER)
    rows_outside_extent = 2 * math.floor( (nw_corner.Y - polygon.extent.YMax) / MIN_DIAMETER ) 
    cols_outside_extent = 2 * math.floor( (polygon.extent.XMin - nw_corner.X) / MIN_DIAMETER )     
    return max_dim - rows_outside_extent, max_dim - cols_outside_extent  # This does not change the center point
    

cdef __get_tier_vacancies (int center_row, int center_col, int tier_idx, Mask* m):
    rows = range(max(0, center_row - tier_idx),  min(center_row + tier_idx+1, m.row_dim))
    cols = range(max(0, center_col - tier_idx),  min(center_col + tier_idx+1,  m.col_dim))  
    top   = [(rows[0], col)  for col in cols           if __mask_get(m, rows[0], col)  == VACANT]
    right = [(row, cols[-1]) for row in rows           if __mask_get(m, row, cols[-1]) == VACANT]
    bot   = [(rows[-1], col) for col in reversed(cols) if __mask_get(m, rows[-1], col) == VACANT]
    left  = [(row, cols[0])  for row in reversed(rows) if __mask_get(m, row, cols[0])  == VACANT]
    logger.debug  ("top + right + bot + left: %s" % (str(top + right + bot + left))) 
    return top + right + bot + left  

                        
cdef __mask_to_point (int row, int col, nw_corner):
    x = nw_corner.X + col*MIN_DIAMETER
    y = nw_corner.Y - row*MIN_DIAMETER
    return arcpy.Point(x,y)


cdef __point_to_mask (point, nw_corner):
    row = math.floor( (nw_corner.Y - point.Y) / MIN_DIAMETER)
    col = math.floor( (point.X - nw_corner.X) / MIN_DIAMETER)
    return row, col
    

cdef void __get_footprint (int row, int col, int tree_footprint_dim, Mask* m, Footprint* fp):
    fp.row_origin = max(row - int((tree_footprint_dim - 1)/2), 0)
    fp.col_origin = max(col - int((tree_footprint_dim - 1)/2), 0)
    fp.row_dim = min(tree_footprint_dim, m.row_dim-fp.row_origin)
    fp.col_dim = min(tree_footprint_dim, m.col_dim-fp.col_origin)  
    return 


cdef bint __is_footprint_clean (Mask* m, Footprint* fp):    
    cdef int r, c
    for r in range (fp.row_origin, fp.row_origin + fp.row_dim):
        for c in range (fp.col_origin, fp.col_origin + fp.col_dim):
            if m.array_[r*m.col_dim + c] != VACANT:
                return False
    return True


cdef bint is_point_in_polygon (int row, int col, polygon, nw_corner, Mask * m, points):
    if m.array_[row*m.col_dim + col] == OUTSIDE_POLYGON:
        return False
    else:
        point = __mask_to_point (row, col, nw_corner)
        if point.within(polygon):
            m.array_[row*m.col_dim + col] = VACANT
            points[(row,col)] = point
            return True
        else:
            m.array_[row*m.col_dim + col] = OUTSIDE_POLYGON
            return False
    

cdef void __occupy_footprint (Mask * m, Footprint* fp, int planting_row, int planting_col, int tree_category):
    cdef int r, c
    for r in range (fp.row_origin, fp.row_origin + fp.row_dim):
        for c in range (fp.col_origin, fp.col_origin + fp.col_dim):
            m.array_[r*m.col_dim + c] = CANOPY
    m.array_[planting_row*m.col_dim + planting_col] = tree_category
    


if __name__ == '__main__':
     run()
    
    



