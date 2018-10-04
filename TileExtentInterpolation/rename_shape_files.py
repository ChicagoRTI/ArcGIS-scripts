# -*- coding: utf-8 -*-
"""
Created on Mon Sep 17 23:03:34 2018

@author: Don
"""

# The original files had periods in the file name which caused arcpy to 
# not recognize them as shape files. Copy the bad files to the 'renamed'
# directory then run this to fix up the names

import os

dir = 'D:/CRTI/GIS data/will_county_tree_crowns_sample/renamed'

# get the file name list to nameList
nameList = os.listdir(dir) 
#loop through the name and rename
for fileName in nameList:
    rename=fileName.replace('.tiles.', '_tiles_', 1)
    os.rename(dir + '/' + fileName,dir + '/' + rename)