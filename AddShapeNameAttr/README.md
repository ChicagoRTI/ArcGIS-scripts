# AddShapeNameAttr
The python code to add an attribute to all shape files in a directory and populate it with the name of the shape file
````
process_shape_file.py <input_shape_file> <output_shape_file>
````

The directory name, attribute name, and attribute value are all hard coded in the python program



To run from Spyder iPython console:
````
runfile('D:/CRTI/python_projects/ArcGIS-scripts/AddShapeNameAttr/add_shape_name_attr.py', wdir='D:/CRTI/python_projects/ArcGIS-scripts/AddShapeNameAttr', args="")
````

To run under ArcGIS python:
````
cd D:\CRTI\python_projects\AddShapeNameAttr\
C:\Python27_ArcGIS\ArcGIS10.4\python -m add_shape_name_attr 
````

## Future work
* Accept values as input instead of hard coding
