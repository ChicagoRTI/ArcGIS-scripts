
import os
import sys
import fs.common_functions
import arcpy
import glob

_TILE_NAME = 'TileName'
_TILE_ID = 'TileId'


_SHAPE_FILE_EXTENSIONS = [
        '.shp',
        '.shx',
        '.dbf',
        '.sbn',
        '.sbx',
        '.fbn',
        '.fbx',
        '.ain',
        '.aih',
        '.atx',
        '.ixs',
        '.mxs',
        '.prj',
        '.xml',
        '.cpg']

def log (message):
    fs.common_functions.log(message)
    return

# Return the file names/ids as a list of tuples <tile_name, tile_id>
def read_file_names (table):
    names = list()
    with arcpy.da.SearchCursor(table, [_TILE_NAME, _TILE_ID, 'Shape@' ]) as rows:
        for row in rows:
            names.append((row[0],row[1],row[2]))
        del rows
    return names


# Write the list of file names/ids to the output table
def write_file_names (table, file_names):
    log ('Creating output table ' + table)
    sr = arcpy.Describe(file_names[0]).spatialReference
    
    out_path, out_fc = os.path.split(table)
    arcpy.env.workspace = out_path
    if arcpy.Exists(table):
        arcpy.Delete_management(table)
    arcpy.CreateFeatureclass_management(out_path, out_fc, "POLYGON", spatial_reference=sr)
    arcpy.AddField_management(out_fc, _TILE_NAME, 'TEXT', '512')
    arcpy.AddField_management(out_fc, _TILE_ID, 'LONG')

    log ('Writing file names to ' + table)
    tile_id = 1    
    with  arcpy.da.InsertCursor(out_fc, ['SHAPE@', _TILE_NAME, _TILE_ID]) as rows:
        for name in file_names:
            extent = arcpy.Describe(name).extent
            array = arcpy.Array([arcpy.Point(extent.XMin, extent.YMin),
                     arcpy.Point(extent.XMin, extent.YMax),
                     arcpy.Point(extent.XMax, extent.YMax),
                     arcpy.Point(extent.XMax, extent.YMin),
                     arcpy.Point(extent.XMin, extent.YMin)
                     ])
            polygon = arcpy.Polygon(array)
            
            rows.insertRow([polygon, name, tile_id])
            tile_id += 1
        del rows 
        
def create_table (input_fc_folder, output_table):
    log ('Gathering file names from ' + input_fc_folder)
    arcpy.env.workspace = input_fc_folder
    
    # Check if the input is a  folder (implies shape files) and any files need to be renamed
    if arcpy.Describe(input_fc_folder).dataType == 'Folder':
        for full_path in glob.glob(os.path.join(input_fc_folder,'*')):
            file_name, extension = os.path.splitext(os.path.basename(full_path))
            if '.' in file_name and extension in _SHAPE_FILE_EXTENSIONS:
                try:
                    os.rename(full_path, os.path.join(input_fc_folder, file_name.replace('.', '_') + extension))
                except:
                    log ('Failed renaming ' + full_path)

    # Gather up the feature class names
    names = [os.path.join(input_fc_folder, fc_name) for fc_name in arcpy.ListFeatureClasses()]
        
    log (str(len(names)) + ' files found')
    write_file_names (output_table, names)
    return 

        

if __name__ == '__main__':
    create_table(os.path.normpath(sys.argv[1]), os.path.normpath(sys.argv[2]))
    
    




