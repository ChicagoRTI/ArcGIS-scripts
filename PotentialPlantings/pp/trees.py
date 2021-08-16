# Requires python 3


import arcpy
import os
import math
from collections import OrderedDict

import pp.stats
import pp.common as pp_c


import pp.logger
logger = pp.logger.get('pp_log')


# Can not run in multiprocessing mode from the Spyder console
IS_MP = False

WRITE_TO_DEBUG_MESH_FC = False



DB_DIR = r'C:\Users\dmorrison\AppData\Roaming\ESRI\Desktop10.6\ArcCatalog\ROW Habitat (SDE).SDE'
MESH_FC = os.path.join(DB_DIR, 'PP_TEST_mesh')

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


def run(community_spec):

    community_name, acres, community_id = community_spec
    pp_c.log_info('Siting trees.', community_name)
    
    size_stats = [0,0,0]
    landuse_stats = [0,0,0,0,0,0,0,0,0,0,0]
    public_private_stats = [0,0]
    
    input_fc = pp_c.get_community_fc_name (community_spec[0], pp_c.COMMUNITY_SPACES_FC)
    output_fc = pp_c.get_community_fc_name (community_spec[0], pp_c.COMMUNITY_TREES_FC)
           
    
    if arcpy.Exists(output_fc):
        arcpy.Delete_management(output_fc)
    arcpy.CreateFeatureclass_management(os.path.dirname(output_fc),
                                        os.path.basename(output_fc),
                                        "POINT",
                                        pp_c.TREES_TEMPLATE_FC,
                                        "DISABLED", 
                                        "DISABLED", 
                                        pp_c.TREES_TEMPLATE_FC)

    community_stats_tbl = pp.stats.prepare_community_stats_tbl (community_name, community_id, pp_c.COMMUNITY_TREE_STATS_TBL, pp_c.TREE_STATS_SPEC)

    if WRITE_TO_DEBUG_MESH_FC and not IS_MP:
        arcpy.management.DeleteFeatures(MESH_FC)
        
    logger.debug  ("Calculating points")
    query = "Shape_Area > 2.5"
    with arcpy.da.SearchCursor(input_fc, ['OBJECTID', 'SHAPE@', 'community_id', 'land_use', 'is_public'], query) as cursor:
        for oid, polygon, community, land_use, is_public in cursor:
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
                mesh = __get_mesh (mesh_row_dim, mesh_col_dim, polygon, nw_corner, input_fc)
            
            plant_points = dict()
            
            for tree_category in TREE_CATEGORIES: 
                for tier_idx in range(0, tiers+1):
                    for row, col in __get_tier_vacancies (center_row, center_col, tier_idx, mesh, mesh_row_dim, mesh_col_dim):        
                        fp = __get_footprint (row, col, TREE_FOOTPRINT_DIM[tree_category], mesh_row_dim, mesh_col_dim)
                        if __is_footprint_clean (mesh, *fp):  
                            if is_point_in_polygon (row, col, polygon, nw_corner, mesh, mesh_type,plant_points):
                                __occupy_footprint (mesh, *fp, row, col, tree_category)
                                

            with arcpy.da.InsertCursor(output_fc, ['SHAPE@', 'code', 'p_oid', 'community_id', 'land_use', 'is_public']) as cursor:
                for row,col in plant_points.keys():
                    cursor.insertRow([plant_points[(row,col)], mesh[row][col], oid, community, land_use, is_public])
                    size_stats[mesh[row][col]] = size_stats[mesh[row][col]] + 1
                    landuse_stats[land_use] = landuse_stats[land_use] + 1
                    public_private_stats[is_public] = public_private_stats[is_public] + 1

            if WRITE_TO_DEBUG_MESH_FC and not IS_MP:
                with arcpy.da.InsertCursor(MESH_FC, ['SHAPE@', 'code', 'row', 'col', 'x', 'y', 'dim']) as cursor:
                    for r in range (0, mesh_row_dim):
                        for c in range (0, mesh_col_dim):
                            p = __mesh_to_point (r, c, nw_corner)
                            cursor.insertRow([p, mesh[r][c], r, c, p.X, p.Y, mesh_row_dim])

    pp.stats.update_stats (community_stats_tbl, community_id, size_stats + landuse_stats[1:] + public_private_stats, pp_c.TREE_STATS_SPEC)
#    pp.stats.update_derived_stats(community_id)
                       
    return 



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




def __get_mesh (mesh_row_dim, mesh_col_dim, polygon, nw_corner, input_fc):
         
    # Lincoln park take  160 minutes vs 4 minutes with this algorithm    
    FISHNET_POLYLINE_FC = os.path.join('in_memory', 'fishnet_polyline')
    FISHNET_POINT_FC = FISHNET_POLYLINE_FC + '_label' 
    POLYGON_FC = os.path.join('in_memory', 'polygon')
    INTERSECT_FC = os.path.join('in_memory', 'intersect')
    
    x_min = nw_corner.X
    y_min = nw_corner.Y - (mesh_row_dim * MIN_DIAMETER)
    x_max = nw_corner.X + (mesh_col_dim * MIN_DIAMETER) 
    y_max = nw_corner.Y 

    arcpy.env.outputCoordinateSystem = arcpy.Describe(input_fc).spatialReference
           
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
    arcpy.CreateFeatureclass_management(os.path.dirname(POLYGON_FC), os.path.basename(POLYGON_FC), "POLYGON", input_fc)
    
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


def prepare_fc ():
    if not arcpy.Exists(pp_c.TREES_FC):
        pp_c.log_debug ("Creating '%s'" % pp_c.TREES_FC)
        sr = arcpy.Describe(pp_c.TREES_TEMPLATE_FC).spatialReference
        arcpy.CreateFeatureclass_management(os.path.dirname(pp_c.TREES_FC), os.path.basename(pp_c.TREES_FC), 'POINT', pp_c.TREES_TEMPLATE_FC, "DISABLED", "DISABLED", sr)
        arcpy.management.AssignDomainToField(pp_c.TREES_FC, pp_c.TREES_LANDUSE_COL, pp_c.LANDUSE_DOMAIN_NAME)
        arcpy.management.AssignDomainToField(pp_c.TREES_FC, pp_c.TREES_PUBLIC_PRIVATE_COL, pp_c.PUBLIC_PRIVATE_DOMAIN_NAME)
        arcpy.management.AssignDomainToField(pp_c.TREES_FC, pp_c.TREES_COMMUNITY_COL, pp_c.COMMUNITY_DOMAIN_NAME)    
        arcpy.management.AssignDomainToField(pp_c.TREES_FC, pp_c.TREES_SIZE_COL, pp_c.TREE_SIZE_DOMAIN_NAME) 
        arcpy.management.AddIndex(pp_c.TREES_FC, pp_c.TREES_COMMUNITY_COL, "IDX_Comm", "NON_UNIQUE", "NON_ASCENDING")
        arcpy.management.AddIndex(pp_c.TREES_FC, pp_c.TREES_LANDUSE_COL, "IDX_LandUse", "NON_UNIQUE", "NON_ASCENDING")
        arcpy.management.AddIndex(pp_c.TREES_FC, pp_c.TREES_PUBLIC_PRIVATE_COL, "IDX_PublicPrivate", "NON_UNIQUE", "NON_ASCENDING")
        
    
    

def combine_trees_fcs (community_specs):
    pp_c.log_debug ('Combining trees feature classes')
    
    community_specs = [c for c in community_specs if arcpy.Exists(pp_c.get_community_fc_name(c[0], pp_c.COMMUNITY_TREES_FC))]
    
    communities  = [c[0] for c in community_specs]
    community_fcs = [pp_c.get_community_fc_name (c, pp_c.COMMUNITY_TREES_FC) for c in communities]
    community_ids = [str(c[2]) for c in community_specs]
    
    out_fc = pp_c.TREES_FC   
        
    if not pp_c.IS_SCRATCH_OUTPUT_DATA:
        pp_c.log_debug ('Deleting existing features in combined trees feature class')
        where = "%s IN (%s)" % (pp_c.TREES_COMMUNITY_COL, ','.join(community_ids))
        old_records = arcpy.SelectLayerByAttribute_management(out_fc, 'NEW_SELECTION', where)[0]
        arcpy.management.DeleteFeatures(old_records)
        
    pp_c.log_info ('Write to combined trees feature class')
    arcpy.management.Append(community_fcs, out_fc)
   
    return


