#!/usr/bin/env python
# Time-stamp: <2019-08-16 11:09:40 smathias>
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
__copyright__ = "Copyright 2015-2019, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "3.0.0"

import os,sys,time,re
from docopt import docopt
from TCRDMP import DBAdaptor
import ast
import csv
from collections import defaultdict
import logging
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = 'tcrd6logs/'
LOGFILE = LOGDIR + '%s.log'%PROGRAM
# This file contains a manually currated dict mapping tissue names to Uberon IDs.
# These are ones for which TCRDMP.get_uberon_id does not return a uid.
TISSUE2UBERON_FILE = '../data/Tissue2Uberon.txt'
# File prepared by Jeremy Yang
# See https://github.com/unmtransinfo/expression-profiles
GTEX_FILE = '../data/GTEx/gtex_rnaseq_sabv_alltissues.tsv'

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
  dataset_id = dba.ins_dataset( {'name': 'GTEx', 'source': 'IDG-KMC generated data by Jeremy Yang at UNM from GTEx files.', 'app': PROGRAM, 'app_version': __version__, 'url': 'http://www.gtexportal.org/home/'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'expression', 'where_clause': "etype = 'GTEx'", 'comment': 'Pre-processing code can be found here: https://github.com/unmtransinfo/expression-profiles'},
            {'dataset_id': dataset_id, 'table_name': 'tdl_info', 'where_clause': "itype = 'GTEx Tissue Specificity Index'", 'comment': 'Tissue Specificity scores are derived from GTEx files. The score is the Tau value as descibed in Yanai, I. et. al., Bioinformatics 21(5): 650-659 (2005)'} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

  with open(TISSUE2UBERON_FILE, 'r') as ifh:
    tiss2uid = ast.literal_eval(ifh.read())
  if not args['--quiet']:
    print "\nGot {} tissue to Uberon ID mappings from file {}".format(len(tiss2uid), TISSUE2UBERON_FILE)
  
  line_ct = slmf.wcl(GTEX_FILE)
  if not args['--quiet']:
    print "\nProcessing {} lines in GTEx file {}".format(line_ct, GTEX_FILE)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  ct = 0
  ensg2pids = defaultdict(list)
  notfnd = set()
  nouid = set()
  dba_err_ct = 0
  pmark = {}
  exp_ct = 0
  with open(GTEX_FILE, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    header = tsvreader.next() # skip header line
    ct += 1
    for row in tsvreader:
      # ENSG    SMTSD   SEX     TPM     TAU     TAU_BYSEX       TPM_RANK        TPM_RANK_BYSEX  TPM_LEVEL TPM_LEVEL_BYSEX TPM_F   TPM_M   log2foldchange
      ct += 1
      pbar.update(ct)
      ensg = re.sub('\.\d+$', '', row[0]) # get rid of version if present
      if ensg in ensg2pids:
        # we've already found it
        pids = ensg2pids[ensg]
      elif ensg in notfnd:
        # we've already not found it
        continue
      else:
        # look it up
        targets = dba.find_targets_by_xref({'xtype': 'Ensembl', 'value': ensg}, False)
        if not targets:
          notfnd.add(ensg)
          continue
        pids = []
        for t in targets:
          pids.append(t['components']['protein'][0]['id'])
        ensg2pids[ensg] = pids # save this mapping so we only lookup each target once
      tissue = row[1]
      init = {'tissue': tissue, 'gender': row[2], 'tpm': row[3], 'tpm_rank': row[6],
              'tpm_rank_bysex': row[7], 'tpm_level': row[8], 'tpm_level_bysex': row[9],
              'tau': row[4], 'tau_bysex': row[5]}
      if row[10]:
        init['tpm_f'] = row[10]
      if row[11]:
        init['tpm_m'] = row[11]
      if row[12]:
        init['log2foldchange'] = row[12]
      # Add Uberon ID, if we can find one
      if tissue in tiss2uid:
        uberon_id = tiss2uid[tissue]
      else:
        uberon_id = dba.get_uberon_id({'name': tissue})
      if uberon_id:
        init['uberon_id'] = uberon_id
      else:
        nouid.add(tissue)
      for pid in pids:
        init['protein_id'] = pid
        rv = dba.ins_gtex(init)
        if not rv:
          dba_err_ct += 1
          continue
        exp_ct += 1
        pmark[pid] = True
  pbar.finish()
  for ensg in notfnd:
    logger.warn("No target found for {}".format(ensg))
  for t in nouid:
    logger.warn("No Uberon ID found for {}".format(t))
  print "Processed {} lines".format(ct)
  print "  Inserted {} new expression rows for {} proteins ({} ENSGs)".format(exp_ct, len(pmark), len(ensg2pids))
  if notfnd:
    print "  No target found for {} ENSGs. See logfile {} for details.".format(len(notfnd), logfile)
  if nouid:
    print "No Uberon ID found for {} tissues. See logfile {} for details.".format(len(nouid), logfile)
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
