import arcpy

import os
arcpy.env.overwriteOutput = True

MOSAIC = r"C:\Users\dmorrison\crti\output\potential_plantings\prep\streets.gdb\veg_mosaic"
PATH_TBL =  r"C:\Users\dmorrison\Documents\ArcGIS\Projects\PotentialPlantings\PotentialPlantings.gdb\veg_mosaic_Paths1"

arcpy.management.ExportMosaicDatasetPaths(MOSAIC, 
                                          PATH_TBL, 
                                          '', "ALL", "RASTER;ITEM_CACHE")


with arcpy.da.SearchCursor(PATH_TBL, ['Path']) as cursor:
    for unshifted_rst, in cursor:

        print (os.path.basename(unshifted_rst))
        shifted_rst = os.path.join(os.path.dirname(unshifted_rst), 'shifted.tif')  
        try:
            arcpy.Delete_management(shifted_rst)
        except Exception:
            pass
        
        arcpy.management.Shift(unshifted_rst, shifted_rst, x_value=-2.5, y_value=3.0)
        
        arcpy.Delete_management(unshifted_rst)
        arcpy.management.Rename(shifted_rst, unshifted_rst)
      



print ("Done")


