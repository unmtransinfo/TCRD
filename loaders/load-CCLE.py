#!/usr/bin/env python
# Time-stamp: <2019-08-20 15:16:04 smathias>
"""
Load CCLE expression data into TCRD from tab-delimited file.

Usage:
    load-CCLE.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-CCLE.py -h | --help

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
__copyright__ = "Copyright 2019, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "1.0.0"

import os,sys,time
from docopt import docopt
from TCRDMP import DBAdaptor
import gzip
import logging
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = 'tcrd6logs/'
LOGFILE = LOGDIR + '%s.log'%PROGRAM
# The input file is produced by the Rscript ../R/process-CCLE.R
# Details/explanation of that code are in ../notebooks/CCLE.ipynb
CCLE_FILE = 'CCLE_DepMap_18q3_RNAseq_RPKM_20180718.gct'
CCLE_TSVGZ_FILE = '../data/CCLE/CCLE.tsv.gz'

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
  dataset_id = dba.ins_dataset( {'name': 'CCLE', 'source': 'File %s from https://portals.broadinstitute.org/ccle', 'app': PROGRAM, 'app_version': __version__, 'url': 'https://portals.broadinstitute.org/ccle'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'expression', 'where_clause': "etype = 'CCLE'"})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)
        
  line_ct = slmf.gzwcl(CCLE_TSVGZ_FILE)
  if not args['--quiet']:
    print "\nProcessing {} lines in processed CCLE file {}".format(line_ct, CCLE_TSVGZ_FILE)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  ct = 0
  pmark = {}
  exp_ct = 0
  dba_err_ct = 0
  with gzip.open(CCLE_TSVGZ_FILE,'rt') as f:
    for line in f:
      ct += 1
      pbar.update(ct)
      if line.startswith('"protein_id"'): # header line
        continue
      # "protein_id"    "cell_id"       "tissue"        "expression"
      line = line.replace('"', '')
      (pid, cell_id, tissue, val) = line.rstrip().split('\t')
      rv = dba.ins_expression( {'protein_id': pid, 'etype': 'CCLE', 'tissue': tissue,
                                'cell_id': cell_id, 'number_value': val} )
      if not rv:
        dba_err_ct += 1
        continue
      exp_ct += 1
      pmark[pid] = True
      
  pbar.finish()
  print "Processed {} lines".format(ct)
  print "  Inserted {} new expression rows for {} proteins.".format(exp_ct, len(pmark))
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
