#!/usr/bin/env python
# Time-stamp: <2019-08-20 10:28:53 smathias>
""" Load qualitative HPM expression data and Tissue Specificity Index tdl_infos into TCRD from tab-delimited files.

Usage:
    load-HPM.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-HPM.py -h | --help

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
LOGFILE = LOGDIR+'%s.log'%PROGRAM
# This file contains a manually currated dict mapping tissue names to Uberon IDs.
# These are ones for which TCRDMP.get_uberon_id does not return a uid.
TISSUE2UBERON_FILE = '../data/Tissue2Uberon.txt'
# 
PROTEIN_QUAL_FILE = '../data/HPM/HPM.protein.qualitative.2015-09-10.tsv'
PROTEIN_TAU_FILE = '../data/HPM/HPM.protein.tau.2015-09-10.tsv'
GENE_QUAL_FILE = '../data/HPM/HPM.gene.qualitative.2015-09-10.tsv'
GENE_TAU_FILE = '../data/HPM/HPM.gene.tau.2015-09-10.tsv'

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
  dataset_id = dba.ins_dataset( {'name': 'Human Proteome Map', 'source': 'IDG-KMC generated data by Oleg Ursu at UNM.', 'app': PROGRAM, 'app_version': __version__, 'url': 'http://www.humanproteomemap.org/'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'expression', 'where_clause': "etype = 'HPM Protein'", 'comment': 'Log Median and qualitative expression values are derived from files from http://www.humanproteomemap.org/download.php'},
            {'dataset_id': dataset_id, 'table_name': 'expression', 'where_clause': "etype = 'HPM Gene'", 'comment': 'Log Median and qualitative expression values are derived from files from http://www.humanproteomemap.org/download.php'},
            {'dataset_id': dataset_id, 'table_name': 'tdl_info', 'where_clause': "itype = 'HPM Protein Tissue Specificity Index'", 'comment': 'Tissue Specificity scores are derived from files from http://www.humanproteomemap.org/download.php. The score is the Tau value as descibed in Yanai, I. et. al., Bioinformatics 21(5): 650-659 (2005)'},
            {'dataset_id': dataset_id, 'table_name': 'tdl_info', 'where_clause': "itype = 'HPM Gene Tissue Specificity Index'", 'comment': 'Tissue Specificity scores are derived from files from http://www.humanproteomemap.org/download.php. The score is the Tau value as descibed in Yanai, I. et. al., Bioinformatics 21(5): 650-659 (2005)'}]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]

  with open(TISSUE2UBERON_FILE, 'r') as ifh:
    tiss2uid = ast.literal_eval(ifh.read())
  if not args['--quiet']:
    print "\nGot {} tissue to Uberon ID mappings from file {}".format(len(tiss2uid), TISSUE2UBERON_FILE)
  
  #
  # Protein Level Expressions
  #
  line_ct = slmf.wcl(PROTEIN_QUAL_FILE)
  if not args['--quiet']:
    print "\nProcessing {} lines in HPM file {}".format(line_ct, PROTEIN_QUAL_FILE)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  ct = 0
  rs2pids = defaultdict(list)
  notfnd = set()
  nouid = set()
  dba_err_ct = 0
  pmark = {}
  exp_ct = 0
  with open(PROTEIN_QUAL_FILE, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    header = tsvreader.next() # skip header line
    ct += 1
    for row in tsvreader:
      ct += 1
      pbar.update(ct)
      #rs = re.sub('\.\d+$', '', row[0]) # get rid of version
      rs = row[0]
      if rs in rs2pids:
        # we've already found it
        pids = rs2pids[rs]
      elif rs in notfnd:
        # we've already not found it
        continue
      else:
        # look it up
        targets = dba.find_targets_by_xref({'xtype': 'RefSeq', 'value': rs}, False)
        if not targets:
          notfnd.add(rs)
          continue
        pids = []
        for t in targets:
          pids.append(t['components']['protein'][0]['id'])
        rs2pids[rs] = pids # save this mapping so we only lookup each target once
      tissue = row[1]
      if row[3] == 'NA':
        init = {'etype': 'HPM Protein', 'tissue': tissue, 'qual_value': row[4],}
      else:
        init = {'etype': 'HPM Protein','tissue': tissue, 
                'qual_value': row[4], 'number_value': row[3]}
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
        rv = dba.ins_expression(init)
        if not rv:
          dba_err_ct += 1
          continue
        exp_ct += 1
        pmark[pid] = True
  pbar.finish()
  print "Processed {} lines.".format(ct)
  print "  Inserted {} new expression rows for {} proteins ({} RefSeqs)".format(exp_ct, len(pmark), len(rs2pids))
  if notfnd:
    print "No target found for {} RefSeqs. See logfile {} for details.".format(len(notfnd), logfile)
  if nouid:
    print "No Uberon ID found for {} tissues. See logfile {} for details.".format(len(nouid), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

  line_ct = slmf.wcl(PROTEIN_TAU_FILE)
  if not args['--quiet']:
    print "\nProcessing {} lines in Tissue Specificity Index file {}".format(line_ct, PROTEIN_TAU_FILE)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  ct = 0
  dba_err_ct = 0
  pmark = {}
  skip_ct = 0
  ti_ct = 0
  with open(PROTEIN_TAU_FILE, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    header = tsvreader.next() # skip header line
    ct += 1
    for row in tsvreader:
      ct += 1
      pbar.update(ct)
      #rs = re.sub('\.\d+$', '', row[0]) # get rid of version
      rs = row[0]
      tau = row[1]
      if rs not in rs2pids:
        skip_ct += 1
        continue
      for pid in rs2pids[rs]:
        rv = dba.ins_tdl_info({'protein_id': pid, 'itype': 'HPM Protein Tissue Specificity Index',
                               'number_value': tau})
        if not rv:
          dba_err_ct += 1
          continue
        ti_ct += 1
        pmark[pid] = True
  pbar.finish()
  print "Processed {} lines.".format(ct)
  print "  Inserted {} new HPM Protein Tissue Specificity Index tdl_info rows for {} proteins.".format(ti_ct, len(pmark))
  if skip_ct > 0:
    print "  Skipped {} rows with RefSeqs not in map from expression file.".format(skip_ct)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

  #
  # Gene Level Expressions
  #
  line_ct = slmf.wcl(GENE_QUAL_FILE)
  if not args['--quiet']:
    print "\nProcessing {} lines in HPM file {}".format(line_ct, GENE_QUAL_FILE)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  ct = 0
  sym2pids = defaultdict(list)
  notfnd = set()
  nouid = set()
  dba_err_ct = 0
  pmark = {}
  exp_ct = 0
  with open(GENE_QUAL_FILE, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    header = tsvreader.next() # skip header line
    ct += 1
    for row in tsvreader:
      ct += 1
      pbar.update(ct)
      sym = re.sub('\.\d+$', '', row[0]) # get rid of version
      if sym in sym2pids:
        pids = sym2pids[sym]
      elif sym in notfnd:
        # we've already not found it
        continue
      else:
        # look it up
        targets = dba.find_targets({'sym': sym}, False)
        if not targets:
          notfnd.add(sym)
          continue
        pids = []
        for t in targets:
          pids.append(t['components']['protein'][0]['id'])
        sym2pids[sym] = pids # save this mapping so we only lookup each target once
      tissue = row[1]
      
      if row[3] == 'NA':
        init = {'etype': 'HPM Gene', 'tissue': tissue, 'qual_value': row[4],}
      else:
        init = {'etype': 'HPM Gene','tissue': tissue, 
                'qual_value': row[4], 'number_value': row[3]}
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
        rv = dba.ins_expression(init)
        if not rv:
          dba_err_ct += 1
          continue
        exp_ct += 1
        pmark[pid] = True
  pbar.finish()
  print "Processed {} lines.".format(ct)
  print "  Inserted {} new expression rows for {} proteins ({} Gene Symbols)".format(exp_ct, len(pmark), len(sym2pids))
  if notfnd:
    print "  No target found for {} symbols. See logfile {} for details.".format(len(notfnd), logfile)
  if nouid:
    print "No Uberon ID found for {} tissues. See logfile {} for details.".format(len(nouid), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

  line_ct = slmf.wcl(GENE_TAU_FILE)
  if not args['--quiet']:
    print "\nProcessing {} lines in Tissue Specificity Index file {}".format(line_ct, GENE_TAU_FILE)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  ct = 0
  dba_err_ct = 0
  pmark = {}
  skip_ct = 0
  ti_ct = 0
  with open(GENE_TAU_FILE, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    header = tsvreader.next() # skip header line
    ct += 1
    for row in tsvreader:
      ct += 1
      pbar.update(ct)
      sym = re.sub('\.\d+$', '', row[0]) # get rid of version
      tau = row[1]
      if sym not in sym2pids:
        skip_ct += 1
        continue
      for pid in rs2pids[rs]:
        rv = dba.ins_tdl_info({'protein_id': pid, 'itype': 'HPM Gene Tissue Specificity Index',
                               'number_value': tau})
        if not rv:
          dba_err_ct += 1
          continue
        ti_ct += 1
        pmark[pid] = True
  pbar.finish()
  print "Processed {} lines.".format(ct)
  print "  Inserted {} new HPM Gene Tissue Specificity Index tdl_info rows for {} proteins.".format(ti_ct, len(pmark))
  if skip_ct > 0:
    print "  Skipped {} rows with symbols not in map from expression file".format(skip_ct)
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
