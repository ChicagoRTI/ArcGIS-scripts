import sys
import os
import arcpy
import traceback

import logger as pp_logger
logger = pp_logger.get('pp_log')


def getParameterInfo ():
    try:   
        logger.debug("Enter getParameterInfo")
    
        layer =  arcpy.Parameter(displayName="Layer", name="layer", datatype="GPFeatureLayer",  parameterType="Required",  direction="Input")                

        class_ = arcpy.Parameter(
            displayName="Class",
            name="class",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        class_.filter.type = "ValueList"
        class_.filter.list = [1,2,3]
        class_.value = class_.filter.list[0]


        params =  [layer, class_]   
    except Exception as e:
        logger.debug('Exception occurred %s' % (str(e)))
        logger.debug(traceback.format_exc())
        raise e   
    return params    