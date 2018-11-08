#!/usr/bin/env python
# Time-stamp: <2018-04-05 10:11:55 smathias>
"""
Load GTEx expression data into TCRD from tab-delimited files.

Usage:
    load-GTEx.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-GTEx.py -h | --help

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
__copyright__ = "Copyright 2015-2018, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.1.0"

import os,sys,time,re
from docopt import docopt
from TCRD import DBAdaptor
import csv
import cPickle as pickle
import logging
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = 'tcrd5logs/'
LOGFILE = LOGDIR + '%s.log'%PROGRAM
GTEX_QUAL_FILE = '../data/GTEx/gtex.tpm.qualitative.2017-10-06.tsv'
GTEX_TAU_FILE = '../data/GTEx/gtex.tau.2017-10-06.tsv'

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
  dataset_id = dba.ins_dataset( {'name': 'GTEx', 'source': 'IDG-KMC generated data by Oleg Ursu at UNM.', 'app': PROGRAM, 'app_version': __version__, 'url': 'http://www.gtexportal.org/home/'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'expression', 'where_clause': "etype = 'GTEx'", 'comment': 'Log Median and qualitative expression values are derived from files from http://www.gtexportal.org/home/datasets2'},
            {'dataset_id': dataset_id, 'table_name': 'tdl_info', 'where_clause': "itype = 'GTEx Tissue Specificity Index'", 'comment': 'Tissue Specificity scores are derived from files from http://www.gtexportal.org/home/datasets2. The score is the Tau value as descibed in Yanai, I. et. al., Bioinformatics 21(5): 650-659 (2005)'} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)
        
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  ensg2pid = {}

  line_ct = slmf.wcl(GTEX_QUAL_FILE)
  if not args['--quiet']:
    print "\nProcessing {} lines in GTEx file {}".format(line_ct, GTEX_QUAL_FILE)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  notfnd = set()
  ct = 0
  dba_err_ct = 0
  tmark = {}
  exp_ct = 0
  with open(GTEX_QUAL_FILE, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    header = tsvreader.next() # skip header line
    ct += 1
    for row in tsvreader:
      # "ENSG"  "SMTSD" "MEDIAN_TPM"   "LEVEL" "LOG_MEDIAN_TPM"       "AGE"   "GENDER"
      ct += 1
      pbar.update(ct)
      ensg = re.sub('\.\d+$', '', row[0]) # get rid of version
      if ensg in ensg2pid:
        # we've already found it
        pid = ensg2pid[ensg]
      elif ensg in notfnd:
        # we've already not found it
        continue
      else:
        targets = dba.find_targets_by_xref({'xtype': 'Ensembl', 'value': ensg}, False)
        if not targets:
          notfnd.add(ensg)
          logger.warn("No target found for {}".format(ensg))
          continue
        t = targets[0]
        tmark[t['id']] = True
        pid = t['components']['protein'][0]['id']
        ensg2pid[ensg] = pid # save this mapping so we only lookup each target once
      if row[4] == 'NA':
        init = {'protein_id': pid,'etype': 'GTEx', 'tissue': row[1], 'qual_value': row[3]}
      else:
        init = {'protein_id': pid, 'etype': 'GTEx','tissue': row[1], 
                'qual_value': row[3], 'number_value': row[4]}
      if row[5]:
        init['age'] = row[5]
      if row[6]:
        init['gender'] = row[6]
      rv = dba.ins_expression(init)
      if not rv:
        dba_err_ct += 1
        continue
      exp_ct += 1
  pbar.finish()
  print "Processed {} lines".format(ct)
  print "  Inserted {} new expression rows for {} targets ({} ENSGs)".format(exp_ct, len(tmark), len(ensg2pid))
  if notfnd:
    print "  No target found for {} ENSGs. See logfile {} for details.".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)
  #pfile = LOGDIR + 'GTEx-ENSG2PID.p'
  #print "Dumping ENSG to protein_id mapping to %s" % pfile
  #pickle.dump(ensg2pid, open(pfile, 'wb'))
  
  line_ct = slmf.wcl(GTEX_TAU_FILE)
  if not args['--quiet']:
    print "\nProcessing {} lines in Tissue Specificity Index file {}".format(line_ct, GTEX_TAU_FILE)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  ct = 0
  dba_err_ct = 0
  tmark = {}
  notfnd = set()
  ti_ct = 0
  with open(GTEX_TAU_FILE, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    header = tsvreader.next() # skip header line
    ct += 1
    for row in tsvreader:
      ct += 1
      pbar.update(ct)
      ensg = re.sub('\.\d+$', '', row[0]) # get rid of version
      tau = row[1]
      if ensg not in ensg2pid:
        notfnd.add(ensg)
        continue
      pid = ensg2pid[ensg]
      tmark[pid] = True
      rv = dba.ins_tdl_info({'protein_id': pid, 'itype': 'GTEx Tissue Specificity Index',
                             'number_value': tau})
      if not rv:
        dba_err_ct += 1
        continue
      ti_ct += 1
  pbar.finish()
  elapsed = time.time() - start_time
  print "Processed {} lines".format(ct)
  print "  Inserted {} new GTEx Tissue Specificity Index tdl_info rows for {} targets".format(ti_ct, len(tmark))
  if notfnd:
    print "  {} ENSGs not in map from expression file".format(len(notfnd))
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
