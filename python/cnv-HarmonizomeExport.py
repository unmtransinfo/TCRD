#!/usr/bin/env python
# Time-stamp: <2019-08-27 15:06:45 smathias>
"""Convert Harmonizome data from CSV files exported from previous TCRD version to inserts for new version.

Usage:
    cnv-HarmonizomeExport.py [--debug | --quiet] [--logfile=<file>] [--loglevel=<int>]
    cnv-HarmonizomeExport.py -h | --help

Options:
  -l --logfile LOGF    : set log file name
  -v --loglevel LOGL   : set logging level [default: 30]
                         50: CRITICAL
                         40: ERROR
                         30: WARNING
                         20: INFO
                         10: DEBUG
                          0: NOTSET
  -q --quiet           : set output verbosity to minimal level
  -d --debug           : turn on debugging output
  -? --help            : print this message and exit 
"""
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2019, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "1.0.0"

import os,sys,time,re
from docopt import docopt
import logging
import csv
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = 'tcrd6logs/'
LOGFILE = LOGDIR + '%s.log'%PROGRAM
IDMAP_FILE = '../exports/TCRDsym26id5id.csv'
GAT_EXPORT_FILE = '../exports/TCRD5-gene_attribute_type.csv'
GAT_IMPORT_FILE = '../SQL/TCRD6-gene_attribute_types.csv'
GA_EXPORT_FILE = '../exports/TCRD5-gene_attribute.csv'
GA_IMPORT_FILE = '../SQL/TCRD6-gene_attributes.csv'

def mk_id_map(ifn):
  idmap = {}
  with open(ifn, 'r') as ifh:
    csvreader = csv.reader(ifh)
    header = csvreader.next() # skip header line
    for row in csvreader:
      # map v5 protein.id to v6 protein.id
      id6 = int(row[1])
      id5 = int(row[2])
      idmap[id5] = id6
  return idmap
    
def cnv_gene_attribute_types(args, ifn, ofn):
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  line_ct = slmf.wcl(ifn)
  if not args['--quiet']:
    print "\nProcessing {} lines in file {}".format(line_ct, ifn)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start()
  rct = 0
  wct = 0
  with open(ofn, 'w') as ofh:
    ofh.write('"id","name","association","description","resource_group","measurement","attribute_group","attribute_type","pubmed_ids","url"\n')
    with open(ifn, 'r') as ifh:
      csvreader = csv.reader(ifh)
      header = csvreader.next() # skip header line
      rct = 1
      for row in csvreader:
        # "id","name","association","description","resource_group","measurement","attribute_group","attribute_type","pubmed_ids","url"
        rct += 1
        ofh.write('"{}","{}","{}","{}","{}","{}","{}","{}","{}","{}"\n'.format(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9]))
        wct += 1
        pbar.update(rct)
      pbar.finish()
  print "Processed {} lines".format(rct)
  print "  Wrote {} new gene_attribute_type rows to file {}".format(wct, ofn)
  return

def cnv_gene_attributes(args, idmap, ifn, ofn):
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  line_ct = slmf.wcl(ifn)
  if not args['--quiet']:
    print "\nProcessing {} lines in file {}".format(line_ct, ifn)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start()
  rct = 0
  wct = 0
  skip_ct = 0
  gaid = 1
  with open(ofn, 'w') as ofh:
    ofh.write('"id","protein_id","gat_id","name","value"\n')
    with open(ifn, 'r') as ifh:
      csvreader = csv.reader(ifh)
      header = csvreader.next() # skip header line
      rct = 1
      for row in csvreader:
        # "id","protein_id","gat_id","name","value"
        rct += 1
        v5pid = int(row[1])
        if v5pid in idmap:
          # v5 protein maps to v6 protein
          v6pid = idmap[v5pid]
        else:
          skip_ct += 1
          continue
        ofh.write('"{}","{}","{}","{}","{}"\n'.format(gaid, v6pid, row[2], row[3], row[4]))
        gaid += 1
        wct += 1
        pbar.update(rct)
      pbar.finish()
  print "Processed {} lines.".format(rct)
  print "  Wrote {} new gene_attribute rows to file {}".format(wct, ofn)
  print "  Skipped {} rows that do not map from v5 to v6.".format(skip_ct)
  return
    
if __name__ == '__main__':
  print "\n{} (v{}) [{}]:".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  
  start_time = time.time()  
  idmap = mk_id_map(IDMAP_FILE)
  if not args['--quiet']:
    print "\nGot {} TCRD5 to TCRD6 protein.id mappings.".format(len(idmap))
  cnv_gene_attribute_types(args, GAT_EXPORT_FILE, GAT_IMPORT_FILE)
  cnv_gene_attributes(args, idmap, GA_EXPORT_FILE, GA_IMPORT_FILE)
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))
