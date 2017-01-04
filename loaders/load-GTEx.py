#!/usr/bin/env python
# Time-stamp: <2017-01-04 12:32:56 smathias>
"""
Load GTEx expression data into TCRD from tab-delimited files.

Usage:
    load-GTEx.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
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
import csv
import cPickle as pickle
import logging
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
GTEX_QUAL_FILE = '/data/GTEx/gtex.rpkm.qualitative.2016-03-29.tsv'
GTEX_TAU_FILE = '/data/GTEx/gtex.tau.2016-03-29.tsv'

def load():
  args = docopt(__doc__, version=__version__)
  debug = int(args['--debug'])
  if debug:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  loglevel = int(args['--loglevel'])
  if args['--logfile']:
    logfile = args['--logfile']
  else:
    logfile = LOGFILE
  logger = logging.getLogger(__name__)
  logger.setLevel(loglevel)
  if not debug:
    logger.propagate = False # turns off console logging when debug is 0
  fh = logging.FileHandler(logfile)
  fmtr = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
  fh.setFormatter(fmtr)
  logger.addHandler(fh)
  
  # DBAdaptor uses same logger as main()
  dba_params = {'dbhost': args['--dbhost'], 'dbname': args['--dbname'], 'logger_name': __name__}
  dba = DBAdaptor(dba_params)
  dbi = dba.get_dbinfo()
  logger.info("Connected to TCRD database %s (schema ver %s; data ver %s)", args['--dbname'], dbi['schema_ver'], dbi['data_ver'])
  if not args['--quiet']:
    print "\nConnected to TCRD database %s (schema ver %s; data ver %s)" % (args['--dbname'], dbi['schema_ver'], dbi['data_ver'])

  # Provenance
  provs = [ {'dataset_id': 2, 'table_name': 'expression', 'where_clause': "etype = 'GTEx'", 'comment': 'Log Median and qualitative expression values are derived from files from http://www.gtexportal.org/home/datasets2'},
            {'dataset_id': 2, 'table_name': 'tdl_info', 'where_clause': "itype = 'GTEx Tissue Specificity Index'", 'comment': 'Tissue Specificity scores are derived from files from http://www.gtexportal.org/home/datasets2. The score is the Tau value as descibed in Yanai, I. et. al., Bioinformatics 21(5): 650-659 (2005)'} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    if not rv:
      print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
      sys.exit(1)
        
  ensg2pid = {}

  start_time = time.time()
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  line_ct = wcl(GTEX_QUAL_FILE)
  line_ct -= 1 # file has header
  if not quiet:
    print "\nProcessing %d records in GTEx file %s" % (line_ct, GTEX_QUAL_FILE)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  notfnd = {}
  ct = 0
  dba_err_ct = 0
  tmark = {}
  exp_ct = 0
  with open(GTEX_QUAL_FILE, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    header = tsvreader.next() # skip header line
    for row in tsvreader:
      # "ENSG"  "SMTSD" "MEDIAN_RPKM"   "LEVEL" "LOG_MEDIAN_RPKM"       "AGE"   "GENDER"
      ct += 1
      pbar.update(ct)
      ensg = re.sub('\.\d+$', '', row[0]) # get rid of version
      if ensg in ensg2pid:
        # we've already found it
        pid = ensg2pid[ensg]
      elif ensg in notfnd:
        # if we didn't find it once, trying again won't help
        continue
      else:
        targets = dba.find_targets_by_xref({'xtype': 'Ensembl', 'value': ensg}, False)
        if not targets:
          notfnd[ensg] = True # save this mapping so we only lookup each target once
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
      logger.info("Inserted exp for row %d" % ct)
      exp_ct += 1
  pbar.finish()
  elapsed = time.time() - start_time
  print "Processed %d GTEx records. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "  Inserted %d new expression rows" % exp_ct
  print "  %d targets have GTEx expression data (%d ENSGs)" % (len(tmark.keys()), len(ensg2pid.keys()))
  if notfnd:
    print "  No target found for %d ENSGs." % len(notfnd.keys())
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)
  pfile = 'tcrd4logs/GTEx-ENSG2PID.p'
  print "Dumping ENSG to protein_id mapping to %s" % pfile
  pickle.dump(ensg2pid, open(pfile, 'wb'))
  
  start_time = time.time()
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  line_ct = wcl(GTEX_TAU_FILE)
  line_ct -= 1 # file has header
  if not quiet:
    print "\nProcessing %d input lines in Tissue Specificity Index file %s" % (line_ct, GTEX_TAU_FILE)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  with open(GTEX_TAU_FILE, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    header = tsvreader.next() # skip header line
    ct = 0
    dba_err_ct = 0
    tmark = {}
    notfnd = {}
    ti_ct = 0
    for row in tsvreader:
      ct += 1
      pbar.update(ct)
      ensg = re.sub('\.\d+$', '', row[0]) # get rid of version
      tau = row[1]
      if ensg not in ensg2pid:
        notfnd[ensg] = True
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
  print "Processed %d tau lines. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "  %d targets have GTEx tau" % len(tmark.keys())
  if notfnd:
    print "  %d ENSGs not in map from medians file" % len(notfnd.keys())
  print "  Inserted %d new GTEx Tissue Specificity Index tdl_info rows" % ti_ct
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)

  print "\n%s: Done.\n" % PROGRAM


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
