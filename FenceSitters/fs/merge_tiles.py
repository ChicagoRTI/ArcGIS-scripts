import sys
import os
import fs.common_functions
import arcpy
import fs.tile_file_names


_CHUNK_SIZE = 1000


def log (message):
    fs.common_functions.log(message)
    return


def merge_one_chunk (fns, sr, fc_output):
    in_mem_tile_fc = os.path.join('in_memory', 'tile')
    try:
        # Create an in-memory feature class to accumulate the chunk
        arcpy.CreateFeatureclass_management(os.path.dirname(in_mem_tile_fc), os.path.basename(in_mem_tile_fc), "POLYGON", fns[0], '','', sr)
        # Aggregate all tiles in the chunk        
        for fn in fns:
            arcpy.Append_management(fn, in_mem_tile_fc)
        # Append the chunk to the output feature class
        arcpy.Append_management(in_mem_tile_fc, fc_output)
            
    finally:
        # Clean up    
        arcpy.Delete_management(in_mem_tile_fc)



def merge (tile_file_names_table, fc_output):
    
    # Chunk up the list of tiles
    fns = [fn[0] for fn in fs.tile_file_names.read_file_names(tile_file_names_table)]
    fns_list = [fns[i:i+_CHUNK_SIZE] for i in range(0, len(fns), _CHUNK_SIZE)] 
    sr = arcpy.Describe(fns[0]).spatialReference
    
    # Delete the output feature set
    arcpy.Delete_management(fc_output)
    arcpy.CreateFeatureclass_management(os.path.dirname(fc_output), os.path.basename(fc_output), "POLYGON", fns[0], '','', sr)
    
    i=0
    for fns in fns_list:
        i += 1
        fs.common_functions.log_progress("Processing segment", len(fns_list), i)
        merge_one_chunk (fns, sr, fc_output)
 


if __name__ == '__main__':
     merge(sys.argv[1], sys.argv[2])
    
    



