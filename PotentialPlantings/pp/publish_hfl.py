import arcpy
import os, sys
from arcgis.gis import GIS

prjPath = r"C:\Users\dmorrison\Documents\ArcGIS\Projects\TEST_publish_hfl\TEST_publish_hfl.aprx"

sd_fs_name = "PP Canopies"
portal = "http://www.arcgis.com" # Can also reference a local portal
user = "don.morrison"
password = "dmField_%8"

arcpy.SignInToPortal("https://www.arcgis.com", user, password)

relPath = r'E:\PotentialPlantings\temp\publish_hfl'
sddraft = os.path.join(relPath, "temporary service name.sddraft")
sd = os.path.join(relPath, "temporary service name.sd")

print("Creating SD file")
arcpy.env.overwriteOutput = True
# prj = arcpy.mp.ArcGISProject(prjPath)
# mp = prj.listMaps()[0]

# sharing_draft = mp.getWebLayerSharingDraft("HOSTING_SERVER", "FEATURE", sd_fs_name)
# sharing_draft.summary = "test"
# sharing_draft.tags = "test"
# sharing_draft.description = ""
# sharing_draft.credits = ""
# sharing_draft.useLimitations = ""
# sharing_draft.portalFolder="PP"

# sharing_draft.exportToSDDraft(sddraft)
# arcpy.StageService_server(sddraft, sd)

print("Connecting to {}".format(portal))
gis = GIS(portal, user, password)

# Find the SD, update it, publish /w overwrite and set sharing and metadata
print("Search for original SD on portal…")
print(f"Query: {sd_fs_name}")
sdItem = gis.content.search(query=sd_fs_name, item_type="Service Definition")
i=0
while sdItem[i].title != sd_fs_name:
            i += 1
print('Item Found')
print(f'item[i].title = {sdItem[i].title}, sd_fs_name = {sd_fs_name}')
item = sdItem[i] 
item.update(data=sd)

print("Overwriting existing feature service…")
fs = item.publish(overwrite=True)


#arcpy.server.UploadServiceDefinition(r"E:\PotentialPlantings\temp\publish_hfl\temporary service name.sd", "HOSTING_SERVER", "PP Canopies", '', "EXISTING", "PP", "STARTED", "USE_DEFINITION", "NO_SHARE_ONLINE", "PRIVATE", "NO_SHARE_ORGANIZATION", None)


print("Finished updating: {} – ID: {}".format(fs.title, fs.id))