import arcpy
import glob
import os

arcpy.env.workspace = r"C:\Users\dmorrison\crti\data\Potential Plantings\cook_county_plantable\cook_county_plantable_shp"
output = r"C:\Users\dmorrison\crti\data\Potential Plantings\cook_county_plantable\cook_county_plantable_gdb.gdb\polygons"

path = os.path.join (arcpy.env.workspace, '*.shp')
in_files = glob.glob(path)

arcpy.management.CreateFeatureclass(os.path.dirname(output), os.path.basename(output), 'POLYGON', spatial_reference=arcpy.SpatialReference(102671))

i=0
print_step = 100

# in_files = in_files[0:20]

print ("starting")
for in_file in in_files:
    i=i+1
    if (int(i/print_step)) * print_step == i:
        print (f"{i} of {len(in_files)}")
    arcpy.management.Append([in_file], output, "NO_TEST")
    
print ("done")