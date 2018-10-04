# FenceSittersMerge
The python code to fix up the fence sitters. 
````
process_shape_file.py <input_shape_file> <output_shape_file>
````

The input is a polygon shape file where all fence sitters clumps are identified by the following attributes:
* Fence = 1 if the polygon is a fence siter
* ClumpID = numeric identifier for the set of fence sitters that form a clump 

Other required attributes:
* FID_1 = unique record ID
* NAME = tile ID
* Area = polygon area (square feet)
* Border_len = polygon border length (feet)
* Border_tre = length (feet) of polygon border that abuts another tree
* Compactnes = index of compactness
* nDSM_max = max height of tree represented by polygon
* nDSM_mean = mean height of tree represented by polygon
* nDSM_min = min height of tree represented by polygon
* RelBord_tr = Border_tre / Border_len
* ShapeIndex = shape index: border_length / (4*(square root of area))


To run from Spyder iPython console:
````
runfile('D:/CRTI/python_projects/FenceSittersMerge/process_shape_file.py', wdir='D:/CRTI/python_projects/FenceSittersMerge', args="'D:/CRTI/GIS data/DP_sample_area_w_clumps/original/DP_sample_area_w_clumps.shp' 'D:/CRTI/GIS data/DP_sample_area_w_clumps/work/DP_sample_area_w_clumps.shp'")
````

To run under ArcGIS python:
````
cd D:\CRTI\python_projects\FenceSittersMerge\
C:\Python27_ArcGIS\ArcGIS10.6\python -m process_shape_file "D:/CRTI/GIS data/DP_sample_area_w_clumps/original/DP_sample_area_w_clumps.shp" "D:/CRTI/GIS data/DP_sample_area_w_clumps/work/DP_sample_area_w_clumps.shp"
````
