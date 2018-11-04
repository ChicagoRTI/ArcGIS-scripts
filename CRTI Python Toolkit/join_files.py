# To run from Spyder iPython console:
#   runfile('D:/CRTI/python_projects/ArcGIS-scripts/CRTI Python Toolkit/join_files.py', wdir='D:/CRTI/python_projects/ArcGIS-scripts/CRTI Python Toolkit', args="'C:\Users\Don\Documents\ArcGIS\scratch.gdb\canopies_without_ndvi' 'PolygonId' 'C:\Users\Don\Documents\ArcGIS\scratch.gdb\zonal_ndvi' 'PolygonId' 'MAX;MEAN;STD'")
#


import sys
import common_functions
common_functions.add_arcgis_to_sys_path()
import arcpy

def log (message):
    common_functions.log(message)
    return

# Define generator for join data
def joindataGen(joinTable,fieldList,sortField):
    with arcpy.da.SearchCursor(joinTable,fieldList,sql_clause=['DISTINCT', 'ORDER BY ' + sortField]) as cursor:
        for row in cursor:
            yield row

# Function for progress reporting
def percentile(n,pct):
    return int(float(n)*float(pct)/100.0)

def join (inTable, inJoinField, joinTable, outJoinField, joinFields):
    log('Join left side: ' + inTable)
    log('Join right side: ' + joinTable)
    log('Join keys: ' + str(inJoinField) + ':' + str(outJoinField))
    
    common_functions.create_index (inTable, [inJoinField], 'LeftIdx')
    common_functions.create_index (joinTable, [outJoinField], 'RightIdx')

    
    # Add join fields
#    log('\nAdding join fields...')
    fList = [f for f in arcpy.ListFields(joinTable) if f.name in joinFields.split(';')]
    for i in range(len(fList)):
        name = fList[i].name
        type = fList[i].type
        if type in ['Integer','OID']:
            arcpy.AddField_management(inTable,name,field_type='LONG')
        elif type == 'String':
            arcpy.AddField_management(inTable,name,field_type='TEXT',field_length=fList[i].length)
        elif type == 'Double':
            arcpy.AddField_management(inTable,name,field_type='DOUBLE')
        elif type == 'Date':
            arcpy.AddField_management(inTable,name,field_type='DATE')
        else:
            arcpy.AddError('\nUnknown field type: {0} for field: {1}'.format(type,name))
    
    # Write values to join fields
    fieldList = [outJoinField] + joinFields.split(';')
    joinDataGen = joindataGen(joinTable,fieldList,outJoinField)
    joinTuple = joinDataGen.next()
    
    # 
    fieldList = [inJoinField] + joinFields.split(';')
    count = int(arcpy.GetCount_management(inTable).getOutput(0))
    j = 0
    with arcpy.da.UpdateCursor(inTable,fieldList,sql_clause=(None,'ORDER BY '+inJoinField)) as cursor:
        for row in cursor:
            j+=1
            common_functions.log_progress("Joining record ", count, j)
            row = list(row)
            key = row[0]
            try:
                while joinTuple[0] < key:
                    joinTuple = joinDataGen.next()
                if key == joinTuple[0]:
                    for i in range(len(joinTuple))[1:]:
                        row[i] = joinTuple[i]
                    row = tuple(row)
                    cursor.updateRow(row)
            except StopIteration:
                arcpy.AddWarning('\nEnd of join table.')
                break
    
    arcpy.SetParameter(5,inTable)
    log('\nDone.')



if __name__ == '__main__':
     join(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])