
TCRD is the central resource behind the [Illuminating the Druggable Genome Knowledge Management Center (IDG-KMC)](http://targetcentral.ws/KMC_TiD/). TCRD contains information about human targets, with special emphasis on four families of targets that are central to the NIH IDG initiative: GPCRs, kinases, ion channels and nuclear receptors. Olfactory GPCRs (oGPCRs) are treated as a separate family. The official public portal for IDG-KMC is: [Pharos](https://pharos.nih.gov/).

The code in this repository is for people wanting to rebuild a version of TCRD from scratch. If you just want to install TCRD locally, MySQL dumps of recent versions are available for download [here](http://juniper.health.unm.edu/tcrd/download/).

## Overview of the Build Process
Targets in TCRD correspond to reviewed human entries in UniProt. There are 50+ datasets in TCRD and one loader script in the loaders directory to load each. Depending on the dataset, data is loaded via web APIs and/or files in various formats. Regarding the latter, some loaders take care of downloading the file(s) they need; others require the user to download or obtain the file(s) manually before running. Additionally, some datasets require pre-processing steps before loading and a few also require manual steps be perforemd after the load is completed.

### doc/TCRD_Build_Notes.html
This file has information for each dataset on the steps required and also an estimate of the time required. Some loaders run in a few minutes, others require days.

### doc/README_v4.txt
This file contains all command lines, and most of their output, run to build TCRD v4. There are notes in this file that should help with the pre- and post- processing required for some of the datasets.

### Loading Order
Some of the loaders need to be run before others. Generally, the steps 1-13 (UniProt through TDLs) should be run in the order they are listed in doc/TCRD_Build_Notes.html. After that, loaders can be run in whatever order you like.

## System Requirements
You will need a Linux or OSX system (you might be able to get things to work on Windows, but it would require a lot of fiddling - Not recommended) and I would recommend at least 4 cores and 64GB of RAM.

## Software Requirements
### MySQL server
I am using MySQL Community Server 5.6.24. But anything version 5.5 or later would be fine.

### Python
Python 2.7 and many Python modules not included in the standard library: BioPython, BeautifulSoup, docopt, goatools, httplib2, progressbar, urllib, urllib2, cPickle, cStringIO, csv, KEGG_Graph, MySQLdb, networkx, numpy, requests, and shelve.

### Lars Jensen's Tagger
This is available [here](https://bitbucket.org/larsjuhljensen/tagger).

### R
R and the R packages dplyr, stringr, tidyr, data.table, and Hmisc.


