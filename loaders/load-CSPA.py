#!/usr/bin/env python
# Time-stamp: <2017-06-20 12:40:06 smathias>
"""
Load Cell Surface Protein Atlas expression data into TCRD from CSV files.

Usage:
    load-HumanCellAtlas.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>] [--pastid=<int>]
    load-HumanCellAtlas.py -h | --help

Options:
  -h --dbhost DBHOST   : MySQL database host name [default: localhost]
  -n --dbname DBNAME   : MySQL database name [default: tcrdev]
  -l --logfile LOGF    : set log file name
  -v --loglevel LOGL   : set logging level [default: 30]
                         50: CRITICAL
                         40: ERROR
                         30: WARNING
                         20: INFO
                         10: DEBUG
                          0: NOTSET
  -q --quiet           : set output verbosity to minimal level
  -d --debug DEBUGL    : set debugging output level (0-3) [default: 0]
  -? --help            : print this message and exit 
"""
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2017, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "1.0.0"

import os,sys,time
from docopt import docopt
import pandas as pd
import numpy as np
import csv
from TCRD import DBAdaptor
import logging
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = 'tcrd4logs/'
LOGFILE = LOGDIR+'%s.log'%PROGRAM
INFILE = '../data/CSPA/S1_File.csv'

def load():
  args = docopt(__doc__, version=__version__)
  debug = int(args['--debug'])
  if debug:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  
  loglevel = int(args['--loglevel'])
  if args['--logfile']:
    logfile = args['--logfile']
  else:
    logfile = LOGFILE
  logger = logging.getLogger(__name__)
  logger.setLevel(loglevel)
  if not debug:
    logger.propagate = False # turns off console logging when debug is 0
  fh = logging.FileHandler(logfile)
  fmtr = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
  fh.setFormatter(fmtr)
  logger.addHandler(fh)

  dba_params = {'dbhost': args['--dbhost'], 'dbname': args['--dbname'], 'logger_name': __name__}
  dba = DBAdaptor(dba_params)
  dbi = dba.get_dbinfo()
  logger.info("Connected to TCRD database %s (schema ver %s; data ver %s)", args['--dbname'], dbi['schema_ver'], dbi['data_ver'])
  if not args['--quiet']:
    print "\nConnected to TCRD database %s (schema ver %s; data ver %s)" % (args['--dbname'], dbi['schema_ver'], dbi['data_ver'])
  
  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'Cell Surface Protein Atlas', 'source': 'Worksheet B in S1_File from http://wlab.ethz.ch/cspa/#downloads', 'app': PROGRAM, 'app_version': __version__, 'url': 'http://wlab.ethz.ch/cspa'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'expression', 'where_clause': "etype = 'Cell Surface Protein Atlas'", 'comment': 'Only high confidence values are loaded.'})
  if not rv:
    print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
    sys.exit(1)

  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  
  #
  # Expressions
  #
  line_ct = wcl(INFILE)
  if not args['--quiet']:
    print "\nProcessing %d lines from CSPA file %s" % (line_ct, INFILE)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  ct = 0
  skip_ct = 0
  notfnd = []
  dba_err_ct = 0
  tmark = {}
  exp_ct = 0
  with open(INFILE, 'rU') as csvfile:
    csvreader = csv.reader(csvfile)
    header = csvreader.next()
    for row in csvreader:
      ct += 1
      pbar.update(ct)
      if row[2] != '1 - high confidence':
        skip_ct += 1
        continue
      uniprot = row[1]
      geneid = row[4]
      targets = dba.find_targets({'uniprot': uniprot}, False)
      if not targets:
        targets = dba.find_targets({'geneid': geneid}, False)
      if not targets:
        k = "%s|%s"%(uniprot,geneid)
        notfnd.append(k)
        logger.warn("No target found for %s" % k)
        continue
      for t in targets:
        tmark[t['id']] = True
        pid = t['components']['protein'][0]['id']
        cell_lines = [c for c in header[6:-1]] # there's a blank field at the end of the header line
        for (i,cl) in enumerate(cell_lines):
          val_idx = i + 6 # add six because row has other values at beginning
          if not row[val_idx]:
            continue
          rv = dba.ins_expression( {'protein_id': pid, 'etype': 'Cell Surface Protein Atlas',
                                    'tissue': 'Cell Line '+cl, 'boolean_value': True} )
          if not rv:
            dba_err_ct += 1
            continue
          exp_ct += 1
  pbar.finish()
  print "Processed %d CSPA lines." % ct
  print "  Inserted %d new expression rows" % exp_ct
  print "  Skipped %d non-high confidence rows" % skip_ct
  print "  %d proteins have CSPA expression data" % len(tmark)
  if notfnd:
    print "  No target found for %d lines. See logfile %s for details." % (len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)
  
      
def wcl(fname):
  with open(fname) as f:
    for i, l in enumerate(f):
      pass
  return i + 1

def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])

if __name__ == '__main__':
  print "\n%s (v%s) [%s]:" % (PROGRAM, __version__, time.strftime("%c"))
  start_time = time.time()
  load()
  elapsed = time.time() - start_time
  print "\n%s: Done. Elapsed time: %s\n" % (PROGRAM, secs2str(elapsed))
