# Requires python 3


import arcpy
import os
import math
import multiprocessing
import timeit
from collections import OrderedDict

from stats import StatsAccumulator
from stats import StatsTimer
import logger as pp_logger
logger = pp_logger.get('pp_log')


# Can not run in multiprocessing mode from the Spyder console
IS_MP = False
MP_NUM_CHUNKS = 8
WRITE_TO_DEBUG_MESH_FC = False

#OPENINGS_FC = 'opening_single'
OPENINGS_FC = 'PP_TEST_openings'
#OPENINGS_FC = 'campus_parks_projected'
#OPENINGS_FC = 'chicago_parks_single_tiny'
#OPENINGS_FC = 'PP_TEST_chicago_parks'
#OPENINGS_FC = 'lincoln_park'
#OPENINGS_FC = 'PP_TEST_pp_spaces_projected_dissolved'
#OPENINGS_FC = 'PP_TEST_pp__swi_spaces_projected'

DB_DIR = r'C:\Users\dmorrison\AppData\Roaming\ESRI\Desktop10.6\ArcCatalog\ROW Habitat (SDE).SDE'
OPENINGS_FC = os.path.join(DB_DIR, OPENINGS_FC)


#OPENINGS_FC = os.path.join(r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\pp\data\test.gdb', OPENINGS_FC)
# #OPENINGS_FC = r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\pp\data\test.gdb\opening_single'
# OPENINGS_FC = r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\pp\data\test.gdb\openings'
# #OPENINGS_FC = r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\pp\data\test.gdb\campus_parks_projected'
# #OPENINGS_FC = r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\pp\data\test.gdb\chicago_parks_single_tiny'
# #OPENINGS_FC = r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\pp\data\test.gdb\chicago_parks'
# #OPENINGS_FC = r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\pp\data\test.gdb\lincoln_park'

#PLANTS_FC = r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\pp\data\test.gdb\plants'
#MESH_FC = r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\pp\data\test.gdb\mesh'

PLANTS_FC = os.path.join(DB_DIR, 'PP_TEST_plants')
MESH_FC = os.path.join(DB_DIR, 'PP_TEST_mesh')
MP_TEMP_OUT_FC_ROOT = os.path.join(arcpy.env.scratchGDB, 'temp_mp_out_fc')

MIN_DIAMETER = 10 * 0.3048
NEG_BUFFER = - (10 * 0.3048)

SMALL = 0
MEDIUM = 1
BIG = 2
VACANT = 100
OUTSIDE_POLYGON = 101
CANOPY = 102

MESH_ALGORITHM_SMALL = 0
MESH_ALGORITHM_BIG = 1

TREE_CATEGORIES = [BIG, MEDIUM, SMALL]

# This is the footprint dimension of each tree catetory. It is a multiple of 
# the MIN_DIAMETER and must be an odd number
TREE_FOOTPRINT_DIM = {SMALL:  1,
                      MEDIUM: 3,
                      BIG:    5}



def run(in_fc, query, out_fc):
    logger.info ("Logging to %s" % pp_logger.LOG_FILE)
    start_time = timeit.default_timer()
    if arcpy.Exists(out_fc):
        arcpy.management.DeleteFeatures(out_fc)
    else:
        arcpy.CreateFeatureclass_management(os.path.dirname(out_fc),
                                            os.path.basename(out_fc),
                                            "POINT",
                                            PLANTS_FC,
                                            "DISABLED", 
                                            "DISABLED", 
                                            PLANTS_FC)
    
    if IS_MP:
        logger.info('Launching ' + str(MP_NUM_CHUNKS) + ' worker processes')
        StatsAccumulator.log_header('Feature statistics')
        
        # Create the set of tuples - each worker process gets one tuple for input        
        mp_run_spec_list = [(MP_NUM_CHUNKS, 
                             i,
                             in_fc,
                             ' AND '.join(filter(None,(query, "((OBJECTID %% %i) - %i = 0)" % (MP_NUM_CHUNKS, i)))),                             
                             MP_TEMP_OUT_FC_ROOT + '_' + str(i)) for i in range(MP_NUM_CHUNKS)]
        for i in range(MP_NUM_CHUNKS):
            chunk_out_fc = mp_run_spec_list[i][4]
            arcpy.Delete_management(chunk_out_fc)
            arcpy.management.CreateFeatureclass(os.path.dirname(chunk_out_fc), os.path.basename(chunk_out_fc), 'POINT', out_fc)
            logger.debug('Created output feature class %s ' % chunk_out_fc)
 
        p = multiprocessing.Pool(MP_NUM_CHUNKS)
        process_stats = p.map(run_mp, mp_run_spec_list)
        p.close()
        
        StatsAccumulator.log_header('Process statistics')
        app_stats = StatsAccumulator()
        for i in range(MP_NUM_CHUNKS):
            process_stats[i].log_accumulation(i)
            app_stats.add(process_stats[i])
        StatsAccumulator.log_header('Totals')
        app_stats.log_accumulation(None)           
            
        # Reassemble the feature classes
        logger.info('Merging output data')
        for i in range(MP_NUM_CHUNKS):
            chunk_out_fc = mp_run_spec_list[i][4]
            logger.debug('Appending ' + chunk_out_fc + ' to ' + out_fc)
            arcpy.Append_management(chunk_out_fc, out_fc)
            arcpy.Delete_management(chunk_out_fc)
            
    else:
        StatsAccumulator.log_header('Feature statistics')
        process_stats = run_mp ( (1, 0, in_fc, query, out_fc) )
        StatsAccumulator.log_header('Totals')
        process_stats.log_accumulation(0)

    
    logger.info("Program Executed in %s seconds" % str(round(timeit.default_timer()-start_time)))


def run_mp (run_spec):    
    logger.debug ("Input: %s" % (str(run_spec)))
    chunks, my_chunk, input_fc, query, output_fc = run_spec
                              
    if WRITE_TO_DEBUG_MESH_FC and not IS_MP:
        arcpy.management.DeleteFeatures(MESH_FC)
        
    process_stats = StatsAccumulator()
        
    logger.debug  ("Calculating points")
    with arcpy.da.SearchCursor(input_fc, ['OBJECTID', 'SHAPE@'], query) as cursor:
        for attrs in cursor:
            feature_stats = StatsTimer()
            oid = attrs[0]
            polygon = attrs[1]
            x_min, y_min, x_max, y_max = polygon.extent.XMin, polygon.extent.YMin, polygon.extent.XMax, polygon.extent.YMax 

            center = arcpy.Point((x_min+x_max)/2, (y_min+y_max)/2)
            tiers = math.ceil(max((x_max-x_min)/2, (y_max-y_min)/2) / MIN_DIAMETER)
            
            # The mesh orgin is the NW corner and indexed row major as  [row][col]
            mesh_row_dim, mesh_col_dim = __get_mesh_dim (polygon, center, tiers)
            nw_corner = arcpy.Point (center.X - (mesh_col_dim*MIN_DIAMETER)/2, center.Y + (mesh_row_dim*MIN_DIAMETER)/2)            
            center_row, center_col = __point_to_mesh (center, nw_corner)

            mesh_type = __get_mesh_algorithm (mesh_row_dim, mesh_col_dim, polygon)
            if mesh_type == MESH_ALGORITHM_SMALL:
                mesh = [m[:] for m in [[VACANT] * mesh_col_dim] * mesh_row_dim] 
            elif mesh_type == MESH_ALGORITHM_BIG: 
                mesh = __get_mesh (mesh_row_dim, mesh_col_dim, polygon, nw_corner)
            feature_stats.record(StatsTimer.MESH_CREATE_END)
            
            plant_points = dict()
            
            for tree_category in TREE_CATEGORIES: 
                for tier_idx in range(0, tiers+1):
                    for row, col in __get_tier_vacancies (center_row, center_col, tier_idx, mesh, mesh_row_dim, mesh_col_dim):        
                        fp = __get_footprint (row, col, TREE_FOOTPRINT_DIM[tree_category], mesh_row_dim, mesh_col_dim)
                        if __is_footprint_clean (mesh, *fp):  
                            if is_point_in_polygon (row, col, polygon, nw_corner, mesh, mesh_type,plant_points):
                                __occupy_footprint (mesh, *fp, row, col, tree_category)
            feature_stats.record(StatsTimer.FIND_SITES_END)

            with arcpy.da.InsertCursor(output_fc, ['SHAPE@', 'code']) as cursor:
                for row,col in plant_points.keys():
                    cursor.insertRow([plant_points[(row,col)], mesh[row][col]])
            feature_stats.record(StatsTimer.WRITE_SITES_END)
            process_stats.accumulate (feature_stats, my_chunk, oid, mesh_row_dim * mesh_col_dim * MIN_DIAMETER * MIN_DIAMETER * 0.000247105, polygon.getArea('PLANAR', 'ACRES'), len(plant_points))


            if WRITE_TO_DEBUG_MESH_FC and not IS_MP:
                with arcpy.da.InsertCursor(MESH_FC, ['SHAPE@', 'code', 'row', 'col', 'x', 'y', 'dim']) as cursor:
                    for r in range (0, mesh_row_dim):
                        for c in range (0, mesh_col_dim):
                            p = __mesh_to_point (r, c, nw_corner)
                            cursor.insertRow([p, mesh[r][c], r, c, p.X, p.Y, mesh_row_dim])

    return process_stats



def __get_mesh_dim (polygon, center, tiers):
    max_dim = tiers*2 + 1
    nw_corner = arcpy.Point (center.X - tiers*MIN_DIAMETER, center.Y + tiers*MIN_DIAMETER)
    rows_outside_extent = 2 * math.floor( (nw_corner.Y - polygon.extent.YMax) / MIN_DIAMETER ) 
    cols_outside_extent = 2 * math.floor( (polygon.extent.XMin - nw_corner.X) / MIN_DIAMETER )     
    return max_dim - rows_outside_extent, max_dim - cols_outside_extent  # This does not change the center point
    


def __get_tier_vacancies (center_row, center_col, tier_idx, mesh, mesh_row_dim, mesh_col_dim):
    rows = range(max(0, center_row - tier_idx),  min(center_row + tier_idx+1, mesh_row_dim))
    cols = range(max(0, center_col - tier_idx),  min(center_col + tier_idx+1, mesh_col_dim))  
    top   = [(rows[0], col)  for col in cols           if mesh[rows[0]][col]  == VACANT]
    right = [(row, cols[-1]) for row in rows           if mesh[row][cols[-1]] == VACANT]
    bot   = [(rows[-1], col) for col in reversed(cols) if mesh[rows[-1]][col] == VACANT]
    left  = [(row, cols[0])  for row in reversed(rows) if mesh[row][cols[0]]  == VACANT]
    return list(OrderedDict.fromkeys(top + right + bot + left))

                        
def __mesh_to_point (row, col, nw_corner):
    x = nw_corner.X + col*MIN_DIAMETER + .5*MIN_DIAMETER
    y = nw_corner.Y - row*MIN_DIAMETER - .5*MIN_DIAMETER
    return arcpy.Point(x,y)


def __point_to_mesh (point, nw_corner):
    row = math.floor( (nw_corner.Y - point.Y) / MIN_DIAMETER)
    col = math.floor( (point.X - nw_corner.X) / MIN_DIAMETER)
    return row, col
    

def __get_footprint (row, col, tree_footprint_dim, mesh_row_dim, mesh_col_dim):
    fp_row_origin = max(row - int((tree_footprint_dim - 1)/2), 0)
    fp_col_origin = max(col - int((tree_footprint_dim - 1)/2), 0)
    fp_row_dim = min(tree_footprint_dim, mesh_row_dim-fp_row_origin)
    fp_col_dim = min(tree_footprint_dim, mesh_col_dim-fp_col_origin)  
    return fp_row_origin, fp_col_origin, fp_row_dim, fp_col_dim


def __is_footprint_clean (mesh, fp_row, fp_col, fp_row_dim, fp_col_dim):    
    for r in range (fp_row, fp_row + fp_row_dim):
        for c in range (fp_col, fp_col + fp_col_dim):
            if mesh[r][c] != VACANT and mesh[r][c] != OUTSIDE_POLYGON:
                return False
    return True


def is_point_in_polygon (row, col, polygon, nw_corner, mesh, mesh_type, plant_points):
    if mesh[row][col] != VACANT:
        raise Exception ("Not vacant")
        
    if mesh_type == MESH_ALGORITHM_BIG:
            plant_points[(row,col)] = __mesh_to_point (row, col, nw_corner)
            return True
    else:
        point = __mesh_to_point (row, col, nw_corner)
        if point.within(polygon):
            plant_points[(row,col)] = point
            return True
        else:
            mesh[row][col] = OUTSIDE_POLYGON
            return False


def __occupy_footprint (mesh, fp_row, fp_col, fp_row_dim, fp_col_dim, planting_row, planting_col, tree_category):
    for r in range (fp_row, fp_row + fp_row_dim):
        for c in range (fp_col, fp_col + fp_col_dim):
            mesh[r][c] = CANOPY
    mesh[planting_row][planting_col] = tree_category




def __get_mesh (mesh_row_dim, mesh_col_dim, polygon, nw_corner):
         
    # Lincoln park take  160 minutes vs 4 minutes with this algorithm    
    FISHNET_POLYLINE_FC = os.path.join('in_memory', 'fishnet_polyline')
    FISHNET_POINT_FC = FISHNET_POLYLINE_FC + '_label' 
    POLYGON_FC = os.path.join('in_memory', 'polygon')
    INTERSECT_FC = os.path.join('in_memory', 'intersect')
    
    x_min = nw_corner.X
    y_min = nw_corner.Y - (mesh_row_dim * MIN_DIAMETER)
    x_max = nw_corner.X + (mesh_col_dim * MIN_DIAMETER) 
    y_max = nw_corner.Y 

    arcpy.env.outputCoordinateSystem = arcpy.Describe(OPENINGS_FC).spatialReference
           
    arcpy.management.CreateFishnet(FISHNET_POLYLINE_FC, 
                                   '%f %f' % (x_min, y_min), 
                                   '%f %f' % (x_min, y_max), 
                                   None, 
                                   None, 
                                   mesh_row_dim, 
                                   mesh_col_dim, 
                                   '%f %f' % (x_max, y_max), 
                                   'LABELS', 
                                   '#', 
                                   'POLYLINE')

    # Create feature class with the input polygon
    arcpy.CreateFeatureclass_management(os.path.dirname(POLYGON_FC), os.path.basename(POLYGON_FC), "POLYGON", OPENINGS_FC)
    
    with arcpy.da.InsertCursor(POLYGON_FC, ['SHAPE@']) as cursor:
        cursor.insertRow([polygon])

    # Get the points within the polygon
    arcpy.analysis.PairwiseIntersect([POLYGON_FC, FISHNET_POINT_FC], INTERSECT_FC)

    # Initialize the mesh
    mesh = [m[:] for m in [[OUTSIDE_POLYGON] * mesh_col_dim] * mesh_row_dim]     
    with arcpy.da.SearchCursor(INTERSECT_FC, ['SHAPE@']) as cursor:
        for attrs in cursor:
            row, col = __point_to_mesh (attrs[0].centroid, nw_corner)
            mesh[row][col] = VACANT

    arcpy.management.Delete(FISHNET_POLYLINE_FC)
    arcpy.management.Delete(FISHNET_POINT_FC)
    arcpy.management.Delete(POLYGON_FC)
    arcpy.management.Delete(INTERSECT_FC)

    return mesh


def __get_mesh_algorithm (mesh_row_dim, mesh_col_dim, polygon):
    threshold_1 = 100000
    threshold_2 = 1000000
    
    polygon_sq_meters = round(polygon.getArea('PLANAR', 'SQUAREMETERS')) 
    mesh_sq_meters = mesh_row_dim * mesh_col_dim * MIN_DIAMETER * MIN_DIAMETER

    if mesh_sq_meters < threshold_1:
        return MESH_ALGORITHM_SMALL
    elif mesh_sq_meters > threshold_2:
        return MESH_ALGORITHM_BIG
    else:
        percent_polygon = (polygon_sq_meters/mesh_sq_meters) * 100
        precent_gap = (mesh_sq_meters - threshold_1)/(threshold_2 - threshold_1) * 100
        if percent_polygon > precent_gap:
            return MESH_ALGORITHM_SMALL
        else:
            return MESH_ALGORITHM_BIG


  


if __name__ == '__main__':
     run(OPENINGS_FC, None, PLANTS_FC)
    
    



