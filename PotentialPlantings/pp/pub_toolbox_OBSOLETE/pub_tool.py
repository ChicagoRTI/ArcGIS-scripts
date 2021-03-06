import sys
import os
import arcpy
import traceback

import main_mp

import pp_logger
logger = pp_logger.get('pp_log')


import importlib
importlib.reload(main_mp)

COMMUNITIES = ['Oak Lawn',
               'Near South Side',
                'West Town',
                'Near North Side',
                'Schiller Park',
                'Harwood Heights',
                'Bensenville',
                'River Grove',
                'Douglas',
                'Franklin Park',
                'Rosemont',
                'Clearing',
                'West Lawn',
                'Northlake',
                'Norwood Park',
                'Melrose Park',
                'Stone Park',
                'Archer Heights',
                'Garfield Ridge',
                'Des Plaines',
                'Ohare',
                'Armour Square',
                'Hometown',
                'Norridge']

def getParameterInfo ():
    try:   
        logger.debug("Enter getParameterInfo")
    
        # layer =  arcpy.Parameter(
        #         displayName="Layer", 
        #         name="layer", 
        #         datatype="GPFeatureLayer",  
        #         parameterType="Required",  
        #         direction="Input")                

        class_ = arcpy.Parameter(
            displayName="Community",
            name="class",
            datatype="String",
            parameterType="Required",
            direction="Input")
        class_.filter.type = "ValueList"
        class_.filter.list = sorted(COMMUNITIES)
        class_.value = class_.filter.list[0]

        output =  arcpy.Parameter(
                displayName="Planting Sites", 
                name="output", 
                datatype="DEFeatureClass",  
                parameterType="Derived",  
                direction="Output")
        output.symbology = os.path.join(os.path.dirname(__file__), 'symbology.lyrx')



        params =  [class_, output]   
    except Exception as e:
        logger.debug('Exception occurred %s' % (str(e)))
        logger.debug(traceback.format_exc())
        raise e   
    return params    



def execute(parameters):
    db_dir = main_mp.DB_DIR    
    in_fc = os.path.join(db_dir, 'PP_TEST_pp_spaces_projected')
    out_fc = os.path.join(arcpy.env.scratchGDB, 'out_fc')
    arcpy.Delete_management(out_fc)
    main_mp.run(in_fc, "community = '%s'" % (parameters[0].value), out_fc)    
    parameters[1].value = out_fc



    # aprx = arcpy.mp.ArcGISProject('CURRENT')
    # logger.debug ("aprx: %s" % (aprx))
    # if aprx is not None and aprx.activeMap is not None:
    #     current_map = aprx.activeMap
    #     logger.info ("Updating map %s" % (current_map.name))
    #     lyr = current_map.addDataFromPath(out_fc)
        
        
        
    return
