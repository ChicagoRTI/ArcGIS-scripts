#Load libraries

library(tidyverse)
library(tidylog)       # More verbose tidyverse
library(magrittr)      # %>% piping
library(sf)            # Spatial data
library(arcpullr)      # Pull REST endpoints

#I work off two computers. This allows me to specify the different paths
path <- 'D:/'
#path <- 'C:/Users/ledarlin/'

#Set working directory
setwd(paste0(path, 'Dropbox/Forest Composition/composition/Maps/shapefiles/Inventory'))

#Grab the layer and clean it up

#This is from the canopy counts inventory
past <- st_read('CanopyCountsTrees.shp') %>% 
  #Make better names. New name = old name
  rename(Latin = GnsSpcs,
         Cultivar = cultivr,
         Condition = vitalty,
         CommonName = CommnNm) %>% 
  #Add columns that will be in the final dataset
  mutate(Dieback = NA,
         Date = NA,
         Edited = NA,
         Notes = NA) %>% 
  #Select only the columns that we want
  dplyr::select('CommonName', 'Latin', 'Cultivar', 'Genus', 'dbh', 'Dieback', 'Condition',
         'Date', 'Edited', 'Notes') %>% 
  #There are a couple of ridiculous trees. Remove their DBH and replace with NA
  mutate(dbh = if_else(dbh > 99, NA, 
                       if_else(dbh < 1, NA, dbh)))

#This file is used to rectify common and latin names
list <- read_csv(paste0(path, 'Dropbox/Forest Composition/composition/AnalyzedStuff/SpeciesListClean.csv')) %>% 
  rename(CommonName = COMMONNAME,
         Latin = GenusSpecies)

#Pull the data from Lindsay's survey and clean up
#Pulls data directly from enterprise
#Steps are pretty much the same as for the past data

present <- get_spatial_layer('https://gis.mortonarb.org/server/rest/services/Hosted/survey123_06e7000db25046e89596e25ffde74ef8/FeatureServer/0') %>% 
  rename(dbh = tree_dbh,
         CommonName = field_9,
         Date = created_date,
         Edited = last_edited_date,
         Cultivar = cultivar,
         Dieback = percent_branch_dieback_or_missi,
         Condition = overall_condition,
         Notes = notes,
         geometry = geoms) %>% 
  left_join(., list, by = 'CommonName') %>% 
  dplyr::select('CommonName', 'Latin', 'Cultivar', 'Genus', 'dbh', 'Dieback', 'Condition',
                'Date', 'Edited', 'Notes') %>% 
  #Merge the past and present data
  rbind(., past) %>% 
  mutate(Photo = NA,
         Container = NA,
         RootsCorrected = NA,
         size_at_planting = NA,
         nursery = NA,
         TreeID = NA)

#Internal

#Pull the data from Angelica's survey and clean up
#Pulls data directly from enterprise
#Steps are pretty much the same as for the past data

#Images don't pull with the data. This is a list of the urls. They will be joined in.
pics <- read_csv('ImageLookup.csv')

internal <- get_spatial_layer('https://gis.mortonarb.org/server/rest/services/Hosted/service_d8b3fda9400f4053aa5c90c400d6c07d/FeatureServer/0') %>% 
  rename(dbh = tree_dbh,
         Multistem = multistem,
         CommonName = common_name,
         Date = date_,
         Edited = last_edited_date,
         Cultivar = cultivar,
         Dieback = percent_dieback_missingcrown,
         Condition = overall_condition,
         Notes = notes,
         geometry = geoms,
         Container = plant_package,
         RootsCorrected = root_correct) %>% 
  left_join(., list, by = 'CommonName') %>% 
    #This combines the latin names from the survey to the ones from the joined table
  mutate(Latin = coalesce(latin_name, Latin),
         nursery = if_else(nursery == 'Other', `other_nursery`, nursery),
         Date = as_date(Date)) %>%
  dplyr::select(-c(CommonName,latin_common,latin_name,Genus,Species,Common,Combined)) %>% 
  left_join(., list, by = 'Latin') %>%   #Rejoin to get common names. Oofta
  #Get only needed columns
  dplyr::select('CommonName', 'Latin', 'Cultivar', 'Genus', 'dbh', 'Dieback', 'Condition',
                'Date', 'Edited', 'Notes', 'Container', 'RootsCorrected', 'size_at_planting',
                'nursery') %>% 
  slice(1:1048) %>% #Remove some erroneous entries that I did.
  cbind(., pics) %>% #Add pics.
  rbind(., present) #Bind to other data.

  
#check

plot(internal[,5])

#Write it out.
st_write(past, paste0('OldData','.shp'), driver = 'ESRI Shapefile', append = FALSE)

