# WARNING - it appears that you have to restart ArcGIS to get it to pick up any changes
# to imported modules. Try to delete the <toolbox name>.<tool_name>.pyt file see if that helps

import arcpy
import os
import sys


class Toolbox(object):
    def __init__(self):
        self.label = "CRTI python toolbox"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [prepare_canopy_data]
        
#############################################################################
#
#                   prepare_canopy_data
#
#############################################################################
class prepare_canopy_data(object):
    def __init__(self):
        self.label = "prepare_canopy_data"
        self.description = "Prepare canopy data"
        self.canRunInBackground = False

    def getParameterInfo(self):
        tile_folder = arcpy.Parameter(
            displayName="Tile folder",
            name="tile_folder",
            datatype="Folder",
            parameterType="Required",
            direction="Input")
        tile_folder.value = r'D:\CRTI\GIS data\DP_sample_tile_block'
                
        tile_dimension = arcpy.Parameter(
            displayName="Tile dimension size (feet)",
            name="tile_dimension",
            datatype="Double",
            parameterType="Required",
            direction="Input")
        tile_dimension.value = 2500.0
        
        ndvi_raster = arcpy.Parameter(
            displayName="NDVI raster file",
            name="ndvi_raster",
            datatype="Folder,
            parameterType="Required",
            direction="Input")
        ndvi_raster.value =r'D:\CRTI\GIS data\Earth Engine\DupageNDVI'
        
        start_step = arcpy.Parameter(
            displayName="Start step",
            name="start_step",
            datatype="Long",
            parameterType="Required",
            direction="Input")
        start_step.value = 1

        output_fc = arcpy.Parameter(
            displayName="Output feature class",
            name="output_fc",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")
        output_fc.value = arcpy.env.scratchGDB + '/prepared_canopy_data'
        
        params = [tile_folder, tile_dimension, ndvi_raster, start_step, output_fc]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        import prepare_canopy_data
        prepare_canopy_data.prepare_canopy_data(
            os.normpath(parameters[0].valueAsText), 
            parameters[1].valueAsText, 
            os.normpath(parameters[2].valueAsText), 
            parameters[3].valueAsText, 
            os.normpath(parameters[4].valueAsText))        
        return

