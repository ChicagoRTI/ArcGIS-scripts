# Requires python 3


import arcpy
import os
import math


openings_fc = r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\data\test.gdb\openings'
neg_buffered_fc = r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\data\test.gdb\neg_buffered'
matrix_fc = r'C:\Git_Repository\CRTI\ArcGIS-scripts\PotentialPlantings\data\test.gdb\matrix'
diameter = 30 * 0.3048
neg_buffer = - (10 * 0.3048)




 # Assumes no multpart polygons
 # Negative buffer might cause polygon to disappear
 # Overlapping polygons is a problem


def run ():
                                   
    arcpy.management.Delete(matrix_fc)
    arcpy.CreateFeatureclass_management(os.path.dirname(matrix_fc),
                                    os.path.basename(matrix_fc),
                                    "POINT",
                                    spatial_reference=arcpy.Describe(openings_fc).SpatialReference)


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
            points = []

            tiers = math.ceil(max((x_max-x_min)/2, (y_max-y_min)/2) / diameter)
            for tier in range(0, tiers+1):
                bot  = [(x,-tier)  for x in range (-tier, tier+1)]
                top  = [(x, tier)  for x in range (-tier, tier+1)]
                left = [(-tier, y) for y in range (-tier, tier+1)]
                right= [(tier, y)  for y in range (-tier, tier+1)]
                tier_coordinates = set(bot + top + left + right)
                for tier_coordinate in tier_coordinates:
                    x = center.X + (tier_coordinate[0] * diameter)
                    y = center.Y + (tier_coordinate[1] * diameter)
                    if x >= x_min and x <= x_max and y >= y_min and y <= y_max:
                        points_checked = points_checked + 1
                        if arcpy.Point(x,y).within(polygon):
                            points.append ( (x,y) )                   

            with arcpy.da.InsertCursor(matrix_fc, ['SHAPE@']) as cursor:
                for point in points:
                    cursor.insertRow([arcpy.Point(point[0], point[1])])


    print ("%i points checked" % points_checked)    





    

if __name__ == '__main__':
     run()
    
    



