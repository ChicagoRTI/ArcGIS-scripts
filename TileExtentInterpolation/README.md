# TileExtentInterpolation
Take a directory of shape files (tiles) and create an output shape files representing the tile boundaries. This code assumes that the tiles are exactly 
1500 feet on each side. 


To run from Spyder iPython console:
````
runfile('D:/CRTI/python_projects/compute_tile_extents/interpolate_tile_extents.py', wdir='D:/CRTI/python_projects/compute_tile_extents', args="'D:/CRTI/GIS data/will_county_tree_crowns_sample/renamed'")
````

To run under ArcGIS python, enter these commands from the DOS window
````
cd D:\CRTI\python_projects\compute_tile_extents\
C:\Python27_ArcGIS\ArcGIS10.4\python -m interpolate_tile_extents "D:/CRTI/GIS data/will_county_tree_crowns_sample/renamed" 
````

Note that the input shape files can not have a period in the file names. Update/run the rename_shape_files.py file to replace the periods with valid characters.

# Future changes
* Take output directory as input
* Multiprocessor support
