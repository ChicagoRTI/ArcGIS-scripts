import arcpy
import os

import pp.common as pp_c

import pp.logger
logger = pp.logger.get('pp_log')


IN_MEM_ID = 0


def run_mp (community_spec):
    try:

        pp_c.log_debug ("C: %s" % str(community_spec))
       
        arcpy.env.outputZFlag = "Disabled"
        arcpy.env.outputMFlag = "Disabled"
        arcpy.overwriteOutput = True
        
        # Process each community past the alphabetical starting point
        community, acres, idx = community_spec
        pp_c.log_info('%i acres' % (acres), community)
        
        pp_c.USE_IN_MEM = pp_c.USE_IN_MEM if community != 'CHICAGO TWSHP' else False
        
        if pp_c.USE_IN_MEM:
            arcpy.Delete_management('in_memory')
            intermediate_output_gdb = None
        else:
            intermediate_output_gdb = os.path.join(pp_c.INTERMEDIATE_OUTPUT_DIR,  'intermediate_%i.gdb' %(pp_c.OS_PID))
            if not arcpy.Exists(intermediate_output_gdb):
                arcpy.CreateFileGDB_management(os.path.dirname(intermediate_output_gdb), os.path.basename(intermediate_output_gdb))

    
        canopy_clipped = __get_intermediate_name (intermediate_output_gdb, 'canopy_clipped', idx, pp_c.USE_IN_MEM)
        plantable_region_clipped = __get_intermediate_name (intermediate_output_gdb, 'plantable_region_clipped', idx, pp_c.USE_IN_MEM)
        buildings_clipped = __get_intermediate_name (intermediate_output_gdb, 'buildings_clipped', idx, pp_c.USE_IN_MEM)
        minus_trees = __get_intermediate_name (intermediate_output_gdb, 'minus_trees', idx, pp_c.USE_IN_MEM)
        minus_trees_buildings = __get_intermediate_name (intermediate_output_gdb, 'minus_trees_buildings', idx, pp_c.USE_IN_MEM)
        minus_trees_buildings_reclass = __get_intermediate_name (intermediate_output_gdb, 'minus_trees_buildings_reclass', idx, pp_c.USE_IN_MEM)
        plantable_poly = __get_intermediate_name (intermediate_output_gdb, 'plantable_poly', idx, pp_c.USE_IN_MEM)
        plantable_single_poly = __get_intermediate_name (intermediate_output_gdb, 'plantable_single_poly', idx, pp_c.USE_IN_MEM)
        plantable_muni = __get_intermediate_name (intermediate_output_gdb, 'plantable_muni', idx, pp_c.USE_IN_MEM)
        plantable_muni_landuse = __get_intermediate_name (intermediate_output_gdb, 'plantable_muni_landuse', idx, pp_c.USE_IN_MEM)
        plantable_muni_landuse_public = __get_intermediate_name (intermediate_output_gdb, 'plantable_muni_landuse_public', idx, pp_c.USE_IN_MEM)
        
        community_fc = get_community_spaces_fc_name (community)
        community_gdb = os.path.dirname(community_fc)
        if not arcpy.Exists(community_gdb):
            arcpy.CreateFileGDB_management(os.path.dirname(community_gdb), os.path.basename(community_gdb))
        pp_c.delete ([community_fc])
                   
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
        percent_buildings = arcpy.management.GetRasterProperties(buildings_clipped, 'MEAN')[0]
    
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
    
        pp_c.log_debug ('Trim excess fields', community)   
        __trim_excess_fields (plantable_muni_landuse_public, ['objectid', 'shape', 'shape_area', 'shape_length', pp_c.SPACES_LANDUSE_COL, pp_c.SPACES_PUBLIC_PRIVATE_COL, pp_c.SPACES_COMMUNITY_COL])
    
        __save_community_spaces (plantable_muni_landuse_public, community_fc)
        pp_c.delete( [plantable_muni_landuse_public] )

        __update_stats (idx, {'percent_canopy': percent_canopy, 'percent_buildings': percent_buildings})
            
    except Exception as ex:
      pp_c.log_debug ('Exception: %s' % (str(ex)))
      raise ex
        
    return community_fc
      




def  __get_intermediate_name (intermediate_output_gdb, name, idx, USE_IN_MEM):
    global IN_MEM_ID
    
    if pp_c.USE_IN_MEM:
        IN_MEM_ID = IN_MEM_ID + 1
        fn = os.path.join('in_memory', 'm%i' % (idx) + '_' + name[0:3] + '_' + str(IN_MEM_ID))
    else:
        fn = os.path.join(intermediate_output_gdb, name + '_%i' % idx )
    pp_c.delete ([fn])
    return fn


def get_community_spaces_fc_name (community):
    community_gdb = os.path.join(pp_c.COMMUNITY_OUTPUT_DIR, community.replace(' ','') + '.gdb')
    community_fc =  os.path.join(community_gdb, pp_c.COMMUNITY_SPACES_FC)
    return community_fc


def get_community_trees_fc_name (community):
    community_gdb = os.path.join(pp_c.COMMUNITY_OUTPUT_DIR, community.replace(' ','') + '.gdb')
    community_fc =  os.path.join(community_gdb, pp_c.COMMUNITY_TREES_FC)
    return community_fc



def __trim_excess_fields (fc, keep_fields):
    all_fields = set([f.name.lower() for f in arcpy.ListFields(fc)])
    keep_fields = set([k.lower() for k in keep_fields])
    arcpy.DeleteField_management(fc, ';'.join(all_fields - keep_fields))
    return



def __save_community_spaces (in_fc, out_fc):
    temp_out_fc = os.path.join(os.path.dirname(out_fc), os.path.basename(out_fc) + '_projected')
    if arcpy.da.Describe(in_fc)['catalogPath'].startswith('in_memory\\'):
        arcpy.CopyFeatures_management(in_fc, temp_out_fc)
    else:        
        arcpy.Copy_management(in_fc, temp_out_fc)   
    arcpy.management.Project(temp_out_fc, out_fc, arcpy.Describe(pp_c.TREE_TEMPLATE_FC).spatialReference)
    pp_c.delete ([temp_out_fc])
    return



def combine_spaces_fcs (community_specs):
    pp_c.log_debug ('Combining spaces feature classes')
    communities  = [c[0] for c in community_specs]
    community_fcs = [get_community_spaces_fc_name (c) for c in communities]
    community_ids = [str(c[2]) for c in community_specs]
    
    out_fc = pp_c.COMBINED_SPACES_FC   
        
    if not arcpy.Exists(pp_c.COMBINED_OUTPUT_DIR):
        arcpy.CreateFileGDB_management(os.path.dirname(pp_c.COMBINED_OUTPUT_DIR), os.path.basename(pp_c.COMBINED_OUTPUT_DIR))
        __create_domains (pp_c.COMBINED_OUTPUT_DIR)
    
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



def combine_trees_fcs (community_specs):
    pp_c.log_debug ('Combining trees feature classes')
    communities  = [c[0] for c in community_specs]
    community_fcs = [get_community_trees_fc_name (c) for c in communities]
    community_ids = [str(c[2]) for c in community_specs]
    
    out_fc = pp_c.COMBINED_TREES_FC   
        
    if not arcpy.Exists(pp_c.COMBINED_TREES_OUTPUT_GDB):
        arcpy.CreateFileGDB_management(os.path.dirname(pp_c.COMBINED_TREES_OUTPUT_GDB), os.path.basename(pp_c.COMBINED_TREES_OUTPUT_GDB))
        __create_domains (pp_c.COMBINED_TREES_OUTPUT_GDB)
    
    if pp_c.IS_SCRATCH_OUTPUT_DATA:
        pp_c.log_debug ('Deleting combined trees feature class')
        pp_c.delete ([out_fc])
        
    if not arcpy.Exists(out_fc):       
        pp_c.log_debug ('Creating combined trees feature class')
        sr = arcpy.Describe(community_fcs[0]).spatialReference
        arcpy.CreateFeatureclass_management(os.path.dirname(out_fc), os.path.basename(out_fc), 'POINT', community_fcs[0], "DISABLED", "DISABLED", sr)
        arcpy.management.AssignDomainToField(out_fc, pp_c.TREES_LANDUSE_COL, pp_c.LANDUSE_DOMAIN_NAME)
        arcpy.management.AssignDomainToField(out_fc, pp_c.TREES_PUBLIC_PRIVATE_COL, pp_c.PUBLIC_PRIVATE_DOMAIN_NAME)
        arcpy.management.AssignDomainToField(out_fc, pp_c.TREES_COMMUNITY_COL, pp_c.COMMUNITY_DOMAIN_NAME)    
        arcpy.management.AssignDomainToField(out_fc, pp_c.TREES_SIZE_COL, pp_c.TREE_SIZE_DOMAIN_NAME) 
        arcpy.management.AddIndex(out_fc, pp_c.TREES_COMMUNITY_COL, "IDX_Comm", "NON_UNIQUE", "NON_ASCENDING")
        arcpy.management.AddIndex(out_fc, pp_c.TREES_LANDUSE_COL, "IDX_LandUse", "NON_UNIQUE", "NON_ASCENDING")
        arcpy.management.AddIndex(out_fc, pp_c.TREES_PUBLIC_PRIVATE_COL, "IDX_PublicPrivate", "NON_UNIQUE", "NON_ASCENDING")
        
    if not pp_c.IS_SCRATCH_OUTPUT_DATA:
        pp_c.log_debug ('Deleting existing features in combined trees feature class')
        where = "%s IN (%s)" % (pp_c.TREES_COMMUNITY_COL, ','.join(community_ids))
        old_records = arcpy.SelectLayerByAttribute_management(out_fc, 'NEW_SELECTION', where)[0]
        arcpy.management.DeleteFeatures(old_records)
        
    pp_c.log_info ('Write to combined trees feature class')
    arcpy.management.Append(community_fcs, out_fc)
   
    return


def __create_domains (workspace):
    # Land use
    arcpy.management.CreateDomain(workspace, pp_c.LANDUSE_DOMAIN_NAME, None, 'SHORT', 'CODED')
    for d in pp_c.LANDUSE_DOMAIN.keys():        
        arcpy.management.AddCodedValueToDomain(workspace, pp_c.LANDUSE_DOMAIN_NAME, pp_c.LANDUSE_DOMAIN[d], d)
    # Public/Private
    arcpy.management.CreateDomain(workspace, pp_c.PUBLIC_PRIVATE_DOMAIN_NAME, None, 'SHORT', 'CODED')
    for d in pp_c.PUBLIC_PRIVATE_DOMAIN.keys():
        arcpy.management.AddCodedValueToDomain(workspace, pp_c.PUBLIC_PRIVATE_DOMAIN_NAME, pp_c.PUBLIC_PRIVATE_DOMAIN[d], d)
    # Tree size
    arcpy.management.CreateDomain(workspace, pp_c.TREE_SIZE_DOMAIN_NAME, None, 'SHORT', 'CODED')
    for d in pp_c.TREE_SIZE_DOMAIN.keys():
        arcpy.management.AddCodedValueToDomain(workspace, pp_c.TREE_SIZE_DOMAIN_NAME, pp_c.TREE_SIZE_DOMAIN[d], d)
    # Community name
    arcpy.management.CreateDomain(workspace, pp_c.COMMUNITY_DOMAIN_NAME, None, 'SHORT', 'CODED')
    with arcpy.da.SearchCursor(pp_c.MUNI_COMMUNITY_AREA, ['OBJECTID', 'Community']) as cursor:
            for attr_vals in cursor:
                arcpy.management.AddCodedValueToDomain(workspace, pp_c.COMMUNITY_DOMAIN_NAME, attr_vals[0], attr_vals[1])
    return        



def compute_tree_stats ():
    # Build a view with the trees per community and make a copy because the view is really slow       
    query = "Select count(*) as trees, community_id from trees group by community_id"
    tree_count_by_community_view = arcpy.management.CreateDatabaseView(os.path.dirname(pp_c.COMBINED_TREES_FC), "tree_count_by_community_view", query)[0]  
    tree_count_by_community_table = arcpy.conversion.TableToTable(tree_count_by_community_view, arcpy.env.scratchGDB, 'tree_count_by_community_table')[0]
        
    # Extract the acres for each community
    acres_by_community = dict()
    with arcpy.da.SearchCursor(pp_c.COMBINED_STATS_FC, [pp_c.STATS_COMMUNITY_COL, 'acres']) as cursor:
        for community_id, acres in cursor:
            acres_by_community[community_id] = acres
    
    # Extract the tree count for each community
    tree_count_by_community = dict()
    with arcpy.da.SearchCursor(tree_count_by_community_table, ['community_id', 'trees'], 'trees IS NOT NULL') as cursor:
        for community_id, trees in cursor:
            tree_count_by_community[community_id] = trees

    pp_c.delete ([tree_count_by_community_view, tree_count_by_community_table]) 
    
    # Update the stats table with the tree count and trees/acre
    for community_id in  tree_count_by_community.keys():
        trees = tree_count_by_community[community_id]
        acres = acres_by_community[community_id]
        trees_per_acre = trees/acres
        __update_stats (community_id, {'trees': trees, 'trees_per_acre': trees_per_acre})
   
                                                
    return


    
def prepare_stats_fc ():
    stats_gdb = os.path.dirname(pp_c.COMBINED_STATS_FC)
    if not arcpy.Exists(stats_gdb) or pp_c.IS_SCRATCH_OUTPUT_DATA:
        arcpy.CreateFileGDB_management(os.path.dirname(stats_gdb), os.path.basename(stats_gdb))

    if not arcpy.Exists(pp_c.COMBINED_STATS_FC) or pp_c.IS_SCRATCH_OUTPUT_DATA:
        # Make a copy of the community feature class and reproject it
        communities_fc = arcpy.conversion.FeatureClassToFeatureClass(pp_c.MUNI_COMMUNITY_AREA, arcpy.env.scratchGDB, 'communities')[0]
        arcpy.management.Project(communities_fc, pp_c.COMBINED_STATS_FC, arcpy.Describe(pp_c.COMBINED_TREES_FC).spatialReference)
    
        # Add the stats fields
        for name, type_ in pp_c.STATS_SPEC:
            arcpy.AddField_management(pp_c.COMBINED_STATS_FC, name, type_)
         # Fill in the community_id field  
        arcpy.management.CalculateField(pp_c.COMBINED_STATS_FC, pp_c.STATS_COMMUNITY_COL, '!OBJECTID!')
        # Fill in the acres field  
        arcpy.management.CalculateField(pp_c.COMBINED_STATS_FC, 'acres', "!shape.area@acres!")
        # Map community id to name
        arcpy.management.AssignDomainToField(pp_c.COMBINED_STATS_FC, pp_c.STATS_COMMUNITY_COL, pp_c.COMMUNITY_DOMAIN_NAME)    

            
        pp_c.delete ([communities_fc])
    return


def __update_stats (community_id, stats):
    field_names = list(stats.keys())
    with arcpy.da.UpdateCursor(pp_c.COMBINED_STATS_FC, [pp_c.STATS_COMMUNITY_COL] + field_names, '%s = %i' % (pp_c.STATS_COMMUNITY_COL, community_id)) as cursor:
        for attr_vals in cursor:
            vals = [attr_vals[0]] + [stats[k] for k in field_names]
            cursor.updateRow(vals)
    return

    




