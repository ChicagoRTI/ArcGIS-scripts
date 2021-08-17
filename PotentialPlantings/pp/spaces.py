import arcpy
import os

import pp.stats
import pp.common as pp_c

import pp.logger
logger = pp.logger.get('pp_log')


IN_MEM_ID = 0

PROBLEM_COMMUNITIES = ['Joliet', 'CHICAGO TWSHP']

def find_spaces (community_spec):
    try:
        
        # Process each community past the alphabetical starting point
        community, acres, idx = community_spec
        pp_c.log_info('Finding spaces. %i acres' % (acres), community)
        
        use_in_mem = pp_c.USE_IN_MEM if community not in PROBLEM_COMMUNITIES else False
        
        if use_in_mem:
            arcpy.Delete_management('in_memory')
            intermediate_output_gdb = None
        else:
            intermediate_output_gdb = os.path.join(pp_c.TEMP_DIR,  'intermediate_%i.gdb' %(pp_c.OS_PID))
            if not arcpy.Exists(intermediate_output_gdb):
                arcpy.CreateFileGDB_management(os.path.dirname(intermediate_output_gdb), os.path.basename(intermediate_output_gdb))

    
        canopy_clipped = __get_intermediate_name (intermediate_output_gdb, 'canopy_clipped', idx, use_in_mem)
        plantable_region_clipped = __get_intermediate_name (intermediate_output_gdb, 'plantable_region_clipped', idx, use_in_mem)
        buildings_clipped = __get_intermediate_name (intermediate_output_gdb, 'buildings_clipped', idx, use_in_mem)
        minus_trees = __get_intermediate_name (intermediate_output_gdb, 'minus_trees', idx, use_in_mem)
        minus_trees_buildings = __get_intermediate_name (intermediate_output_gdb, 'minus_trees_buildings', idx, use_in_mem)
        minus_trees_buildings_reclass = __get_intermediate_name (intermediate_output_gdb, 'minus_trees_buildings_reclass', idx, use_in_mem)
        plantable_poly = __get_intermediate_name (intermediate_output_gdb, 'plantable_poly', idx, use_in_mem)
        plantable_single_poly = __get_intermediate_name (intermediate_output_gdb, 'plantable_single_poly', idx, use_in_mem)
        plantable_muni = __get_intermediate_name (intermediate_output_gdb, 'plantable_muni', idx, use_in_mem)
        plantable_muni_landuse = __get_intermediate_name (intermediate_output_gdb, 'plantable_muni_landuse', idx, use_in_mem)
        plantable_muni_landuse_public = __get_intermediate_name (intermediate_output_gdb, 'plantable_muni_landuse_public', idx, use_in_mem)
        
        community_fc = pp_c.get_community_fc_name (community, pp_c.COMMUNITY_SPACES_FC)
        pp_c.delete ([community_fc])
        community_stats_tbl = pp.stats.prepare_community_stats_tbl (community, idx, pp_c.COMMUNITY_SPACE_STATS_TBL, pp_c.SPACE_STATS_SPEC)
                   
        pp_c.log_debug ('Getting community boundary', community)
        community_boundary = arcpy.SelectLayerByAttribute_management(pp_c.MUNI_COMMUNITY_AREA, 'NEW_SELECTION', "COMMUNITY = '%s'" % (community))[0]
    
        pp_c.log_debug ('Clipping %s' %(os.path.basename(pp_c.CANOPY_EXPAND_TIF)), community)
        arcpy.management.Clip(pp_c.CANOPY_EXPAND_TIF, '#', canopy_clipped, community_boundary, nodata_value='', clipping_geometry="ClippingGeometry", maintain_clipping_extent="MAINTAIN_EXTENT")
        percent_canopy = float(arcpy.management.GetRasterProperties(canopy_clipped, 'MEAN')[0])
    
        pp_c.log_debug ('Clipping %s' %(os.path.basename(pp_c.PLANTABLE_REGION_TIF)), community)
        arcpy.management.Clip(pp_c.PLANTABLE_REGION_TIF, '#', plantable_region_clipped, community_boundary, clipping_geometry="ClippingGeometry", maintain_clipping_extent="MAINTAIN_EXTENT")
    
        pp_c.log_debug ('Removing trees', community)
        arcpy.gp.RasterCalculator_sa('Con("%s" != 1,"%s")' % (canopy_clipped, plantable_region_clipped), minus_trees)
        pp_c.delete( [canopy_clipped, plantable_region_clipped] )
                   
        pp_c.log_debug ('Clipping %s' %(os.path.basename(pp_c.BUILDINGS_EXPAND_TIF)), community)
        arcpy.management.Clip(pp_c.BUILDINGS_EXPAND_TIF, '#', buildings_clipped, community_boundary, clipping_geometry="ClippingGeometry", maintain_clipping_extent="MAINTAIN_EXTENT")
        percent_buildings = float(arcpy.management.GetRasterProperties(buildings_clipped, 'MEAN')[0])
    
        pp_c.log_debug ('Removing buildings', community)
        arcpy.gp.RasterCalculator_sa('Con("%s" != 1,"%s")' % (buildings_clipped, minus_trees), minus_trees_buildings)
        pp_c.delete( [buildings_clipped, minus_trees, community_boundary] )
        
        pp_c.log_debug ('Reclassifying raster', community)
        minus_trees_buildings_reclass = arcpy.sa.Reclassify(minus_trees_buildings, "Value", "0 NODATA;1 1", "DATA"); 
        pp_c.delete( [minus_trees_buildings] )
        
        pp_c.log_debug ('Converting raster to polygon', community)        
        arcpy.RasterToPolygon_conversion(minus_trees_buildings_reclass, plantable_poly, "SIMPLIFY", "", "SINGLE_OUTER_PART", "")
        pp_c.delete( [minus_trees_buildings_reclass] )

        pp_c.log_debug ('Repair invalid features', community)        
        arcpy.management.RepairGeometry(plantable_poly, "DELETE_NULL", "ESRI")
    
        pp_c.log_debug ('Converting multipart polygons to singlepart', community)        
        arcpy.MultipartToSinglepart_management(plantable_poly, plantable_single_poly)            
        pp_c.delete( [plantable_poly] )
                
        pp_c.log_debug ('Spatial join', community)        
        arcpy.SpatialJoin_analysis(plantable_single_poly, pp_c.MUNI_COMMUNITY_AREA, plantable_muni, "JOIN_ONE_TO_ONE", "KEEP_ALL", "", "INTERSECT", "", "")
        pp_c.delete( [plantable_single_poly] )
    
        pp_c.log_debug ('Identify land use', community)        
        arcpy.Identity_analysis(plantable_muni, pp_c.LAND_USE_2015, plantable_muni_landuse, "ALL", "", "NO_RELATIONSHIPS")
        pp_c.delete( [plantable_muni] )
    
        pp_c.log_debug ('Identify public land', community)        
        arcpy.Identity_analysis(plantable_muni_landuse, pp_c.PUBLIC_LAND, plantable_muni_landuse_public, "ALL", "", "NO_RELATIONSHIPS")
        pp_c.delete( [plantable_muni_landuse] )
    
        pp_c.log_debug ('Add and populate the "CommunityID" field', community)   
        arcpy.management.CalculateField(plantable_muni_landuse_public, pp_c.SPACES_COMMUNITY_COL, '%i' % (idx), "PYTHON3", "", "SHORT")
    
        pp_c.log_debug ('Add and populate the "Public" field', community)   
        arcpy.management.CalculateField(plantable_muni_landuse_public, pp_c.SPACES_PUBLIC_PRIVATE_COL, "is_public(!FID_%s!)" % (os.path.basename(pp_c.PUBLIC_LAND)), "PYTHON3", r"""def is_public (fid):
            if fid == -1:
                return 0
            else:
                return 1""", "SHORT")
        
        __save_community_spaces (plantable_muni_landuse_public, community_fc)
        pp_c.delete( [plantable_muni_landuse_public] )

        pp.stats.update_stats (community_stats_tbl, idx, [percent_canopy*100, percent_buildings*100], pp_c.SPACE_STATS_SPEC)
            
    except Exception as ex:
      pp_c.log_debug ('Exception: %s' % (str(ex)))
      raise ex
        
    return community_fc
      

def  __get_intermediate_name (intermediate_output_gdb, name, idx, use_in_mem):
    global IN_MEM_ID
    
    if use_in_mem:
        IN_MEM_ID = IN_MEM_ID + 1
        fn = os.path.join('in_memory', 'm%i' % (idx) + '_' + name[0:3] + '_' + str(IN_MEM_ID))
    else:
        fn = os.path.join(intermediate_output_gdb, name + '_%i' % idx )
    pp_c.delete ([fn])
    return fn


def __trim_excess_fields (fc, keep_fields):
    all_fields = set([f.name.lower() for f in arcpy.ListFields(fc)])
    keep_fields = set([k.lower() for k in keep_fields])
    arcpy.DeleteField_management(fc, ';'.join(all_fields - keep_fields))
    return


def __save_community_spaces (in_fc, out_fc):
    sr = arcpy.Describe(pp_c.SPACES_TEMPLATE_FC).spatialReference
    arcpy.CreateFeatureclass_management(os.path.dirname(out_fc), os.path.basename(out_fc), 'POLYGON', pp_c.SPACES_TEMPLATE_FC, "DISABLED", "DISABLED", sr)        
    arcpy.management.AlterField(in_fc, 'LandUse', 'land_use')
    arcpy.management.Append(in_fc, out_fc, "NO_TEST")
    return


def prepare_fc ():
    if not arcpy.Exists(pp_c.SPACES_FC):       
        pp_c.log_debug ("Creating '%s'" % pp_c.SPACES_FC)
        sr = arcpy.Describe(pp_c.SPACES_TEMPLATE_FC).spatialReference
        arcpy.CreateFeatureclass_management(os.path.dirname(pp_c.SPACES_FC), os.path.basename(pp_c.SPACES_FC), 'POLYGON', pp_c.SPACES_TEMPLATE_FC, "DISABLED", "DISABLED", sr)        
        arcpy.management.AddIndex(pp_c.SPACES_FC, pp_c.SPACES_COMMUNITY_COL, "IDX_Comm", "NON_UNIQUE", "NON_ASCENDING")
        arcpy.management.AddIndex(pp_c.SPACES_FC, pp_c.SPACES_LANDUSE_COL, "IDX_LandUse", "NON_UNIQUE", "NON_ASCENDING")
    return   


def combine_spaces_fcs (community_specs):
    pp_c.log_debug ('Combining spaces feature classes')
    communities  = [c[0] for c in community_specs]
    community_fcs = [pp_c.get_community_fc_name (c, pp_c.COMMUNITY_SPACES_FC) for c in communities]
    community_ids = [str(c[2]) for c in community_specs]
    
    out_fc = pp_c.COMBINED_SPACES_FC   
    
    if pp_c.IS_SCRATCH_OUTPUT_DATA:
        pp_c.log_debug ('Deleting combined spaces feature class')
        pp_c.delete ([out_fc])
                
    if not arcpy.Exists(out_fc):       
        pp_c.log_debug ('Creating combined spaces feature class')
        sr = arcpy.Describe(community_fcs[0]).spatialReference
        arcpy.CreateFeatureclass_management(os.path.dirname(out_fc), os.path.basename(out_fc), 'POLYGON', community_fcs[0], "DISABLED", "DISABLED", sr)
        arcpy.management.AssignDomainToField(out_fc, pp_c.SPACES_LANDUSE_COL, pp_c.LANDUSE_DOMAIN_NAME)
        arcpy.management.AssignDomainToField(out_fc, pp_c.SPACES_PUBLIC_PRIVATE_COL, pp_c.PUBLIC_PRIVATE_DOMAIN_NAME)
        arcpy.management.AssignDomainToField(out_fc, pp_c.SPACES_COMMUNITY_COL, pp_c.COMMUNITY_DOMAIN_NAME)         
        arcpy.management.AddIndex(out_fc, pp_c.SPACES_COMMUNITY_COL, "IDX_Comm", "NON_UNIQUE", "NON_ASCENDING")
        arcpy.management.AddIndex(out_fc, pp_c.SPACES_LANDUSE_COL, "IDX_LandUse", "NON_UNIQUE", "NON_ASCENDING")
        
    if not pp_c.IS_SCRATCH_OUTPUT_DATA:        
        pp_c.log_debug ('Deleting existing features in combined spaces feature class')
        where = "%s IN (%s)" % (pp_c.SPACES_COMMUNITY_COL, ','.join(community_ids))
        old_records = arcpy.SelectLayerByAttribute_management(out_fc, 'NEW_SELECTION', where)[0]
        arcpy.management.DeleteFeatures(old_records)

 
    pp_c.log_info ('Write to combined spaces feature class')
    arcpy.management.Append(community_fcs, out_fc)
   
    return







    




