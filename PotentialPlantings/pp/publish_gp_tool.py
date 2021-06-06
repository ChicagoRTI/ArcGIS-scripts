
import arcpy
import os



import pp.pub_toolbox.pp_logger as logger
logger = logger.get('pp_log')


CODE_BASE = os.path.normpath(os.path.dirname(__file__) + '/../')
GP_TOOL_TITLE = 'FindPlantSites_TEST'
COMMUNITY =   'Bensenville' 

SD_DRAFT_FN = os.path.join(arcpy.env.scratchFolder, 'gp_tool.sddraft')
SD_FN = os.path.join(arcpy.env.scratchFolder, 'gp_tool.sd')
AGS_CONNECTION_FN = r'E:\ROW_as_habitat\conn3.ags'
REST_FOLDER = 'PP_Spaces'

AGS_ADMIN_URL = 'https://seaman.fm.pri:6443/arcgis/admin'


    
def __run_gp_tool ():
    logger.info ("Running tool %s" % (GP_TOOL_TITLE))
    # Load the published toolbox and run the tool
    arcpy.ImportToolbox(os.path.join(CODE_BASE, r'pp\pub_toolbox\PublishedTools.pyt'))  
    results = [arcpy.publishedtools.FindPlantSites(COMMUNITY)]
    return results
            
        
def stage():     
    results = __run_gp_tool()
                     
    # Delete any existing sd and sddraft files
    __delete_file(SD_DRAFT_FN)
    __delete_file(SD_FN)
    
    logger.info ("Creating SDDraft %s" % (SD_DRAFT_FN))    
    arcpy.CreateGPSDDraft(results,
                          SD_DRAFT_FN,
                          GP_TOOL_TITLE,
                          server_type='FROM_CONNECTION_FILE',
                          connection_file_path=AGS_CONNECTION_FN,
                          copy_data_to_server=False,
                          folder_name=REST_FOLDER,
                          summary='test',
                          tags='test',
                          executionType='Asynchronous',
                          showMessages='Info',
                          minInstances=1,
                          maxInstances=2,
                          maxUsageTime=10*60,
                          resultMapServer=True)
    
    logger.info ("Creating SD %s" % (SD_FN))    
    arcpy.server.StageService(SD_DRAFT_FN, SD_FN)
    return


def publish(): 
    logger.info ("Uploading SD %s" % (SD_FN) )   
    arcpy.UploadServiceDefinition_server(SD_FN, AGS_CONNECTION_FN)
    return




def __delete_file (file_name):
    if os.path.exists(file_name): 
        os.remove(file_name)
    
if __name__ == '__main__':
    stage ()
    publish()
    pass
    
 
