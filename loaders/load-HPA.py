#!/usr/bin/env python
# Time-stamp: <2017-01-13 12:48:37 smathias>
"""Load qualitative HPA expression data and Tissue Specificity Index tdl_infos into TCRD from tab-delimited files.

Usage:
    load-HPA.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>] [--pastid=<int>]
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
  -d --debug DEBUGL    : set debugging output level (0-3) [default: 0]
  -? --help            : print this message and exit 
"""
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2015-2017, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.0.0"

import os,sys,time,re
from docopt import docopt
import csv
from TCRD import DBAdaptor
import logging
import cPickle as pickle
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = 'tcrd4logs/'
LOGFILE = LOGDIR+'%s.log'%PROGRAM
PROTEIN_QUAL_FILE = '../data/HPA/HPA.Protein.expression.qualitative.2015-09-09.tsv'
PROTEIN_TAU_FILE = '../data/HPA/HPA.Protein.tau.2015-09-09.tsv'
RNA_QUAL_FILE = '../data/HPA/HPA.RNA.expression.qualitative.2015-09-09.tsv'
RNA_TAU_FILE = '../data/HPA/HPA.RNA.tau.2015-09-09.tsv'

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

  dba_params = {'dbhost': args['--dbhost'], 'dbname': args['--dbname'], 'logger_name': __name__}
  dba = DBAdaptor(dba_params)
  dbi = dba.get_dbinfo()
  logger.info("Connected to TCRD database %s (schema ver %s; data ver %s)", args['--dbname'], dbi['schema_ver'], dbi['data_ver'])
  if not args['--quiet']:
    print "\nConnected to TCRD database %s (schema ver %s; data ver %s)" % (args['--dbname'], dbi['schema_ver'], dbi['data_ver'])
  
  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'Human Protein Atlas', 'source': 'IDG-KMC generated data by Oleg Ursu at UNM.', 'app': PROGRAM, 'app_version': __version__, 'url': 'http://www.proteinatlas.org/'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'expression', 'where_clause': "etype = 'HPA Protein'", 'comment': 'Log Median and qualitative expression values are derived from files from http://www.proteinatlas.org/'},
            {'dataset_id': dataset_id, 'table_name': 'expression', 'where_clause': "etype = 'HPA RNA'", 'comment': 'Log Median and qualitative expression values are derived from files from http://www.proteinatlas.org/'},
            {'dataset_id': dataset_id, 'table_name': 'tdl_info', 'where_clause': "itype = 'HPA Protein Tissue Specificity Index'", 'comment': 'Tissue Specificity scores are derived from files from http://www.proteinatlas.org/. The score is the Tau value as descibed in Yanai, I. et. al., Bioinformatics 21(5): 650-659 (2005)'},
            {'dataset_id': dataset_id, 'table_name': 'tdl_info', 'where_clause': "itype = 'HPA RNA Tissue Specificity Index'", 'comment': 'Tissue Specificity scores are derived from files from http://www.proteinatlas.org/. The score is the Tau value as descibed in Yanai, I. et. al., Bioinformatics 21(5): 650-659 (2005)'}]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    if not rv:
      print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
      sys.exit(1)

  start_time = time.time()
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]

  #
  # Protein Level Expressions
  #
  line_ct = wcl(PROTEIN_QUAL_FILE)
  line_ct -= 1 # file has header
  if not args['--quiet']:
    print "\nProcessing %d records in HPA file %s" % (line_ct, PROTEIN_QUAL_FILE)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  ensg2pid = {}
  notfnd = {}
  ct = 0
  dba_err_ct = 0
  tmark = {}
  exp_ct = 0
  with open(PROTEIN_QUAL_FILE, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    header = tsvreader.next() # skip header line
    for row in tsvreader:
      ct += 1
      pbar.update(ct)
      #ensg = re.sub('\.\d+$', '', row[0]) # get rid of version
      ensg = row[0]
      if ensg in ensg2pid:
        pid = ensg2pid[ensg]
      elif ensg in notfnd:
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
      rv = dba.ins_expression( {'protein_id': pid, 'etype': 'HPA Protein','tissue': row[1], 
                                'qual_value': row[2], 'string_value': "%s: %s"%(row[3],row[4])} )
      if not rv:
        dba_err_ct += 1
        continue
      exp_ct += 1
  pbar.finish()
  print "Processed %d HPA records." % ct
  print "  %d targets have HPA Protein expression data (%d ENSGss)" % (len(tmark.keys()), len(ensg2pid.keys()))
  if notfnd:
    print "  No target found for %d ENSGs." % len(notfnd.keys())
  print "  Inserted %d new expression rows" % exp_ct
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)
  pfile = LOGDIR + 'HPAP-ENSG2PID.p'
  print "Dumping ENSG to protein_id mapping to %s" % pfile
  pickle.dump(ensg2pid, open(pfile, 'wb'))

  line_ct = wcl(PROTEIN_TAU_FILE)
  line_ct -= 1 # file has header
  if not args['--quiet']:
    print "\nProcessing %d input lines in Tissue Specificity Index file %s" % (line_ct, PROTEIN_TAU_FILE)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  with open(PROTEIN_TAU_FILE, 'rU') as tsv:
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
      #ensg = re.sub('\.\d+$', '', row[0]) # get rid of version
      ensg = row[0]
      tau = row[1]
      if ensg not in ensg2pid:
        notfnd[ensg] = True
        continue
      pid = ensg2pid[ensg]
      tmark[pid] = True
      rv = dba.ins_tdl_info({'protein_id': pid, 'itype': 'HPA Protein Tissue Specificity Index',
                             'number_value': tau})
      if not rv:
        dba_err_ct += 1
        continue
      ti_ct += 1
  pbar.finish()
  print "Processed %d tau lines." % ct
  print "  %d targets have HPA Protein tau" % len(tmark.keys())
  if notfnd:
    print "  %d ENSGs not in map from expression file" % len(notfnd.keys())
  print "  Inserted %d new HPA Protein Tissue Specificity Index tdl_info rows" % ti_ct
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)

  #
  # RNA Level Expressions
  #
  start_time = time.time()
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  line_ct = wcl(RNA_QUAL_FILE)
  line_ct -= 1 # file has header
  if not args['--quiet']:
    print "\nProcessing %d records in HPA file %s" % (line_ct, RNA_QUAL_FILE)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  ensg2pid = {}
  notfnd = {}
  ct = 0
  dba_err_ct = 0
  tmark = {}
  exp_ct = 0
  with open(RNA_QUAL_FILE, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    header = tsvreader.next() # skip header line
    for row in tsvreader:
      ct += 1
      pbar.update(ct)
      #ensg = re.sub('\.\d+$', '', row[0]) # get rid of version
      ensg = row[0]
      if ensg in ensg2pid:
        pid = ensg2pid[ensg]
      elif ensg in notfnd:
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
      rv = dba.ins_expression( {'protein_id': pid, 'etype': 'HPA RNA','tissue': row[1], 
                                'qual_value': row[4]} )
      if not rv:
        dba_err_ct += 1
        continue
      exp_ct += 1
  pbar.finish()
  print "Processed %d HPA records." % ct
  print "  %d targets have HPA RNA expression data (%d ENSGs)" % (len(tmark.keys()), len(ensg2pid.keys()))
  if notfnd:
    print "  No target found for %d RNA Symbols." % len(notfnd.keys())
  print "  Inserted %d new expression rows" % exp_ct
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)
  pfile = 'HPAR-ENSG2PID.p'
  print "Dumping ENSG to protein_id mapping to %s" % pfile
  pickle.dump(ensg2pid, open(pfile, 'wb'))

  line_ct = wcl(RNA_TAU_FILE)
  line_ct -= 1 # file has header
  if not args['--quiet']:
    print "\nProcessing %d input lines in Tissue Specificity Index file %s" % (line_ct, RNA_TAU_FILE)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  with open(RNA_TAU_FILE, 'rU') as tsv:
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
      #ensg = re.sub('\.\d+$', '', row[0]) # get rid of version
      ensg = row[0]
      tau = row[1]
      if ensg not in ensg2pid:
        notfnd[ensg] = True
        continue
      pid = ensg2pid[ensg]
      tmark[pid] = True
      rv = dba.ins_tdl_info({'protein_id': pid, 'itype': 'HPA RNA Tissue Specificity Index',
                             'number_value': tau})
      if not rv:
        dba_err_ct += 1
        continue
      ti_ct += 1
  pbar.finish()
  ct = ct - 3
  print "Processed %d tau lines." % ct
  print "  %d targets have HPA RNA tau" % len(tmark.keys())
  if notfnd:
    print "  %d ENSGs not in map from expression file" % len(notfnd.keys())
  print "  Inserted %d new HPA RNA Tissue Specificity Index tdl_info rows" % ti_ct
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)


def wcl(fname):
  with open(fname) as f:
    for i, l in enumerate(f):
      pass
  return i + 1

def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])

if __name__ == '__main__':
  print "\n%s (v%s) [%s]:" % (PROGRAM, __version__, time.strftime("%c"))
  start_time = time.time()
  load()
  elapsed = time.time() - start_time
  print "\n%s: Done. Elapsed time: %s\n" % (PROGRAM, secs2str(elapsed))
