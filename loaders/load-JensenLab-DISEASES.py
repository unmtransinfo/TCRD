#!/usr/bin/env python
# Time-stamp: <2017-02-23 08:08:26 smathias>
"""Load disease associations into TCRD from JensenLab DISEASES TSV files..

Usage:
    load-JensenLabDISEASES.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-JensenLabDISEASES.py -? | --help

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
__copyright__ = "Copyright 2014-2016, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.0.0"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import logging
import csv
import urllib
import shelve
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
LOGFILE = "%s.log" % PROGRAM

DOWNLOAD_DIR = '../data/JensenLab/'
BASE_URL = 'http://download.jensenlab.org/'
FILE_K = 'human_disease_knowledge_filtered.tsv'
FILE_E = 'human_disease_experiments_filtered.tsv'
FILE_T = 'human_disease_textmining_filtered.tsv'
SRC_FILES = [os.path.basename(FILE_K),
             os.path.basename(FILE_E),
             os.path.basename(FILE_T)]
SHELF_FILE = 'tcrd4logs/load-JensenLab-DISEASES.db'

def download():
  for f in [FILE_K, FILE_E, FILE_T]:
    if os.path.exists(DOWNLOAD_DIR + f):
      os.remove(DOWNLOAD_DIR + f)
    print "Downloading ", BASE_URL + f
    print "         to ", DOWNLOAD_DIR + f
    urllib.urlretrieve(BASE_URL + f, DOWNLOAD_DIR + f)

def load():
  args = docopt(__doc__, version=__version__)
  debug = int(args['--debug'])
  if debug:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  
  loglevel = int(args['--loglevel'])
  if args['--logfile']:
    logfile = args['--logfile']
  else:
    logfile = "%s.log" % PROGRAM
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
    
  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'Jensen Lab DISEASES', 'source': 'Files %s from %s'%(", ".join(SRC_FILES), BASE_URL), 'app': PROGRAM, 'app_version': __version__, 'url': 'http://diseases.jensenlab.org/'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'disease', 'where_clause': "dtype LIKE 'JensenLab %'"})
  if not rv:
    print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
    sys.exit(1)
  
  s = shelve.open(SHELF_FILE, writeback=True)
  s['knowledge_not_found'] = set()
  s['experiment_not_found'] = set()
  s['textmining_not_found'] = set()
  
  # Knowledge channel
  start_time = time.time()
  fn = DOWNLOAD_DIR + FILE_K
  line_ct = wcl(fn)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  if not args['--quiet']:
    print "\nProcessing %d lines in file %s" % (line_ct, fn)
  with open(fn, 'rU') as tsv:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    tmark = {}
    dis_ct = 0
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
      ensp = row[0]
      sym = row[1]
      targets = dba.find_targets({'stringid': ensp})
      if not targets:
        targets = dba.find_targets({'sym': sym}, idg = False)
      if not targets:
        k = "%s|%s"%(ensp,sym)
        s['knowledge_not_found'].add(k)
        continue
      dtype = 'JensenLab Knowledge ' + row[4]
      for t in targets:
        tmark[t['id']] = True
        rv = dba.ins_disease( {'target_id': t['id'], 'dtype': dtype, 'name': row[3],
                               'did': row[2], 'evidence': row[5], 'conf': row[6]} )
        if not rv:
          dba_err_ct += 1
          continue
        dis_ct += 1
      pbar.update(ct)
  pbar.finish()
  elapsed = time.time() - start_time
  print "%d lines processed. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "  %d targets have disease association(s)" % len(tmark.keys())
  print "  Inserted %d new disease rows" % dis_ct
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)
  if len(s['knowledge_not_found']) > 0:
    print "No target found for %d disease association rows. See shelve file: %s" % (len(s['knowledge_not_found']), SHELF_FILE)

  # Experiment channel
  start_time = time.time()
  fn = DOWNLOAD_DIR + FILE_E
  line_ct = wcl(fn)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  if not args['--quiet']:
    print "\nProcessing %d line in file %s" % (line_ct, fn)
  with open(fn, 'rU') as tsv:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    tmark = {}
    dis_ct = 0
    skip_ct = 0
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
      if row[6] == '0':
        # skip zero confidence rows
        skip_ct += 1
        continue
      ensp = row[0]
      sym = row[1]
      targets = dba.find_targets({'stringid': ensp})
      if not targets:
        targets = dba.find_targets({'sym': sym}, idg = False)
      if not targets:
        k = "%s|%s"%(ensp,sym)
        s['experiment_not_found'].add(k)
        continue
      dtype = 'JensenLab Experiment ' + row[4]
      for t in targets:
        tmark[t['id']] = True
        rv = dba.ins_disease( {'target_id': t['id'], 'dtype': dtype, 'name': row[3],
                               'did': row[2], 'evidence': row[5], 'conf': row[6]} )
        if not rv:
          dba_err_ct += 1
          continue
        dis_ct += 1
      pbar.update(ct)
  pbar.finish()
  elapsed = time.time() - start_time
  print "%d lines processed. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "  Skipped %d zero confidence rows" % skip_ct
  print "  %d targets have disease association(s)" % len(tmark.keys())
  print "  Inserted %d new disease rows" % dis_ct
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)
  if len(s['experiment_not_found']) > 0:
    print "No target found for %d disease association rows. See shelve file: %s" % (len(s['experiment_not_found']), SHELF_FILE)

  # Text Mining channel
  start_time = time.time()
  fn = DOWNLOAD_DIR + FILE_T
  line_ct = wcl(fn)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  if not args['--quiet']:
    print "\nProcessing %d lines in file %s" % (line_ct, fn)
  with open(fn, 'rU') as tsv:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    tmark = {}
    dis_ct = 0
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
      ensp = row[0]
      sym = row[1]
      targets = dba.find_targets({'stringid': ensp})
      if not targets:
        targets = dba.find_targets({'sym': sym}, idg = False)
      if not targets:
        k = "%s|%s"%(ensp,sym)
        s['textmining_not_found'].add(k)
        continue
      dtype = 'JensenLab Text Mining'
      for t in targets:
        tmark[t['id']] = True
        rv = dba.ins_disease( {'target_id': t['id'], 'dtype': dtype, 'name': row[3],
                               'did': row[2], 'zscore': row[4], 'conf': row[5]} )
        if not rv:
          dba_err_ct += 1
          continue
        dis_ct += 1
      pbar.update(ct)
  pbar.finish()
  elapsed = time.time() - start_time
  print "%d lines processed. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "  %d targets have disease association(s)" % len(tmark.keys())
  print "  Inserted %d new disease rows" % dis_ct
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)
  if len(s['textmining_not_found']) > 0:
    print "No target found for %d disease association rows. See shelve file: %s" % (len(s['textmining_not_found']), SHELF_FILE)

def wcl(fname):
  with open(fname) as f:
    for i, l in enumerate(f):
      pass
  return i + 1

def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])

if __name__ == '__main__':
  print "\n%s (v%s) [%s]:\n" % (PROGRAM, __version__, time.strftime("%c"))
  download()
  load()
  print "\n%s: Done.\n" % PROGRAM
