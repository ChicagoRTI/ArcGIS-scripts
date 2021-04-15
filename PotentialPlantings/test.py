# Requires python 3


import arcpy
import os
import math
import numpy as np


#openings_fc = r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\data\test.gdb\opening_single'
openings_fc = r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\data\test.gdb\openings'
neg_buffered_fc = r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\data\test.gdb\neg_buffered'
matrix_fc = r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\data\test.gdb\matrix'
mask_fc = r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\data\test.gdb\mask'
diameter = 30 * 0.3048
neg_buffer = - (10 * 0.3048)


 

OPEN = -1
SMALL = 0
MEDIUM = 1
BIG = 2
BEYOND_EXTENT = 100
OUTSIDE_POLYGON = 101
CANOPY = 102


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
            x_min, y_min, x_max, y_max = polygon.extent.XMin, polygon.extent.YMin, polygon.extent.XMax, polygon.extent.YMax 

            center = arcpy.Point((x_min+x_max)/2, (y_min+y_max)/2)
            tiers = math.ceil(max((x_max-x_min)/2, (y_max-y_min)/2) / diameter)
            

            nw_corner = arcpy.Point (center.X - tiers*diameter, center.Y + tiers*diameter)
            
            center_row = tiers
            center_col = tiers
            
            # The mask orgin is the NW corner and indexed as  [row][col]
            mask_dim = tiers*2 + 1
            mask = np.full( (mask_dim, mask_dim), OPEN, dtype=int)
            __trim_mask (mask, mask_dim, nw_corner, polygon)
                         
            plant_heres = list()
            
            
            for tree_size in [BIG, MEDIUM, SMALL]:
            
                for tier in range(0, tiers+1):
                    top  = [(center_row - tier, col)  for col in range (center_row - tier, center_row + tier + 1)]
                    right= [(row, center_col + tier)  for row in range (center_col - tier, center_col + tier + 1)]
                    bot  = [(center_row + tier, col)  for col in reversed(range (center_row - tier, center_row + tier + 1))]
                    left = [(row, center_col - tier)  for row in reversed(range (center_col - tier, center_col + tier + 1))]
#                    for row, col in top + right + bot + left:
                    for row, col in [(r,c) for (r,c)in top + right + bot + left if mask[r, c] == OPEN]:
#                        if mask[row, col] == OPEN:                                                  
        
                        fp_row, fp_col, fp_row_dim, fp_col_dim = __get_footprint (row, col, tree_size, mask_dim)
#                       print ("(%i,%i): %i x %i" % (fp_row, fp_col, fp_row_dim, fp_col_dim))                        
                        if __is_footprint_clean (mask, fp_row, fp_col, fp_row_dim, fp_col_dim):                        
                            __occupy_footprint (mask, fp_row, fp_col, fp_row_dim, fp_col_dim, row, col, tree_size)
                            plant_heres.append ( (__mask_to_point (row, col, nw_corner), tree_size) )  


            with arcpy.da.InsertCursor(matrix_fc, ['SHAPE@', 'code']) as cursor:
                for plant_here in plant_heres:
                    cursor.insertRow([plant_here[0], plant_here[1]])

            with arcpy.da.InsertCursor(mask_fc, ['SHAPE@', 'code', 'row', 'col', 'x', 'y', 'dim']) as cursor:
                for r in range (0, mask_dim):
                    for c in range (0, mask_dim):
                        p = __mask_to_point (r, c, nw_corner)
                        cursor.insertRow([__mask_to_point (r, c, nw_corner), mask[r][c], r, c, p.X, p.Y, mask_dim])



    #print ("%i points checked" % points_checked)    


def __trim_mask (mask, mask_dim, nw_corner, polygon):
    x_min, y_min, x_max, y_max = polygon.extent.XMin, polygon.extent.YMin, polygon.extent.XMax, polygon.extent.YMax, 
    for r in range (0, mask_dim):
        for c in range (0, mask_dim):
            point = __mask_to_point (r, c, nw_corner)
            if point.X < x_min or point.X > x_max or point.Y < y_min or point.Y > y_max or not point.within(polygon):
                mask[r][c] = OUTSIDE_POLYGON
            
    
def __mask_to_point (row, col, nw_corner):
    x = nw_corner.X + col*diameter
    y = nw_corner.Y - row*diameter
    return arcpy.Point(x,y)
    
def __is_point_clean (mask, row, col):
    return mask[row][col] == OPEN


def __get_footprint (row, col, tree_size, mask_dim):
    if row == 14 and col == 14 and mask_dim == 17:
        x=1
        pass
    
    fp_row_origin = max(row - tree_size,0)
    fp_col_origin = max(col - tree_size,0)
    fp_row_dim = min(2*tree_size + 1, mask_dim-fp_row_origin)
    fp_col_dim = min(2*tree_size + 1, mask_dim-fp_col_origin)
    
    return fp_row_origin, fp_col_origin, fp_row_dim, fp_col_dim


def __is_footprint_clean (mask, fp_row, fp_col, fp_row_dim, fp_col_dim):    
    for r in range (fp_row, fp_row + fp_row_dim):
        for c in range (fp_col, fp_col + fp_col_dim):
            if mask[r][c] != OPEN:
                return False
    return True


def __occupy_footprint (mask, fp_row, fp_col, fp_row_dim, fp_col_dim, planting_row, planting_col, tree_size):
    for r in range (fp_row, fp_row + fp_row_dim):
        for c in range (fp_col, fp_col + fp_col_dim):
            mask[r][c] = CANOPY
    mask[planting_row][planting_col] = tree_size


if __name__ == '__main__':
     run()
    
    



