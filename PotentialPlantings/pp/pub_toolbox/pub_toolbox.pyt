# -*- coding: utf-8 -*-

import arcpy
import pub_tool


import importlib
importlib.reload(pub_tool)


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Published"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [FindPlantSites]


class FindPlantSites(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Find Plant Sites"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        params = pub_tool.getParameterInfo()
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
        pub_tool.execute(parameters)
        return
