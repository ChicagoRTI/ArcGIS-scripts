# Requires python 3


import arcpy
import os
import math
import numpy as np


openings_fc = r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\data\test.gdb\openings'
neg_buffered_fc = r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\data\test.gdb\neg_buffered'
matrix_fc = r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\data\test.gdb\matrix'
mask_fc = r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\data\test.gdb\mask'
diameter = 30 * 0.3048
neg_buffer = - (10 * 0.3048)




 # Assumes no multpart polygons
 # Negative buffer might cause polygon to disappear
 # Overlapping polygons is a problem


# def run ():
                                   
#     arcpy.management.Delete(matrix_fc)
#     arcpy.CreateFeatureclass_management(os.path.dirname(matrix_fc),
#                                     os.path.basename(matrix_fc),
#                                     "POINT",
#                                     spatial_reference=arcpy.Describe(openings_fc).SpatialReference)


#     print ("Negative buffering")    
#     arcpy.management.Delete(neg_buffered_fc)
#     arcpy.GraphicBuffer_analysis(openings_fc, neg_buffered_fc, neg_buffer)
    
#     points_checked = 0
    
#     print ("Calculating points")    
#     with arcpy.da.SearchCursor(neg_buffered_fc, ['OBJECTID', 'SHAPE@']) as cursor:
#         for attrs in cursor:
#             polygon = attrs[1]
#             x_min, y_min, x_max, y_max = polygon.extent.XMin, polygon.extent.YMin, polygon.extent.XMax, polygon.extent.YMax, 
#             center = arcpy.Point((x_min+x_max)/2, (y_min+y_max)/2)
#             points = []

#             tiers = math.ceil(max((x_max-x_min)/2, (y_max-y_min)/2) / diameter)
#             for tier in range(0, tiers+1):
#                 bot  = [(x,-tier)  for x in range (-tier, tier+1)]
#                 top  = [(x, tier)  for x in range (-tier, tier+1)]
#                 left = [(-tier, y) for y in range (-tier, tier+1)]
#                 right= [(tier, y)  for y in range (-tier, tier+1)]
#                 tier_coordinates = set(bot + top + left + right)
#                 for tier_coordinate in tier_coordinates:
#                     x = center.X + (tier_coordinate[0] * diameter)
#                     y = center.Y + (tier_coordinate[1] * diameter)
#                     if x >= x_min and x <= x_max and y >= y_min and y <= y_max:
#                         points_checked = points_checked + 1
#                         if arcpy.Point(x,y).within(polygon):
#                             points.append ( (x,y) )                   

#             with arcpy.da.InsertCursor(matrix_fc, ['SHAPE@']) as cursor:
#                 for point in points:
#                     cursor.insertRow([arcpy.Point(point[0], point[1])])


#     print ("%i points checked" % points_checked)    

OPEN = -1
SMALL = 0
MEDIUM = 1
BIG = 2
BEYOND_EXTENT = 100
OUTSIDE_POLYGON = 101


def run ():
                                   
    arcpy.management.DeleteFeatures(matrix_fc)
    arcpy.management.DeleteFeatures(mask_fc)

    print ("Negative buffering")    
    arcpy.management.Delete(neg_buffered_fc)
    arcpy.GraphicBuffer_analysis(openings_fc, neg_buffered_fc, neg_buffer)
    
    points_checked = 0
    
    print ("Calculating points")    
    with arcpy.da.SearchCursor(neg_buffered_fc, ['OBJECTID', 'SHAPE@']) as cursor:
        for attrs in cursor:
            polygon = attrs[1]
            x_min, y_min, x_max, y_max = polygon.extent.XMin, polygon.extent.YMin, polygon.extent.XMax, polygon.extent.YMax, 

            center = arcpy.Point((x_min+x_max)/2, (y_min+y_max)/2)
            tiers = math.ceil(max((x_max-x_min)/2, (y_max-y_min)/2) / diameter)
            



            nw_corner = arcpy.Point (center.X - tiers*diameter, center.Y + tiers*diameter)
            
            center_row = tiers
            center_col = tiers
            
            # The mask orgin is the NW corner and indexed as  [row][col]
            mask_dim = tiers*2 + 1
            mask = np.full( (mask_dim, mask_dim), OPEN, dtype=int)
            plant_heres = list()

            for tree_size in [BIG, MEDIUM, SMALL]:
            
                for tier in range(0, tiers+1):
                    top  = [(center_row - tier, col)  for col in range (center_row - tier, center_row + tier + 1)]
                    right= [(row, center_col + tier)  for row in range (center_col - tier, center_col + tier + 1)]
                    bot  = [(center_row + tier, col)  for col in reversed(range (center_row - tier, center_row + tier + 1))]
                    left = [(row, center_col - tier)  for row in reversed(range (center_col - tier, center_col + tier + 1))]
                    for tier_coordinate in top + right + bot + left:
    
                        row = tier_coordinate[0]
                        col = tier_coordinate[1]
                        
                        if mask[row, col] == OPEN:                                                  
                            # Is the point outside of the polygon extent?
                            tier_point = __mask_to_point (row, col, nw_corner)
                            if tier_point.X >= x_min and tier_point.X <= x_max and tier_point.Y >= y_min and tier_point.Y <= y_max:
        
                                fp_row, fp_col, fp_row_dim, fp_col_dim = __get_footprint (row, col, tree_size, mask_dim)
    #                           print ("(%i,%i): %i x %i" % (fp_row, fp_col, fp_row_dim, fp_col_dim))                        
                                if __is_footprint_clean (mask, fp_row, fp_col, fp_row_dim, fp_col_dim):                        
                                    if tier_point.within(polygon):
                                        __occupy_footprint (mask, fp_row, fp_col, fp_row_dim, fp_col_dim, tree_size)
                                        plant_heres.append ( (tier_point, tree_size) )  
                                    else:
                                        mask[row][col] = OUTSIDE_POLYGON
                            else:
                                mask[row][col] = BEYOND_EXTENT

                            


            with arcpy.da.InsertCursor(matrix_fc, ['SHAPE@', 'code']) as cursor:
                for plant_here in plant_heres:
                    cursor.insertRow([plant_here[0], plant_here[1]])

            with arcpy.da.InsertCursor(mask_fc, ['SHAPE@', 'code']) as cursor:
                for r in range (0, mask_dim):
                    for c in range (0, mask_dim):
                        cursor.insertRow([__mask_to_point (r, c, nw_corner), mask[r][c]])



    #print ("%i points checked" % points_checked)    


def __mask_to_point (row, col, nw_corner):
    x = nw_corner.X + row*diameter
    y = nw_corner.Y - col*diameter
    return arcpy.Point(x,y)
    
def __is_point_clean (mask, row, col):
    return mask[row][col] == OPEN


def __get_footprint (row, col, size, mask_dim):
    fp_row_origin = max(row - size,0)
    fp_col_origin = max(col - size,0)
    fp_row_dim = min(2*size + 1, mask_dim-row)
    fp_col_dim = min(2*size + 1, mask_dim-col)
    
    return fp_row_origin, fp_col_origin, fp_row_dim, fp_col_dim


def __is_footprint_clean (mask, fp_row, fp_col, fp_row_dim, fp_col_dim):    
    for r in range (fp_row, fp_row + fp_row_dim):
        for c in range (fp_col, fp_col + fp_col_dim):
            if mask[r][c] != OPEN:
                return False
    return True


def __occupy_footprint (mask, fp_row, fp_col, fp_row_dim, fp_col_dim, tree_size):
    for r in range (fp_row, fp_row + fp_row_dim):
        for c in range (fp_col, fp_col + fp_col_dim):
            mask[r][c] = tree_size


if __name__ == '__main__':
     run()
    
    



