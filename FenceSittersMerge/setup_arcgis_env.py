 # Startup script to link Anaconda python environment with ArcGIS
#
# 1. Install Anaconda, setup environment to match your ArcGIS version
# 2. Edit the paths below
# 3. Put this startup script in the startup folder as "usercustomize.py"
#    Startup folder can be found with: "C:\Python27\ArcGIS10.2\python -m site --user-site"
#    Usually will be:
# C:\Users\%USERNAME%\AppData\Roaming\Python\Python27\site-packages

import sys
import os

# edit these paths to match your setup
arcver = "10.4"
# Anaconda home folders
conda32 = r"C:\Anaconda2"
conda64 = r"D:\Users\cprice\Anaconda64"
# here are the conda environments you've set up use with ArcGIS
# arc1022 is the environment setup for ArcGIS
conda_env32 = "{}/envs/{}".format(conda32, "Python27-geospacial")
conda_env64 = "{}/envs/{}".format(conda64, "arc1022")

# do not edit below this line

# ArcGIS Python home folders
# i.e. C:\Python27\ArcGIS10.2
arcver = arcver[:4]
arcpy32 = r"C:\Python27_ArcGIS\ArcGIS{}".format(arcver)
arcpy64 = r"C:\Python27\ArcGISx64{}".format(arcver)

try:
    if sys.version.find("64 bit") < 0:
        conda_path = os.path.normpath(conda_env32)
        arcpy_path = os.path.normpath(arcpy32)
        arcpy_pthfile = os.path.normpath(
            arcpy_path + "/lib/site-packages/desktop{}.pth".format(arcver))
    else:
        conda_path = os.path.normpath(conda_env64)
        arcpy_path = os.path.normpath(arcpy64)
        arcpy_pthfile = os.path.normpath(
            arcpy_path + "/lib/site-packages/DTBGGP64.pth")

    for p in [conda_path, arcpy_path, arcpy_pthfile]:
        if not os.path.exists(p):
            raise Exception("{} not found".format(p))

    ## print(sys.prefix)
    ## print(conda_path)

    # If running ArcGIS's Python, add conda modules to path
    if (sys.executable.lower().find("desktop" + arcver) != -1
        or sys.prefix.lower().find("arcgis10") != -1):
        sys.path.append(os.path.dirname(arcpy_path))
        conda_site = os.path.join(conda_path, "lib", "site-packages")
        if not os.path.isdir(conda_site):
            raise Exception()
        sys.path.append(conda_site)
        print("usercustomize.py: added conda paths to arc")

    # if running Anaconda add arcpy to path
    elif sys.prefix.lower() == conda_path.lower():
        with open(arcpy_pthfile, "r") as f:
            sys.path +=  [p.strip() for p in f.readlines()]
        print("usercustomize.py: added arcpy paths to conda")

except Exception as msg:
    print(msg)
    pass