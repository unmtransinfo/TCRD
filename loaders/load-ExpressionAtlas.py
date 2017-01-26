#!/usr/bin/env python
# Time-stamp: <2017-01-13 12:55:27 smathias>
"""Load disease associations into TCRD from JensenLab DISEASES TSV files..

Usage:
    load-ExpressionAtlas.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-ExpressionAtlas.py -? | --help

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
__copyright__ = "Copyright 2016, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.0.0"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import logging
import csv
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
LOGFILE = "%s.log" % PROGRAM
INPUT_FILE = '../data/ExpressionAtlas/disease_assoc_human_do_uniq.tsv'

def load():
  args = docopt(__doc__, version=__version__)
  debug = int(args['--debug'])
  if debug:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  
  loglevel = int(args['--loglevel'])
  if args['--logfile']:
    logfile = args['--logfile']
  else:
    logfile = "%s.log" % PROGRAM
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
    
  start_time = time.time()
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'Expression Atlas', 'source': 'IDG-KMC generated data by Oleg Ursu at UNM.', 'app': PROGRAM, 'app_version': __version__, 'url': 'https://www.ebi.ac.uk/gxa/', 'comment': 'Disease associations are derived from files from https://www.ebi.ac.uk/gxa/download.html'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'disease', 'where_clause': "dtype = 'Expression Atlas'"})
  if not rv:
    print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
    sys.exit(1)
  
  line_ct = wcl(INPUT_FILE)
  if not args['--quiet']:
    print "\nProcessing %d lines in file %s" % (line_ct, INPUT_FILE)
  with open(INPUT_FILE, 'rU') as tsv:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    tsvreader = csv.reader(tsv, delimiter='\t')
    header = tsvreader.next() # skip header line
    ct = 0
    k2tid = {}
    notfnd = set()
    dis_ct = 0
    dba_err_ct = 0
    for row in tsvreader:
      # "Gene ID"       "DOID"  "Gene Name"     "log2foldchange"        "p-value"       "disease""experiment_id"  "contrast_id"
      ct += 1
      sym = row[2]
      ensg = row[0]
      k = "%s|%s"%(sym,ensg)
      if k in k2tid:
        # we've already found it
        tid = k2tid[k]
      elif k in notfnd:
        # we've already not found it
          continue
      else:
        targets = dba.find_targets({'sym': sym}, idg = False)
        if not targets:
          targets = dba.find_targets_by_xref({'xtype': 'Ensembl', 'value': ensg})
        if not targets:
          notfnd.add(k)
          continue
        t = targets[0]
        tid = t['components']['protein'][0]['id']
        k2tid[k] = tid # save this mapping so we only lookup each target once
      rv = dba.ins_disease( {'target_id': tid, 'dtype': 'Expression Atlas', 'name': row[5],
                             'did': row[1], 'log2foldchange': "%.3f"%float(row[3]), 'pvalue': row[4]} )
      if not rv:
        dba_err_ct += 1
        continue
      dis_ct += 1
      pbar.update(ct)
  pbar.finish()
  elapsed = time.time() - start_time
  print "%d lines processed. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "  %d targets have disease association(s)" % len(k2tid)
  print "  Inserted %d new disease rows" % dis_ct
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)
  if notfnd:
    print "No target found for %d disease association rows." % len(notfnd)


def wcl(fname):
  with open(fname) as f:
    for i, l in enumerate(f):
      pass
  return i + 1

def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])

if __name__ == '__main__':
  print "\n%s (v%s) [%s]:" % (PROGRAM, __version__, time.strftime("%c"))
  load()
  print "\n%s: Done.\n" % PROGRAM
