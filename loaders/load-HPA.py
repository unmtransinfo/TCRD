#!/usr/bin/env python
# Time-stamp: <2019-08-16 15:06:52 smathias>
"""Load qualitative HPA expression data and Tissue Specificity Index tdl_infos into TCRD from tab-delimited files.

Usage:
    load-HPA.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>] [--pastid=<int>]
    load-HPA.py -h | --help

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
  -p --pastid PASTID   : TCRD target id to start at (for restarting frozen run)
  -q --quiet           : set output verbosity to minimal level
  -d --debug           : turn on debugging output
  -? --help            : print this message and exit 
"""
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2015-2019, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "3.0.0"

import os,sys,time,re
from docopt import docopt
from TCRDMP import DBAdaptor
import ast
import csv
import logging
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = 'tcrd6logs/'
LOGFILE = LOGDIR+'%s.log'%PROGRAM
# The input files are produced by ../R/process-HPA.R
HPA_FILE = '../data/HPA/HPA.tsv'
HPA_TAU_FILE = '../data/HPA/HPA_TAU.tsv'
# This file contains a manually currated dict mapping tissue names to Uberon IDs.
# These are ones for which TCRDMP.get_uberon_id does not return a uid.
TISSUE2UBERON_FILE = '../data/Tissue2Uberon.txt'

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
  dataset_id = dba.ins_dataset( {'name': 'Human Protein Atlas', 'source': 'IDG-KMC generated data by Steve Mathias at UNM from HPA file http://www.proteinatlas.org/download/normal_tissue.tsv.zip.', 'app': PROGRAM, 'app_version': __version__, 'url': 'http://www.proteinatlas.org/'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'expression', 'where_clause': "etype = 'HPA'", 'comment': 'Qualitative expression values are derived from files from http://www.proteinatlas.org/'},
            {'dataset_id': dataset_id, 'table_name': 'tdl_info', 'where_clause': "itype = 'HPA Tissue Specificity Index'", 'comment': 'Tissue Specificity scores are derived from files from http://www.proteinatlas.org/. The score is the Tau value as descibed in Yanai, I. et. al., Bioinformatics 21(5): 650-659 (2005)'} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

  with open(TISSUE2UBERON_FILE, 'r') as ifh:
    tiss2uid = ast.literal_eval(ifh.read())
  if not args['--quiet']:
    print "\nGot {} tissue to Uberon ID mappings from file {}".format(len(tiss2uid), TISSUE2UBERON_FILE)
    
  line_ct = slmf.wcl(HPA_FILE)
  if not args['--quiet']:
    print "\nProcessing {} lines in HPA file {}".format(line_ct, HPA_FILE)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  ct = 0
  dba_err_ct = 0
  pmark = {}
  exp_ct = 0
  nouid = set()
  with open(HPA_FILE, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    header = tsvreader.next() # skip header line
    ct += 1
    for row in tsvreader:
      # "protein_id"    "Tissue"        "Gene"  "Gene name"     "Level" "Reliability"
      ct += 1
      tissue = row[1]
      init = {'protein_id': row[0], 'etype': 'HPA', 'tissue': tissue, 
              'qual_value': row[4], 'evidence': row[5]} 
      # Add Uberon ID, if we can find one
      if tissue in tiss2uid:
        uberon_id = tiss2uid[tissue]
      else:
        uberon_id = dba.get_uberon_id({'name': tissue})
      if uberon_id:
        init['uberon_id'] = uberon_id
      else:
        nouid.add(tissue)
      rv = dba.ins_expression(init)
      if not rv:
        dba_err_ct += 1
        continue
      exp_ct += 1
      pmark[row[1]] = True
      pbar.update(ct)
  pbar.finish()
  print "Processed {} HPA lines.".format(ct)
  print "  Inserted {} new expression rows for {} proteins.".format(exp_ct, len(pmark))
  if nouid:
    print "No Uberon ID found for {} tissues. See logfile {} for details.".format(len(nouid), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

  line_ct = slmf.wcl(HPA_TAU_FILE)
  if not args['--quiet']:
    print "\nProcessing {} lines in HPA TAU file {}".format(line_ct, HPA_TAU_FILE)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  ct = 0
  dba_err_ct = 0
  pmark = {}
  skip_ct = 0
  ti_ct = 0
  with open(HPA_TAU_FILE, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    header = tsvreader.next() # skip header line
    ct += 1
    for row in tsvreader:
      # "Gene"  "TAU"   "protein_id"
      ct += 1
      pbar.update(ct)
      if row[1] == 'None':
        skip_ct += 1
        continue
      rv = dba.ins_tdl_info({'protein_id': int(row[2]), 'itype': 'HPA Tissue Specificity Index',
                             'number_value': row[1]})
      if not rv:
        dba_err_ct += 1
        continue
      pmark[row[1]] = True
      ti_ct += 1
  pbar.finish()
  print "Processed {} lines.".format(ct)
  print "  Inserted {} new HPA Tissue Specificity Index tdl_info rows for {} proteins.".format(ti_ct, len(pmark))
  if skip_ct:
    print "  Skipped {} rows with no tau.".format(skip_ct)
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
