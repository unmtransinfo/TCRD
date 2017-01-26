#!/usr/bin/env python
# Time-stamp: <2017-01-13 12:08:03 smathias>
"""Load Experimental MF/BP Leaf Term GOA tdl_infos into TCRD.

Usage:
    load-GOExptFuncLeafTDLIs.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-GOExptFuncLeafTDLIs.py -h | --help

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
__copyright__ = "Copyright 2015-2016, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.0.0"

import os,sys,time,re
from docopt import docopt
from TCRD import DBAdaptor
from goatools.obo_parser import GODag
import logging
import urllib
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
LOGFILE = './%s.log'%PROGRAM
# GO OBO file: http://www.geneontology.org/ontology/go.obo
DOWNLOAD_DIR = '../data/GO/'
BASE_URL = 'http://www.geneontology.org/ontology/'
FILENAME = 'go.obo'

def download_goobo():
  if os.path.exists(DOWNLOAD_DIR + FILENAME):
    os.remove(DOWNLOAD_DIR + FILENAME)
  start_time = time.time()
  print "\nDownloading ", BASE_URL + FILENAME
  print "         to ", DOWNLOAD_DIR + FILENAME
  urllib.urlretrieve(BASE_URL + FILENAME, DOWNLOAD_DIR + FILENAME)
  elapsed = time.time() - start_time
  print "Done. Elapsed time: %s" % secs2str(elapsed)

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

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'GO Experimental Leaf Term Flags', 'source': 'IDG-KMC generated data by Steve Mathias at UNM.', 'app': PROGRAM, 'app_version': __version__, 'comments': 'These values are calculated by the loader app and indicate that a protein is annotated with a GO leaf term in either the Molecular Function or Biological Process branch with an experimental evidenve code.'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'tdl_info', 'where_clause': "itype = 'Experimental MF/BP Leaf Term GOA'"})
  if not rv:
    print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
    sys.exit(1)

  gofile = DOWNLOAD_DIR + FILENAME
  logger.info("Parsing GO OBO file: %s" % gofile)
  godag = GODag(gofile)
  
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  tct = dba.get_target_count(idg=False)
  if not args['--quiet']:
    print "\nProcessing %d TCRD targets" % tct
  pbar = ProgressBar(widgets=pbar_widgets, maxval=tct).start()
  ct = 0
  ti_ct = 0
  notfnd = {}
  dba_err_ct = 0
  exp_codes = ['EXP', 'IDA', 'IPI', 'IMP', 'IGI', 'IEP']
  for t in dba.get_targets(idg=False, include_annotations=True):
    ct += 1
    p = t['components']['protein'][0]
    if 'goas' in p:
      lfe_goa_strs = []
      for d in p['goas']:
        if d['go_term'].startswith('C'): continue # only want MF/BP terms
        ev = d['evidence']
        if ev not in exp_codes: continue # only want experimental evidence GOAs
        gt = godag.query_term(d['go_id'])
        if not gt:
          k = "%s:%s" % (d['go_id'], d['go_term'])
          notfnd[k] = True
          logger.error("GO term %s not found in GODag" % k)
          continue
        if len(gt.children) == 0: # if it's a leaf node
          lfe_goa_strs.append("%s|%s|%s"%(d['go_id'], d['go_term'], ev))
      if lfe_goa_strs:
        rv = dba.ins_tdl_info({'protein_id': p['id'], 'itype': 'Experimental MF/BP Leaf Term GOA', 'string_value': "; ".join(lfe_goa_strs)})
        if not rv:
          dba_err_ct += 1
          continue
        ti_ct += 1
    pbar.update(ct)
  pbar.finish()
  
  elapsed = time.time() - start_time
  print "%d TCRD targets processed. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "  Inserted %d new  tdl_info rows" % ti_ct
  if len(notfnd.keys()) > 0:
    print "WARNING: %d GO terms not found in GODag. See logfile %s for details." % (len(notfnd.keys()), logfile)
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)

def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])

if __name__ == '__main__':
  print "\n%s (v%s) [%s]:" % (PROGRAM, __version__, time.strftime("%c"))
  download_goobo()
  load()
  print "\n%s: Done.\n" % PROGRAM
