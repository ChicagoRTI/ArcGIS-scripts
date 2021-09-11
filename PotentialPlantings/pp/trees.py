# Requires python 3


import arcpy
import os
import math
from collections import OrderedDict

import pp.stats
import pp.common as pp_c


import pp.logger
logger = pp.logger.get('pp_log')


WRITE_TO_DEBUG_MESH_FC = False

DB_DIR = r'C:\Users\dmorrison\AppData\Roaming\ESRI\Desktop10.6\ArcCatalog\ROW Habitat (SDE).SDE'
MESH_FC = os.path.join(DB_DIR, 'PP_TEST_mesh')


MESH_ALGORITHM_SMALL = 0
MESH_ALGORITHM_BIG = 1

MIN_DIAMETER = pp_c.MIN_DIAMETER
SMALL = pp_c.SMALL
MEDIUM = pp_c.MEDIUM
BIG = pp_c.BIG
VACANT = pp_c.VACANT
OUTSIDE_POLYGON = pp_c.OUTSIDE_POLYGON
CANOPY = pp_c.CANOPY
TREE_CATEGORIES = pp_c.TREE_CATEGORIES
TREE_FOOTPRINT_DIM = pp_c.TREE_FOOTPRINT_DIM
TREE_RADIUS = pp_c.TREE_RADIUS


def site_trees (community_spec):

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
    
    
    intermediate_output_gdb =  pp_c.prepare_intermediate_output_gdb (pp_c.USE_IN_MEM)
    intermediate_trees = pp_c.get_intermediate_name (intermediate_output_gdb, 'trees_int', community_id, pp_c.USE_IN_MEM)
    intermediate_trees_lu = pp_c.get_intermediate_name (intermediate_output_gdb, 'tlu_int', community_id, pp_c.USE_IN_MEM)
    intermediate_trees_lu_public = pp_c.get_intermediate_name (intermediate_output_gdb, 'tlpub_int', community_id, pp_c.USE_IN_MEM)

    arcpy.CreateFeatureclass_management(os.path.dirname(intermediate_trees),
                                        os.path.basename(intermediate_trees),
                                        "POINT",
                                        pp_c.TREES_TEMPLATE_FC,
                                        "DISABLED", 
                                        "DISABLED", 
                                        pp_c.TREES_TEMPLATE_FC)
    arcpy.DeleteField_management(intermediate_trees, ['land_use'])
    
    community_stats_tbl = pp.stats.prepare_community_stats_tbl (community_name, community_id, pp_c.COMMUNITY_TREE_STATS_TBL, pp_c.TREE_STATS_SPEC)

    if WRITE_TO_DEBUG_MESH_FC:
        arcpy.management.DeleteFeatures(MESH_FC)
        
    pp_c.log_info  ("Calculating points", community_name)
    query = "Shape_Area > 2.5"
    with arcpy.da.SearchCursor(input_fc, ['OBJECTID', 'SHAPE@', 'community_id'], query) as cursor:
        for oid, polygon, community in cursor:
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
                                

            with arcpy.da.InsertCursor(intermediate_trees, ['SHAPE@', 'code', 'p_oid', 'community_id']) as cursor:
                for row,col in plant_points.keys():
                    cursor.insertRow([plant_points[(row,col)], mesh[row][col], oid, community])

            if WRITE_TO_DEBUG_MESH_FC:
                with arcpy.da.InsertCursor(MESH_FC, ['SHAPE@', 'code', 'row', 'col', 'x', 'y', 'dim']) as cursor:
                    for r in range (0, mesh_row_dim):
                        for c in range (0, mesh_col_dim):
                            p = __mesh_to_point (r, c, nw_corner)
                            cursor.insertRow([p, mesh[r][c], r, c, p.X, p.Y, mesh_row_dim])


    pp_c.log_debug ('Identify land use', community_name)        
    arcpy.Identity_analysis(intermediate_trees, pp_c.LAND_USE_2015, intermediate_trees_lu, "ALL", "", "NO_RELATIONSHIPS")
    pp_c.delete( [intermediate_trees] )
    arcpy.management.AlterField(intermediate_trees_lu, 'LandUse', 'land_use')

    pp_c.log_debug ('Identify public land', community_name)        
    arcpy.Identity_analysis(intermediate_trees_lu, pp_c.PUBLIC_LAND, intermediate_trees_lu_public, "ONLY_FID", "", "NO_RELATIONSHIPS")
    pp_c.delete( [intermediate_trees_lu] )

    pp_c.log_debug ('Populate the "is_public" field', community_name)   
    arcpy.management.CalculateField(intermediate_trees_lu_public, pp_c.SPACES_PUBLIC_PRIVATE_COL, "is_public(!FID_%s!)" % (os.path.basename(pp_c.PUBLIC_LAND)), "PYTHON3", r"""def is_public (fid):
        if fid == -1:
            return 0
        else:
            return 1""", "SHORT")

    # __downsize (intermediate_output_gdb, intermediate_trees_lu_public, community_name, community_id)

    pp_c.log_debug ('Find overlaps', community_name)   
    overlap_oids = __find_overlaps (intermediate_output_gdb, intermediate_trees_lu_public, community_name, community_id)  
        
    pp_c.log_debug ('Collecting tree statistics, fixing bad land uses, and downsizing overlaps', community_name)  
    big_to_medium, medium_to_small, small = 0,0,0
    with arcpy.da.UpdateCursor(intermediate_trees_lu_public, ['objectid', 'code', 'land_use', 'is_public', ]) as cursor:    
        for oid, tree_size, land_use, is_public in cursor:
            if land_use not in pp_c.LANDUSE_DOMAIN.values():
                # Fix up unrecognized land use 
                land_use = pp_c.LANDUSE_DOMAIN['Other']
                cursor.updateRow([oid, tree_size, land_use, is_public])
            if oid in overlap_oids:
                if tree_size == BIG:
                    tree_size = MEDIUM
                    big_to_medium = big_to_medium + 1
                    cursor.updateRow([oid, tree_size, land_use, is_public])
                elif tree_size == MEDIUM:
                    tree_size = SMALL
                    medium_to_small = medium_to_small + 1
                    cursor.updateRow([oid, tree_size, land_use, is_public]) 
                else:
                    tree_size = SMALL
                    small = small + 1
            size_stats[tree_size] = size_stats[tree_size] + 1
            landuse_stats[land_use] = landuse_stats[land_use] + 1
            public_private_stats[is_public] = public_private_stats[is_public] + 1
    pp_c.log_debug ("Updated feature class with new sizes. L->M=%i, M->S=%i, S=%i" % (big_to_medium, medium_to_small, small), community_name)  
        

    pp_c.log_debug ("Writing points to '%s'" % output_fc, community_name)            
    arcpy.management.Append(intermediate_trees_lu_public, output_fc, "NO_TEST")
    pp_c.delete ([intermediate_trees_lu_public])

    pp.stats.update_stats (community_stats_tbl, community_id, size_stats + landuse_stats[1:] + public_private_stats, pp_c.TREE_STATS_SPEC)

            
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


# def __get_mesh_algorithm (mesh_row_dim, mesh_col_dim, polygon):
#     threshold_1 = 100000
#     threshold_2 = 1000000
    
#     polygon_sq_meters = round(polygon.getArea('PLANAR', 'SQUAREMETERS')) 
#     mesh_sq_meters = mesh_row_dim * mesh_col_dim * MIN_DIAMETER * MIN_DIAMETER

#     if mesh_sq_meters < threshold_1:
#         return MESH_ALGORITHM_SMALL
#     elif mesh_sq_meters > threshold_2:
#         return MESH_ALGORITHM_BIG
#     else:
#         percent_polygon = (polygon_sq_meters/mesh_sq_meters) * 100
#         precent_gap = (mesh_sq_meters - threshold_1)/(threshold_2 - threshold_1) * 100
#         if percent_polygon > precent_gap:
#             return MESH_ALGORITHM_SMALL
#         else:
#             return MESH_ALGORITHM_BIG



def __get_mesh_algorithm (mesh_row_dim, mesh_col_dim, polygon):
    threshold_cells_1 = 10000
    threshold_cells_2 = 100000
    
    mesh_cells = mesh_row_dim * mesh_col_dim

    if mesh_cells < threshold_cells_1:
        return MESH_ALGORITHM_SMALL
    elif mesh_cells > threshold_cells_2:
        pp_c.log_debug ('Big Mesh1 %i cells' % (mesh_cells)) 
        return MESH_ALGORITHM_BIG
    else:
        polygon_cells = round(polygon.getArea('PLANAR', 'SQUAREMETERS')/(MIN_DIAMETER * MIN_DIAMETER)) 
        percent_polygon = (polygon_cells/mesh_cells) * 100
        precent_gap = (mesh_cells - threshold_cells_1)/(threshold_cells_2 - threshold_cells_1) * 100
        if percent_polygon > precent_gap:
            return MESH_ALGORITHM_SMALL
        else:
            pp_c.log_debug ('Big Mesh2 %i cells, %i percent polygon, %i percent gap' % (mesh_cells, int(percent_polygon), int(precent_gap))) 
            return MESH_ALGORITHM_BIG



def __find_overlaps (intermediate_output_gdb, in_fc, community_name, community_id):
    trees_buffered = pp_c.get_intermediate_name (intermediate_output_gdb, 'tbuffered_int', community_id, pp_c.USE_IN_MEM)
    trees_overlapped = pp_c.get_intermediate_name (intermediate_output_gdb, 'tolap_int', community_id, pp_c.USE_IN_MEM)
    
    pp_c.log_debug ('Populate the "radius" field', community_name)   
    arcpy.management.CalculateField(in_fc, 'radius', "get_radius(!code!)", "PYTHON3", r"""def get_radius (code):
        if code == 0:
            return %1.2f
        elif code == 1:
            return %1.2f
        else:
            return %1.2f""" % (TREE_RADIUS[SMALL], TREE_RADIUS[MEDIUM], TREE_RADIUS[BIG]), "FLOAT")

    pp_c.log_debug ('Buffer the points', community_name)   
    arcpy.analysis.Buffer(in_fc, trees_buffered, "radius", "FULL", "ROUND", "NONE", None, "PLANAR")

    pp_c.log_debug ('Find overlapping trees', community_name)
    arcpy.analysis.Intersect(trees_buffered, trees_overlapped, "ONLY_FID", None, "INPUT")    
    pp_c.delete( [trees_buffered] )
    overlap_oids = []    
    with arcpy.da.SearchCursor(trees_overlapped, ['FID_%s' % (os.path.basename(trees_buffered))]) as cursor:
        for oid in cursor:
            overlap_oids.append(oid[0])
    pp_c.delete( [trees_overlapped] )            
    return overlap_oids




def prepare_fc ():
    if not arcpy.Exists(pp_c.TREES_FC):
        pp_c.log_debug ("Creating '%s'" % pp_c.TREES_FC)
        sr = arcpy.Describe(pp_c.TREES_TEMPLATE_FC).spatialReference
        arcpy.CreateFeatureclass_management(os.path.dirname(pp_c.TREES_FC), os.path.basename(pp_c.TREES_FC), 'POINT', pp_c.TREES_TEMPLATE_FC, "DISABLED", "DISABLED", sr)
        arcpy.management.AssignDomainToField(pp_c.TREES_FC, pp_c.TREES_LANDUSE_COL, pp_c.LANDUSE_DOMAIN_NAME)
        arcpy.management.AssignDomainToField(pp_c.TREES_FC, pp_c.TREES_PUBLIC_PRIVATE_COL, pp_c.PUBLIC_PRIVATE_DOMAIN_NAME)
        arcpy.management.AssignDomainToField(pp_c.TREES_FC, pp_c.TREES_COMMUNITY_COL, pp_c.COMMUNITY_DOMAIN_NAME)    
        arcpy.management.AssignDomainToField(pp_c.TREES_FC, pp_c.TREES_SIZE_COL, pp_c.TREE_SIZE_DOMAIN_NAME) 
        
        

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

    if len(communities) > 10:
        pp_c.remove_indexes (out_fc, pp_c.TREES_INDEX_SPEC)        
        
    pp_c.log_info ('Write to combined trees feature class')
    arcpy.management.Append(community_fcs, out_fc)
    
    if len(communities) > 10:
        pp_c.add_indexes (out_fc, pp_c.TREES_INDEX_SPEC) 
   
    return


