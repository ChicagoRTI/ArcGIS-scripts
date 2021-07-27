# -*- coding: utf-8 -*-

import arcpy
from datetime import datetime



BuildingsExpand_tif = r"E:\PotentialPlantings\data\lindsay_tifs\BuildingsExpand.tif"
CanopyExpand_tif = r"E:\PotentialPlantings\data\lindsay_tifs\CanopyExpand.tif"
PlantableRegion_tif = r"E:\PotentialPlantings\data\lindsay_tifs\PlantableRegion.tif"

MuniCommunityArea = r"E:\PotentialPlantings\data\muni_community_area\MuniCommunityArea.shp"
LandUse2015_shp = r"E:\PotentialPlantings\data\cmap_landuse_2015\Landuse2015_CMAP_v1.shp"
DissolvedMerged = "D:\\Dropbox\\Forest Composition\\composition\\Maps\\shapefiles\\Illinois Protected Natural Lands Geodatabase\\Illinois Protected Natural Lands.gdb\\DissolvedMerged"


MinusTrees = r"E:\PotentialPlantings\intermediate_data.gdb\MinusTrees"
MinusTreesBuildings = r"E:\PotentialPlantings\intermediate_data.gdb\MinusTreesBuildings"
PlantablePoly = r"E:\PotentialPlantings\intermediate_data.gdb\PlantablePoly"
PlantableSinglePoly = r"E:\PotentialPlantings\intermediate_data.gdb\PlantableSinglePoly"
PlantableMuni = r"E:\PotentialPlantings\intermediate_data.gdb\PlantableMuni"
PlantableMuniLandUse = r"E:\PotentialPlantings\intermediate_data.gdb\PlantableMuniLandUse"
PlantableMuniLandUsePublic = r"E:\PotentialPlantings\intermediate_data.gdb\PlantableMuniLandUsePublic"
LandUsePublic__2_ = PlantableMuniLandUsePublic
LandUsePublic__4_ = LandUsePublic__2_

def run(start_step)
    print("Start Time 1 =", datetime.now().strftime("%H:%M:%S"))

    step_start = int(start_step)
    step_count = 1
    step_total = 14
    
    try:
   
        # Step 1: Raster Calculator
        if step_count >= step_start:    
            arcpy.gp.RasterCalculator_sa('Con(IsNull("%s"),"%s")' % (CanopyExpand_tif, PlantableRegion_tif), MinusTrees)
            print("Current Time 2 =", datetime.now().strftime("%H:%M:%S"))
        step_count += 1 
        
        
        # Step 2: Raster Calculator (2)
        if step_count >= step_start:    
            arcpy.gp.RasterCalculator_sa('Con(IsNull("%s"),"%s")' % (BuildingsExpand_tif, MinusTrees), MinusTreesBuildings)
            print("Current Time 3 =", datetime.now().strftime("%H:%M:%S"))
        step_count += 1 
        
        
        # Step 3: Raster to Polygon
        if step_count >= step_start:    
            tempEnvironment0 = arcpy.env.outputZFlag
            arcpy.env.outputZFlag = "Disabled"
            tempEnvironment1 = arcpy.env.outputMFlag
            arcpy.env.outputMFlag = "Disabled"
            arcpy.RasterToPolygon_conversion(MinusTreesBuildings, PlantablePoly, "SIMPLIFY", "", "SINGLE_OUTER_PART", "")
            print("Current Time 4 =", datetime.now().strftime("%H:%M:%S"))
            arcpy.env.outputZFlag = tempEnvironment0
            arcpy.env.outputMFlag = tempEnvironment1
        step_count += 1 
    
        
        # Step 4: Multipart To Singlepart
        if step_count >= step_start:    
            arcpy.MultipartToSinglepart_management(PlantablePoly, PlantableSinglePoly)
            print("Current Time 5 =", datetime.now().strftime("%H:%M:%S"))
        step_count += 1 
    
        
        # Step 5: Spatial Join
        if step_count >= step_start:    
            arcpy.SpatialJoin_analysis(PlantableSinglePoly, MuniCommunityArea, PlantableMuni, "JOIN_ONE_TO_ONE", "KEEP_ALL", "", "INTERSECT", "", "")
            print("Current Time 6 =", datetime.now().strftime("%H:%M:%S"))
        step_count += 1 
        
        # Process: Identity
        arcpy.Identity_analysis(PlantableMuni, LandUse2015_shp, PlantableMuniLandUse, "ALL", "", "NO_RELATIONSHIPS")
        
        # Process: Identity (2)
        arcpy.Identity_analysis(PlantableMuniLandUse, DissolvedMerged, PlantableMuniLandUsePublic, "ALL", "", "NO_RELATIONSHIPS")
        
        # Process: Add Field
        arcpy.AddField_management(PlantableMuniLandUsePublic, "Public", "TEXT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    except ex as Exception:
        print("Current Time ex =", datetime.now().strftime("%H:%M:%S"))
        raise ex
        
        

if __name__ == '__main__':
    run(sys.argv[1])


# Process: Calculate Field
# arcpy.CalculateField_management(LandUsePublic__2_, "Public", "reclass(!FID_DissolvedMerged!)", "PYTHON", "def reclass(FID_DissolvedMerged):
#     if (FID_DissolvedMerged== -1):
#         return \"N\"
#     else:
#         return \"Y\"")

