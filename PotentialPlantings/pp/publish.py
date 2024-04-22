
# Credentials are stashed using this command
#
#  SET PYTHON_EXE="C:\\Users\\dmorrison\\AppData\\Local\\ESRI\\conda\\envs\\arcgispro-py3-clone\\python.exe"
#  %PYTHON_EXE%  -c "import keyring; keyring.set_password('PP_PUBLISHER', 'don.morrison.2000@gmail.com', 'xxxxxxxx')"
#
#
# This script can NOT publish to the enterprise portal because it uses "IWA" authentication. The only way to access 
# the enterprise portal from python is to have ArcGIS pro up and the enterprise portal specified as the active portal. Then 
# it can be accessed with this login
#
# gis = GIS("pro")
#
import arcpy
from arcgis.gis import GIS
import keyring
import tempfile
import os
from shutil import copyfile

KEYRING_ID = 'PP_PUBLISHER'
USERNAME = 'don.morrison.2000@gmail.com'
PASSWORD = keyring.get_password(KEYRING_ID, USERNAME)

BLANK_PROJECT = r'C:\Users\dmorrison\crti\git\ArcGIS-scripts\PotentialPlantings\pp\templates\blank_project.aprx'

PUBLISH_SPECS = [
    # {'name': 'PP Stats',
    #  'folder': 'PP',
    #  'data_source': r'C:\Users\dmorrison\crti\output\potential_plantings\trees_and_stats.gdb\stats',
    #  'display_field': 'objectid',
    #  'portal_agol': True,
    #  'shr_org': True,
    #  'shr_everyone': False,
    #  'shr_group': 'Potential Plantings'
    #  },
    # {'name': 'PP Trees',
    #  'folder': 'PP',
    #  'data_source': r'C:\Users\dmorrison\crti\output\potential_plantings\trees_and_stats.gdb\trees',
    #  'display_field': 'objectid',
    #  'portal_agol': True,
    #  'shr_org': True,
    #  'shr_everyone': False,
    #  'shr_group': 'Potential Plantings'
    #  },
    {'name': 'PP_spaces',
      'folder': 'PP',
      'data_source': r'C:\Users\dmorrison\crti\output\potential_plantings\spaces.gdb\spaces',
      'display_field': 'objectid',
      'portal_agol': False,
      'shr_org': True,
      'shr_everyone': True,
      'shr_group': None
      },

    ]

def run():
    
    for pub_spec in PUBLISH_SPECS:
        __publish (pub_spec)
    return   
    

def __publish (pub_spec):
    
    print ("Logging in")
    if pub_spec['portal_agol']:
        gis = GIS(username=USERNAME, password=PASSWORD)
    else:
        gis = GIS("Pro")
    print ("Logged into %s as %s" % (gis.properties.portalName, gis.users.me.username))
        
    print ("Creating layer from %s" % pub_spec['data_source'])
    lyr = arcpy.MakeFeatureLayer_management(pub_spec['data_source'], os.path.basename(pub_spec['data_source'])).getOutput(0)
    lyr_def = lyr.getDefinition("V2")
    lyr_def.featureTable.displayField = pub_spec['display_field']
    lyr.setDefinition(lyr_def)
    
    
    print ("Creating project")
    prjPath = tempfile.NamedTemporaryFile(suffix='.aprx').name
    copyfile(BLANK_PROJECT, prjPath)
    aprx = arcpy.mp.ArcGISProject(prjPath)
    aprx_map = aprx.listMaps()[0].addLayer(lyr, 'BOTTOM')
    aprx.save()     
    

    relPath = os.path.dirname(prjPath)
    sddraft = os.path.join(relPath, "WebUpdate.sddraft")
    sd = os.path.join(relPath, "WebUpdate.sd")
    
    # Create a new SDDraft and stage to SD
    print("Creating SD file")
    arcpy.env.overwriteOutput = True
    prj = arcpy.mp.ArcGISProject(prjPath)
    mp = prj.listMaps()[0]
    arcpy.mp.CreateWebLayerSDDraft(mp, sddraft,  pub_spec['name'], 'MY_HOSTED_SERVICES', 'FEATURE_ACCESS','', True, True)
    arcpy.StageService_server(sddraft, sd)
        
    # Find the SD, update it, publish /w overwrite and set sharing and metadata
    print("Search for original SD on portal…")
    sdItem = [i for i in gis.users.me.items(folder=pub_spec['folder']) if i.title==pub_spec['name'] and i.type=='Service Definition'][0]
    print("Found SD: {}, ID: {} Uploading and overwriting…".format(sdItem.title, sdItem.id))
    sdItem.update(data=sd)
    print("Overwriting existing feature service…")
    fs = sdItem.publish(overwrite=True)
    
    print("Setting sharing option")
    g_ids = [g.id for g in gis.groups.search("title: '%s' AND owner: %s" % (pub_spec['shr_group'], USERNAME))]
    g_id = [g_ids[0]] if len(g_ids) > 0 else None
    print (str(g_id))
    fs.share(org=pub_spec['shr_org'], everyone=pub_spec['shr_everyone'], groups=g_id)
  
    print("Finished updating: {} - ID: {}".format(fs.title, fs.id))
    
    del aprx_map                             
    del aprx                             
    arcpy.Delete_management(lyr)  
    os.remove(sddraft)                           
    os.remove(sd)                           
    os.remove(prjPath)                           
                             
                                  
    return




if __name__ == '__main__':
     run()