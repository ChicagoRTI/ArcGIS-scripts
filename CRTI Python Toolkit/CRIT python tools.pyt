# WARNING - it appears that you have to restart ArcGIS to get it to pick up any changes
# to imported modules. Try to delete the <toolbox name>.<tool_name>.pyt file see if that helps

import arcpy
import os
import sys
import ConfigParser



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

    # ArcGIS does some crazy stuff which prevents us from strong anything in an instance variable (and having it
    # persist across method calls), so make this a class variables
    g_current_county = ''
    
    def __init__(self):
        self.label = "prepare_canopy_data"
        self.description = "Prepare canopy data"
        self.canRunInBackground = False

        # Get the list of supported counties (read only)       
        self.county_names_config = ConfigParser.RawConfigParser()
        self.county_names_config.read(os.path.join(os.path.dirname(__file__), 'config_county_names.properties'))
        self.county_names = self.county_names_config.sections()
        
        # Get the config file (read/write)
        self.config_fn = os.path.join(os.path.dirname(__file__), 'config_input_parameters.properties')
        self.config = ConfigParser.RawConfigParser()
        self.config.read(self.config_fn)

        # List of input parameter names that get mapped to the config file
        self.input_parm_names = ['county_name', 'tile_folder', 'tile_dimension', 'ndvi_rasters', 'start_step', 'scratch_workspace', 'output_feature_class']

        
    def getParameterInfo(self):
        
        county_name = arcpy.Parameter(
            displayName="County",
            name="county_name",
            datatype="String",
            parameterType="Required",
            direction="Input")
        county_name.filter.type = "ValueList"
        county_name.filter.list = self.county_names
        self.county_names
    
    
        tile_folder = arcpy.Parameter(
            displayName="Tile folder",
            name="tile_folder",
            datatype="Folder",
            parameterType="Required",
            direction="Input")
                
        tile_dimension = arcpy.Parameter(
            displayName="Tile dimension size (feet)",
            name="tile_dimension",
            datatype="Double",
            parameterType="Required",
            direction="Input")
        
        ndvi_raster = arcpy.Parameter(
            displayName="NDVI raster file",
            name="ndvi_raster",
            datatype="Folder",
            parameterType="Required",
            direction="Input")
        
        start_step = arcpy.Parameter(
            displayName="Start step",
            name="start_step",
            datatype="Long",
            parameterType="Required",
            direction="Input")
        
        scratch_workspace = arcpy.Parameter(
            displayName="Scratch workspace",
            name="scratch_workspace",
            datatype="Folder",
            parameterType="Required",
            direction="Input")

        output_feature_class = arcpy.Parameter(
            displayName="Output feature class",
            name="output_feature_class",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")

        save_parameters = arcpy.Parameter(
            displayName="Save parameters",
            name="save_parameters",
            datatype="Boolean",
            parameterType="Optional",
            direction="Input")
        scratch_workspace.value = False
        
        params = [county_name, tile_folder, tile_dimension, ndvi_raster, start_step, scratch_workspace, output_feature_class, save_parameters]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
 
        # If the county name is changed, update the input parms from the config file
        if parameters[0].valueAsText != prepare_canopy_data.g_current_county and parameters[0].valueAsText in self.config.sections():
            for i in range(1,len(self.input_parm_names)):
                parameters[i].value = self.config.get(parameters[0].valueAsText, self.input_parm_names[i])
        prepare_canopy_data.g_current_county = parameters[0].valueAsText

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        # Write out the county input parameters to the config file
        if parameters[7].value == True:
            for i in range(1,len(self.input_parm_names)):
                self.config.set(parameters[0].valueAsText, self.input_parm_names[i], parameters[i].valueAsText)
            self.config.write(open(self.config_fn, 'w'))

        import prepare_canopy_data
        prepare_canopy_data.prepare_canopy_data(
            os.path.normpath(parameters[1].valueAsText), 
            parameters[2].valueAsText, 
            os.path.normpath(parameters[3].valueAsText), 
            parameters[4].valueAsText, 
            os.path.normpath(parameters[5].valueAsText),
            os.path.normpath(parameters[6].valueAsText))        
        return

