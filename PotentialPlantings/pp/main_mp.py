# Requires python 3


import arcpy
import os
import math
import numpy as np
from datetime import datetime
import multiprocessing
import timeit

import pp.logger.logger
logger = pp.logger.logger.get('pp_log')


WRITE_TO_DEBUG_MASK_FC = False

USE_NUMPY = False


#OPENINGS_FC = r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\pp\data\test.gdb\opening_single'
#OPENINGS_FC = r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\pp\data\test.gdb\openings'
#OPENINGS_FC = r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\pp\data\test.gdb\campus_parks_projected'
OPENINGS_FC = r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\pp\data\test.gdb\chicago_parks'
#OPENINGS_FC = r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\pp\data\test.gdb\lincoln_park'
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


# Can not run in multiprocessing mode from the Spyder console
IS_MP = True
MP_NUM_CHUNKS = 8
MP_CHUNK_LIST = [(MP_NUM_CHUNKS, i, MATRIX_FC + '_' + str(i)) for i in range(MP_NUM_CHUNKS)]


def run():
    logger.info ("Logging to %s" % pp.logger.logger.LOG_FILE)
    start_time = timeit.default_timer()
    arcpy.management.DeleteFeatures(MATRIX_FC)
    
    if IS_MP:
        logger.info('Launching ' + str(MP_NUM_CHUNKS) + ' worker processes')
        __print_header ()

        # Create the set of tuples - each worker process gets one tuple for input        
        for i in range(MP_NUM_CHUNKS):
            chunk_fc = MP_CHUNK_LIST[i][2]
            arcpy.Delete_management(chunk_fc)
            arcpy.management.CreateFeatureclass(os.path.dirname(chunk_fc), os.path.basename(chunk_fc), 'POINT', MATRIX_FC)
            logger.debug('Created output feature class %s ' % chunk_fc)
 
        p = multiprocessing.Pool(MP_NUM_CHUNKS)
        stats_subtotals = p.map(run_mp, MP_CHUNK_LIST)
        p.close()
        
        logger.info('')
        logger.info('Subtotals')
        stats_totals = [0 for i in range(len(stats_subtotals[0]))]
        for i in range(MP_NUM_CHUNKS):
            __print_totals (stats_subtotals[i], i)
            for j in range (len(stats_subtotals[i])):
                stats_totals[j] = stats_totals[j] + stats_subtotals[i][j]                                      
        logger.info('')
        logger.info('Totals')
        __print_header ()
        __print_totals (stats_totals, -1)
        
                
        # Reassemble the feature classes
        for i in range(MP_NUM_CHUNKS):
            chunk_fc = MP_CHUNK_LIST[i][2]
            logger.debug('Appending ' + chunk_fc + ' to ' + MATRIX_FC)
            arcpy.Append_management(chunk_fc, MATRIX_FC)
            

    else:
        __print_header ()
        s = run_mp ( (1, 0, MATRIX_FC) )
        __print_totals (s, 0)
    
    logger.info("Program Executed in %s seconds" % str(timeit.default_timer()-start_time)) 


def run_mp (chunk):
#    logger.info ("Logging to %s" % pp.logger.logger.LOG_FILE)
    
    chunks, my_chunk, output_fc = chunk
    
    logger.debug ("Chunk %i of %i. Output will be written to %s" % (my_chunk+1, chunks, output_fc))
    
    logger.debug  ("Using numpy? %s" % str(USE_NUMPY))    
    times = [0,0,0]    
    stats_totals = [0,0,0,0,0,0,0]             
                
    if WRITE_TO_DEBUG_MASK_FC:
        arcpy.management.DeleteFeatures(MASK_FC)
    
    logger.debug  ("Calculating points")
    with arcpy.da.SearchCursor(OPENINGS_FC, ['OBJECTID', 'SHAPE@'], "(MOD(OBJECTID,%i) - %i = 0)" % (chunks, my_chunk)) as cursor:
        for attrs in cursor:
            times[0] = datetime.now()
            oid = attrs[0]
            polygon = attrs[1]
            x_min, y_min, x_max, y_max = polygon.extent.XMin, polygon.extent.YMin, polygon.extent.XMax, polygon.extent.YMax 

            center = arcpy.Point((x_min+x_max)/2, (y_min+y_max)/2)
            tiers = math.ceil(max((x_max-x_min)/2, (y_max-y_min)/2) / MIN_DIAMETER)
            
            # The mask orgin is the NW corner and indexed row major as  [row][col]
            mask_row_dim, mask_col_dim = __get_mask_dim (polygon, center, tiers)
            nw_corner = arcpy.Point (center.X - (mask_col_dim*MIN_DIAMETER)/2, center.Y + (mask_row_dim*MIN_DIAMETER)/2)            
            center_row, center_col = __point_to_mask (center, nw_corner)

            mask = __get_mask (mask_row_dim, mask_col_dim, polygon, nw_corner)
            
            # if USE_NUMPY:
            #     mask = np.full( (mask_row_dim, mask_col_dim), VACANT, dtype=np.uint8)
            # elif mask_row_dim * mask_col_dim > 0:
            #     mask = [m[:] for m in [[VACANT] * mask_col_dim] * mask_row_dim] 
            # else: 
            #     mask = __big_space (mask_row_dim, mask_col_dim, polygon, arcpy.Describe(OPENINGS_FC).spatialReference, nw_corner)

            points = dict()
            
            for tree_category in TREE_CATEGORIES: 
                for tier_idx in range(0, tiers+1):
                    for row, col in __get_tier_vacancies (center_row, center_col, tier_idx, mask, mask_row_dim, mask_col_dim):        
                        fp = __get_footprint (row, col, TREE_FOOTPRINT_DIM[tree_category], mask_row_dim, mask_col_dim)
                        if __is_footprint_clean (mask, *fp):  
                            if is_point_in_polygon (row, col, polygon, nw_corner, mask, points):
                                __occupy_footprint (mask, *fp, row, col, tree_category)
            times[1] = datetime.now()


            with arcpy.da.InsertCursor(output_fc, ['SHAPE@', 'code']) as cursor:
                plantings = [(r,c) for r,c in points.keys() if mask[r][c] <= BIG]
                for row,col in plantings:
                    cursor.insertRow([points[(row,col)], mask[row][col]])
            times[2] = datetime.now()


            if WRITE_TO_DEBUG_MASK_FC:
                with arcpy.da.InsertCursor(MASK_FC, ['SHAPE@', 'code', 'row', 'col', 'x', 'y', 'dim']) as cursor:
                    for r in range (0, mask_row_dim):
                        for c in range (0, mask_col_dim):
                            p = __mask_to_point (r, c, nw_corner)
                            cursor.insertRow([p, mask[r][c], r, c, p.X, p.Y, mask_row_dim])

            __print_stats (polygon, oid, times, mask_row_dim*mask_col_dim, len(points), len(plantings), stats_totals, my_chunk)

#    __print_totals (stats_totals)
    return stats_totals



def __print_header ():
    logger.info  ("{:>2s} {:>12s} {:>8s} {:>8s} {:>6s} {:>6s} {:>10s} {:>10s} {:>10s}".format('Pr', 'OID', 'SqMtrs', 'Grid', 'Points', 'Plants', 'Time 1', 'Time 2', 'Time ttl'))
    logger.info  ('--------------------')


def __print_stats (polygon, oid, times, mask_size, potential_sites, plantings, stats_totals, my_chunk):
    d_1 = (times[1]-times[0]).seconds + (times[1]-times[0]).microseconds / 1000000.0
    d_2 = (times[2]-times[1]).seconds + (times[2]-times[1]).microseconds / 1000000.0
    d_3 = (times[2]-times[0]).seconds + (times[2]-times[0]).microseconds / 1000000.0
    size = round(polygon.getArea('PLANAR', 'SQUAREMETERS'))
    s = [size, mask_size, potential_sites, plantings, d_1, d_2, d_3]

    logger.info  ("{:>2d} {:>12d} {:>8d} {:>8d} {:>6d} {:>6d} {:>10.3f} {:>10.3f} {:>10.3f}".format(my_chunk, oid, *s))

    for i in range (len(stats_totals)):
        stats_totals[i] = stats_totals[i] + s[i]
   
    
def __print_totals (stats_totals, my_chunk):
    logger.info  ("{:>2d} {:>12s} {:>8d} {:>8d} {:>6d} {:>6d} {:>10.3f} {:>10.3f} {:>10.3f}".format(my_chunk, '', *stats_totals))
    


def __get_mask_dim (polygon, center, tiers):
    max_dim = tiers*2 + 1
    nw_corner = arcpy.Point (center.X - tiers*MIN_DIAMETER, center.Y + tiers*MIN_DIAMETER)
    rows_outside_extent = 2 * math.floor( (nw_corner.Y - polygon.extent.YMax) / MIN_DIAMETER ) 
    cols_outside_extent = 2 * math.floor( (polygon.extent.XMin - nw_corner.X) / MIN_DIAMETER )     
    return max_dim - rows_outside_extent, max_dim - cols_outside_extent  # This does not change the center point
    


def __get_tier_vacancies (center_row, center_col, tier_idx, mask, mask_row_dim, mask_col_dim):
    rows = range(max(0, center_row - tier_idx),  min(center_row + tier_idx+1, mask_row_dim))
    cols = range(max(0, center_col - tier_idx),  min(center_col + tier_idx+1, mask_col_dim))  
    top   = [(rows[0], col)  for col in cols           if mask[rows[0]][col]  == VACANT]
    right = [(row, cols[-1]) for row in rows           if mask[row][cols[-1]] == VACANT]
    bot   = [(rows[-1], col) for col in reversed(cols) if mask[rows[-1]][col] == VACANT]
    left  = [(row, cols[0])  for row in reversed(rows) if mask[row][cols[0]]  == VACANT]
    return top + right + bot + left  

                        
def __mask_to_point (row, col, nw_corner):
    x = nw_corner.X + col*MIN_DIAMETER
    y = nw_corner.Y - row*MIN_DIAMETER
    return arcpy.Point(x,y)


def __point_to_mask (point, nw_corner):
    row = math.floor( (nw_corner.Y - point.Y) / MIN_DIAMETER)
    col = math.floor( (point.X - nw_corner.X) / MIN_DIAMETER)
    return row, col
    

def __get_footprint (row, col, tree_footprint_dim, mask_row_dim, mask_col_dim):
    fp_row_origin = max(row - int((tree_footprint_dim - 1)/2), 0)
    fp_col_origin = max(col - int((tree_footprint_dim - 1)/2), 0)
    fp_row_dim = min(tree_footprint_dim, mask_row_dim-fp_row_origin)
    fp_col_dim = min(tree_footprint_dim, mask_col_dim-fp_col_origin)  
    return fp_row_origin, fp_col_origin, fp_row_dim, fp_col_dim


def __is_footprint_clean (mask, fp_row, fp_col, fp_row_dim, fp_col_dim):    
    for r in range (fp_row, fp_row + fp_row_dim):
        for c in range (fp_col, fp_col + fp_col_dim):
            if mask[r][c] != VACANT and mask[r][c] != OUTSIDE_POLYGON:
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




def __get_mask (mask_row_dim, mask_col_dim, polygon, nw_corner):
    
    # if USE_NUMPY:
    #     mask = np.full( (mask_row_dim, mask_col_dim), VACANT, dtype=np.uint8)
    # elif mask_row_dim * mask_col_dim < 0:
    #     mask = [m[:] for m in [[VACANT] * mask_col_dim] * mask_row_dim] 
    # else: 
        
    ma = __get_mask_algorithm (mask_row_dim, mask_col_dim, polygon)
    if ma == 0:
         mask = [m[:] for m in [[VACANT] * mask_col_dim] * mask_row_dim] 
    else:         
        # Lincoln park take  160 minutes vs 4 minutes with this algorithm    
        FISHNET_POLYLINE_FC = os.path.join('in_memory', 'fishnet_polyline')
        FISHNET_POINT_FC = FISHNET_POLYLINE_FC + '_label' 
        POLYGON_FC = os.path.join('in_memory', 'polygon')
        INTERSECT_FC = os.path.join('in_memory', 'intersect')
        
        x_min = nw_corner.X
        y_min = nw_corner.Y - (mask_row_dim * MIN_DIAMETER)
        x_max = nw_corner.X + (mask_col_dim * MIN_DIAMETER) 
        y_max = nw_corner.Y 
    
        arcpy.env.outputCoordinateSystem = arcpy.Describe(OPENINGS_FC).spatialReference
               
        logger.debug ('Creating fishnet: %i' % (mask_row_dim*mask_col_dim))
        arcpy.management.CreateFishnet(FISHNET_POLYLINE_FC, 
                                       '%f %f' % (x_min, y_min), 
                                       '%f %f' % (x_min, y_max), 
                                       None, 
                                       None, 
                                       mask_row_dim, 
                                       mask_col_dim, 
                                       '%f %f' % (x_max, y_max), 
                                       'LABELS', 
                                       '#', 
                                       'POLYLINE')
    
        # Create feature class with the input polygon
        logger.debug ('Creating feature class')
        arcpy.CreateFeatureclass_management(os.path.dirname(POLYGON_FC), os.path.basename(POLYGON_FC), "POLYGON", OPENINGS_FC)
        
        with arcpy.da.InsertCursor(POLYGON_FC, ['SHAPE@']) as cursor:
            cursor.insertRow([polygon])
    
        # Get the points within the polygon
        logger.debug ('Intersecting')
        arcpy.analysis.PairwiseIntersect([POLYGON_FC, FISHNET_POINT_FC], INTERSECT_FC)
    
        logger.debug ('Writing results')
        # Initialize the mask
        mask = [m[:] for m in [[OUTSIDE_POLYGON] * mask_col_dim] * mask_row_dim]     
        with arcpy.da.SearchCursor(INTERSECT_FC, ['SHAPE@']) as cursor:
            for attrs in cursor:
                row, col = __point_to_mask (attrs[0].centroid, nw_corner)
                mask[row][col] = VACANT
    
        logger.debug ('Deleting temp feature classes')
        arcpy.management.Delete(FISHNET_POLYLINE_FC)
        arcpy.management.Delete(FISHNET_POINT_FC)
        arcpy.management.Delete(POLYGON_FC)
        arcpy.management.Delete(INTERSECT_FC)
    
        logger.debug ('Done')

    return mask


def __get_mask_algorithm (mask_row_dim, mask_col_dim, polygon):
    threshold_1 = 100000
    threshold_2 = 1000000
    
    polygon_sq_meters = round(polygon.getArea('PLANAR', 'SQUAREMETERS')) 
    mask_sq_meters = mask_row_dim * mask_col_dim * MIN_DIAMETER * MIN_DIAMETER

    if mask_sq_meters < threshold_1:
        return 0
    elif mask_sq_meters > threshold_2:
        return 1
    else:
        percent_polygon = (polygon_sq_meters/mask_sq_meters) * 100
        precent_gap = (mask_sq_meters - threshold_1)/(threshold_2 - threshold_1) * 100
        if percent_polygon > precent_gap:
            return 0
        else:
            return 1




































    


if __name__ == '__main__':
     run()
    
    



