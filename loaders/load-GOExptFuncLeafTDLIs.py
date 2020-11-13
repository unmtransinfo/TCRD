#!/usr/bin/env python
# Time-stamp: <2020-06-25 12:48:21 smathias>
"""Load Experimental MF/BP Leaf Term GOA tdl_infos into TCRD.

Usage:
    load-GOExptFuncLeafTDLIs.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
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
  -d --debug           : turn on debugging output
  -? --help            : print this message and exit 
"""
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2015-2020, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "3.0.0"

import os,sys,time,re
from docopt import docopt
from TCRD7 import DBAdaptor
from goatools.obo_parser import GODag
import logging
import urllib
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd7logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
# GO OBO file: http://www.geneontology.org/ontology/go.obo
DOWNLOAD_DIR = '../data/GO/'
BASE_URL = 'http://www.geneontology.org/ontology/'
FILENAME = 'go.obo'

def download_goobo(args):
  if os.path.exists(DOWNLOAD_DIR + FILENAME):
    os.remove(DOWNLOAD_DIR + FILENAME)
  if not args['--quiet']:
    print "\nDownloading ", BASE_URL + FILENAME
    print "         to ", DOWNLOAD_DIR + FILENAME
  urllib.urlretrieve(BASE_URL + FILENAME, DOWNLOAD_DIR + FILENAME)
  if not args['--quiet']:
    print "Done."

def load(args, dba, logfile, logger):
  gofile = DOWNLOAD_DIR + FILENAME
  if not args['--quiet']:
    print "\nParsing GO OBO file: {}".format(gofile)
  logger.info("Parsing GO OBO file: {}".format(gofile))
  godag = GODag(gofile)
  
  tct = dba.get_target_count(idg=False)
  if not args['--quiet']:
    print "\nProcessing {} TCRD targets".format(tct)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
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
  print "{} TCRD targets processed.".format(ct)
  print "  Inserted {} new tdl_info rows".format(ti_ct)
  if len(notfnd.keys()) > 0:
    print "WARNING: {} GO terms not found in GODag. See logfile {} for details.".format((len(notfnd.keys()), logfile))
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format((dba_err_ct, logfile))


if __name__ == '__main__':
  print "\n%s (v%s) [%s]:\n" % (PROGRAM, __version__, time.strftime("%c"))
  
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  if args['--logfile']:
    logfile =  args['--logfile']
  else:
    logfile = LOGFILE
  loglevel = int(args['--loglevel'])
  logger = logging.getLogger(__name__)
  logger.setLevel(loglevel)
  if not args['--debug']:
    logger.propagate = False # turns off console logging
  fh = logging.FileHandler(LOGFILE)
  fmtr = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
  fh.setFormatter(fmtr)
  logger.addHandler(fh)

  dba_params = {'dbhost': args['--dbhost'], 'dbname': args['--dbname'], 'logger_name': __name__}
  dba = DBAdaptor(dba_params)
  dbi = dba.get_dbinfo()
  logger.info("Connected to TCRD database {} (schema ver {}; data ver {})".format(args['--dbname'], dbi['schema_ver'], dbi['data_ver']))
  if not args['--quiet']:
    print "Connected to TCRD database {} (schema ver {}; data ver {})".format(args['--dbname'], dbi['schema_ver'], dbi['data_ver'])

  download_goobo(args)
  start_time = time.time()
  load(args, dba, logfile, logger)
  elapsed = time.time() - start_time

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'GO Experimental Leaf Term Flags', 'source': 'IDG-KMC generated data by Steve Mathias at UNM.', 'app': PROGRAM, 'app_version': __version__, 'comments': 'These values are calculated by the loader app and indicate that a protein is annotated with a GO leaf term in either the Molecular Function or Biological Process branch with an experimental evidenve code.'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile {} for details.".format(logfile)
    sys.exit(1)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'tdl_info', 'where_clause': "itype = 'Experimental MF/BP Leaf Term GOA'"})
  if not rv:
    print "WARNING: Error inserting provenance. See logfile {} for details.".format(logfile)
    sys.exit(1)

  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))
