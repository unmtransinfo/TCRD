#!/usr/bin/env python
# Time-stamp: <2018-04-05 10:13:42 smathias>
"""
Load Cell Surface Protein Atlas expression data into TCRD from CSV files.

Usage:
    load-HumanCellAtlas.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>] [--pastid=<int>]
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
  -d --debug           : turn on debugging output
  -? --help            : print this message and exit 
"""
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2017-2018, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "1.1.0"

import os,sys,time
from docopt import docopt
import pandas as pd
import numpy as np
import csv
from TCRD import DBAdaptor
import logging
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = 'tcrd5logs/'
LOGFILE = LOGDIR+'%s.log'%PROGRAM
INFILE = '../data/CSPA/S1_File.csv'

def load(args):
  loglevel = int(args['--loglevel'])
  if args['--logfile']:
    logfile = args['--logfile']
  else:
    logfile = LOGFILE
  logger = logging.getLogger(__name__)
  logger.setLevel(loglevel)
  if not args['--debug']:
    logger.propagate = False # turns off console logging
  fh = logging.FileHandler(logfile)
  fmtr = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
  fh.setFormatter(fmtr)
  logger.addHandler(fh)

  dba_params = {'dbhost': args['--dbhost'], 'dbname': args['--dbname'], 'logger_name': __name__}
  dba = DBAdaptor(dba_params)
  dbi = dba.get_dbinfo()
  logger.info("Connected to TCRD database {} (schema ver {}; data ver {})".format(args['--dbname'], dbi['schema_ver'], dbi['data_ver']))
  if not args['--quiet']:
    print "\nConnected to TCRD database {} (schema ver {}; data ver {})".format(args['--dbname'], dbi['schema_ver'], dbi['data_ver'])
  
  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'Cell Surface Protein Atlas', 'source': 'Worksheet B in S1_File.xlsx from http://wlab.ethz.ch/cspa/#downloads, converted to CSV', 'app': PROGRAM, 'app_version': __version__, 'url': 'http://wlab.ethz.ch/cspa'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'expression', 'where_clause': "etype = 'Cell Surface Protein Atlas'", 'comment': 'Only high confidence values are loaded.'})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  
  line_ct = slmf.wcl(INFILE)
  if not args['--quiet']:
    print "\nProcessing {} lines from CSPA file {}".format(line_ct, INFILE)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  ct = 0
  skip_ct = 0
  notfnd = set()
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
        notfnd.add(k)
        logger.warn("No target found for {}".format(k))
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
  print "Processed {} CSPA lines.".format(ct)
  print "  Inserted {} new expression rows for {} targets".format(exp_ct, len(tmark))
  print "  Skipped {} non-high confidence rows".format(skip_ct)
  if notfnd:
    print "  No target found for {} UniProts/GeneIDs. See logfile {} for details".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)
  

if __name__ == '__main__':
  print "\n{} (v{}) [{}]:".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  start_time = time.time()
  load(args)
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))
