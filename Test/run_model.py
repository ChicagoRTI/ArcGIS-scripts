# -*- coding: utf-8 -*-

# To run from Spyder iPython console:
#   runfile('D:/CRTI/python_projects/ArcGIS-scripts/Test/run_model.py')
#
# To run under ArcGIS python, enter these commands from the DOS window
#   cd D:\CRTI\python_projects\ArcGIS-scripts\Test\
#   C:\Python27_ArcGIS\ArcGIS10.6\python -m run_model

# NOTE: running this from the Spyder console works but there is no console output

__toolbox = r"C:\Users\Don\AppData\Roaming\ESRI\Desktop10.6\ArcToolbox\My Toolboxes\DonsToolbox.tbx"
__alias = "mytbx"

import arcpy
import sys
arcpy.ImportToolbox(__toolbox, __alias)

# Run the imported model
arg1 = r'D:\Temp\shp_test'
arg2 = 'NAME2'
arcpy.mytbx.ModelTest(arg1, arg2)

# This is a hack tha tries to determine running under ArcGIS or outside of ArcGIS
# (in which case we neeed to retrieve the messages explicitly)
if 'ArcGIS\\ArcGIS' not in sys.executable:
    print(arcpy.GetMessages())