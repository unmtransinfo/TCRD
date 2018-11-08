#!/usr/bin/env python
# Time-stamp: <2018-04-03 10:03:32 smathias>
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
__copyright__ = "Copyright 2015-2018, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.1.0"

import os,sys,time,re
from docopt import docopt
import csv
from TCRD import DBAdaptor
import logging
import cPickle as pickle
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = 'tcrd5logs/'
LOGFILE = LOGDIR+'%s.log'%PROGRAM
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
  
  #
  # Protein Level Expressions
  #
  line_ct = slmf.wcl(PROTEIN_QUAL_FILE)
  if not args['--quiet']:
    print "\nProcessing {} lines in HPM file {}".format(line_ct, PROTEIN_QUAL_FILE)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  rs2pid = {}
  notfnd = set()
  ct = 0
  dba_err_ct = 0
  tmark = {}
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
      if rs in rs2pid:
        pid = rs2pid[rs]
      elif rs in notfnd:
        continue
      else:
        targets = dba.find_targets_by_xref({'xtype': 'RefSeq', 'value': rs}, False)
        if not targets:
          notfnd.add(rs)
          continue
        t = targets[0]
        tmark[t['id']] = True
        pid = t['components']['protein'][0]['id']
        rs2pid[rs] = pid # save this mapping so we only lookup each target once
      if row[3] == 'NA':
        init = {'protein_id': pid,'etype': 'HPM Protein', 'tissue': row[1], 'qual_value': row[4],}
      else:
        init = {'protein_id': pid, 'etype': 'HPM Protein','tissue': row[1], 
                'qual_value': row[4], 'number_value': row[3]}
      rv = dba.ins_expression(init)
      if not rv:
        dba_err_ct += 1
        continue
      exp_ct += 1
  pbar.finish()
  print "Processed {} lines.".format(ct)
  print "  Inserted {} new expression rows for {} targets ({} RefSeqs)".format(exp_ct, len(tmark), len(rs2pid))
  if notfnd:
    print "No target found for {} RefSeqs. See logfile {} for details.".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)
  #pfile = LOGDIR + 'HPMP-RefSeq2PID.p'
  #print "Dumping ENSG to protein_id mapping to {}".format(pfile)
  #pickle.dump(rs2pid, open(pfile, 'wb'))

  line_ct = slmf.wcl(PROTEIN_TAU_FILE)
  if not args['--quiet']:
    print "\nProcessing {} lines in Tissue Specificity Index file {}".format(line_ct, PROTEIN_TAU_FILE)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  ct = 0
  dba_err_ct = 0
  tmark = {}
  notfnd = set()
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
      if rs not in rs2pid:
        notfnd.add(rs)
        continue
      pid = rs2pid[rs]
      tmark[pid] = True
      rv = dba.ins_tdl_info({'protein_id': pid, 'itype': 'HPM Protein Tissue Specificity Index',
                             'number_value': tau})
      if not rv:
        dba_err_ct += 1
        continue
      ti_ct += 1
  pbar.finish()
  print "Processed {} lines.".format(ct)
  print "  Inserted {} new HPM Protein Tissue Specificity Index tdl_info rows for {} targets".format(ti_ct, len(tmark))
  if notfnd:
    print "  {} RefSeqs not in map from expression file".format(len(notfnd))
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

  #
  # Gene Level Expressions
  #
  line_ct = slmf.wcl(GENE_QUAL_FILE)
  if not args['--quiet']:
    print "\nProcessing {} lines in HPM file {}".format(line_ct, GENE_QUAL_FILE)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  sym2pid = {}
  notfnd = set()
  ct = 0
  dba_err_ct = 0
  tmark = {}
  exp_ct = 0
  with open(GENE_QUAL_FILE, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    header = tsvreader.next() # skip header line
    ct += 1
    for row in tsvreader:
      ct += 1
      pbar.update(ct)
      sym = re.sub('\.\d+$', '', row[0]) # get rid of version
      if sym in sym2pid:
        pid = sym2pid[sym]
      elif sym in notfnd:
        continue
      else:
        targets = dba.find_targets({'sym': sym}, False)
        if not targets:
          notfnd.add(sym)
          continue
        t = targets[0]
        tmark[t['id']] = True
        pid = t['components']['protein'][0]['id']
        sym2pid[sym] = pid # save this mapping so we only lookup each target once
      if row[3] == 'NA':
        init = {'protein_id': pid,'etype': 'HPM Gene', 'tissue': row[1], 'qual_value': row[4],}
      else:
        init = {'protein_id': pid, 'etype': 'HPM Gene','tissue': row[1], 
                'qual_value': row[4], 'number_value': row[3]}
      rv = dba.ins_expression(init)
      if not rv:
        dba_err_ct += 1
        continue
      exp_ct += 1
  pbar.finish()
  print "Processed {} lines.".format(ct)
  print "  Inserted {} new expression rows for {} targets ({} Gene Symbols)".format(exp_ct, len(tmark.keys()), len(sym2pid))
  if notfnd:
    print "  No target found for {} symbols. See logfile {} for details.".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)
  #pfile = LOGDIR + 'HPMG-Sym2PID.p'
  #print "Dumping symbol to protein_id mapping to {}".format(pfile)
  #pickle.dump(sym2pid, open(pfile, 'wb'))

  line_ct = slmf.wcl(GENE_TAU_FILE)
  if not args['--quiet']:
    print "\nProcessing {} lines in Tissue Specificity Index file {}".format(line_ct, GENE_TAU_FILE)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  ct = 0
  dba_err_ct = 0
  tmark = {}
  notfnd = set()
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
      if sym not in sym2pid:
        notfnd.add(sym)
        continue
      pid = sym2pid[sym]
      tmark[pid] = True
      rv = dba.ins_tdl_info({'protein_id': pid, 'itype': 'HPM Gene Tissue Specificity Index',
                             'number_value': tau})
      if not rv:
        dba_err_ct += 1
        continue
      ti_ct += 1
  pbar.finish()
  print "Processed {} lines.".format(ct)
  print "  Inserted {} new HPM Gene Tissue Specificity Index tdl_info rows for {} targets".format(ti_ct, len(tmark))
  if notfnd:
    print "  {} symbols not in map from expression file".format(len(notfnd))
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
