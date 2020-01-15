#!/usr/bin/env python
# Time-stamp: <2019-04-23 11:51:19 smathias>
"""
Load RGD QTL and terms data into TCRD from tab-delimited files.

Usage:
    load-RGD.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-RGD.py -h | --help

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
import logging
import csv
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = 'tcrd6logs/'
LOGFILE = LOGDIR + '%s.log'%PROGRAM
# The input file is produced by the Rscript ../R/process-RGD.R
# Details/explanation of that code are in ../notebooks/RGD.ipynb
QTL_FILE = '../data/RGD/rat_qtls.tsv'
TERMS_FILE = '../data/RGD/rat_terms.tsv'

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
  dataset_id = dba.ins_dataset( {'name': 'RGD', 'source': 'Files %s and %s produced by UNM KMC group from files from ftp://ftp.rgd.mcw.edu/pub/data_release/', 'app': PROGRAM, 'app_version': __version__, 'url': ''} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  provs = [{'dataset_id': dataset_id, 'table_name': 'rat_term'}, {'dataset_id': dataset_id, 'table_name': 'rat_qtl'}]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)
        
  line_ct = slmf.wcl(QTL_FILE)
  if not args['--quiet']:
    print "\nProcessing {} lines in processed RGD file {}".format(line_ct, QTL_FILE)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  ct = 0
  dba_err_ct = 0
  nhpmark = {}
  qtl_ct = 0
  with open(QTL_FILE, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    header = tsvreader.next() # skip header line
    ct += 1
    for row in tsvreader:
      ct += 1
      # 0 "GENE_RGD_ID"
      # 1 "nhprotein_id"
      # 2 "QTL_RGD_ID"
      # 3 "QTL_SYMBOL"
      # 4 "QTL_NAME"
      # 5 "LOD"
      # 6 "P_VALUE"
      # 7 "TRAIT_NAME"
      # 8 "MEASUREMENT_TYPE"
      # 9 "ASSOCIATED_DISEASES"
      # 10 "PHENOTYPES"
      init = {'nhprotein_id': row[1], 'rgdid': row[0], 'qtl_rgdid': row[2], 
              'qtl_symbol': row[3], 'qtl_name': row[4]}
      if row[5] and row[5] != 'None':
        init['lod'] = row[5]
      if row[6] and row[6] != 'None':
        init['p_value'] = row[6]
      if row[7] and row[7] != 'None':
        init['trait_name'] = row[7]
      if row[8] and row[8] != 'None':
        init['measurement_type'] = row[8]
      if row[9] and row[9] != 'None':
        init['associated_disease'] = row[9]
      if row[10] and row[10] != 'None':
        init['phenotype'] = row[10]
      rv = dba.ins_rat_qtl(init)
      if not rv:
        dba_err_ct += 1
        continue
      qtl_ct += 1
      nhpmark[row[1]] = True
      pbar.update(ct)
  pbar.finish()
  print "Processed {} lines".format(ct)
  print "  Inserted {} new rat_qtl rows for {} nhproteins.".format(qtl_ct, len(nhpmark))
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

  line_ct = slmf.wcl(TERMS_FILE)
  if not args['--quiet']:
    print "\nProcessing {} lines in processed RGD file {}".format(line_ct, TERMS_FILE)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  ct = 0
  dba_err_ct = 0
  term_ct = 0
  with open(TERMS_FILE, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    header = tsvreader.next() # skip header line
    ct += 1
    for row in tsvreader:
      ct += 1
      # 0 "RGD_ID"
      # 1 "OBJECT_SYMBOL"
      # 2 "TERM_ACC_ID"
      # 3 "TERM_NAME"
      # 4 "QUALIFIER"
      # 5 "EVIDENCE"
      # 6 "ONTOLOGY"
      init = {'rgdid': row[0], 'term_id': row[2], 'qtl_symbol': row[3], 'qtl_name': row[4]}
      if row[1] and row[1] != 'None':
        init['obj_symbol'] = row[1]
      if row[3] and row[3] != 'None':
        init['term_name'] = row[3]
      if row[4] and row[4] != 'None':
        init['qualifier'] = row[4]
      if row[5] and row[5] != 'None':
        init['evidence'] = row[5]
      if row[6] and row[6] != 'None':
        init['ontology'] = row[6]
      rv = dba.ins_rat_term(init)
      if not rv:
        dba_err_ct += 1
        continue
      term_ct += 1
      pbar.update(ct)
  pbar.finish()
  print "Processed {} lines".format(ct)
  print "  Inserted {} new rat_term rows.".format(term_ct)
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
