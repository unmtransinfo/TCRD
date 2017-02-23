#!/usr/bin/env python
# Time-stamp: <2017-02-22 14:36:31 smathias>
"""Load expression data into TCRD from JensenLab TISSUES TSV files..

Usage:
    load-JensenLabTISSUES.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-JensenLabTISSUES.py -? | --help

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
__copyright__ = "Copyright 2014-2017, Steve Mathias"
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
LOGDIR = 'tcrd4logs/'
LOGFILE = LOGDIR+'%s.log'%PROGRAM
LOGFILE = "%s.log" % PROGRAM
DOWNLOAD_DIR = '../data/JensenLab/'
BASE_URL = 'http://download.jensenlab.org/'
FILE_K = 'human_tissue_knowledge_filtered.tsv'
FILE_E = 'human_tissue_experiments_filtered.tsv'
FILE_T = 'human_tissue_textmining_filtered.tsv'
SRC_FILES = [os.path.basename(FILE_K),
             os.path.basename(FILE_E),
             os.path.basename(FILE_T)]

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
  dataset_id = dba.ins_dataset( {'name': 'Jensen Lab TISSUES', 'source': 'Files %s from %s'%(", ".join(SRC_FILES), BASE_URL), 'app': PROGRAM, 'app_version': __version__, 'url': 'http://tissues.jensenlab.org/'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'expression', 'where_clause': "type LIKE 'JensenLab %'"})
  if not rv:
    print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
    sys.exit(1)

  # this dict will map ENSP|sym from input files to TCRD protein_id(s)
  # so we only have to find target(s) once for each pair.
  # See find_pids() below
  pmap = {}

  # Knowledge channel
  start_time = time.time()
  fn = DOWNLOAD_DIR+FILE_K
  line_ct = wcl(fn)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  if not args['--quiet']:
    print "\nProcessing %d lines in input file %s" % (line_ct, fn)
  with open(fn, 'rU') as tsv:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    pmark = {}
    exp_ct = 0
    dbmfile = LOGDIR + 'TISSUESk_not-found.db'
    notfnd = shelve.open(dbmfile)
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
      pbar.update(ct)
      k = "%s|%s" % (row[0], row[1]) # ENSP|sym
      if k in notfnd:
        continue
      pids = find_pids(dba, k, pmap)
      if not pids:
        notfnd[k] = True
        continue
      etype = 'JensenLab Knowledge ' + row[4]
      for pid in pids:
        pmark[pid] = True
        rv = dba.ins_expression( {'protein_id': pid, 'etype': etype, 'tissue': row[3],
                                  'boolean_value': 1, 'oid': row[2], 'evidence': row[5], 
                                  'conf': row[6]} )
        if not rv:
          dba_err_ct += 1
          continue
        exp_ct += 1
  pbar.finish()
  elapsed = time.time() - start_time
  print "%d rows processed. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "  %d proteins have expression(s)" % len(pmark.keys())
  print "  Inserted %d new expression rows" % exp_ct
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)
  if notfnd:
    print "No target found for %d rows - keys saved to file: %s" % (len(notfnd.keys()), dbmfile)

  # Experiment channel
  start_time = time.time()
  fn = DOWNLOAD_DIR+FILE_E
  line_ct = wcl(fn)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  if not args['--quiet']:
    print "\nProcessing %d lines in input file %s" % (line_ct, fn)
  with open(fn, 'rU') as tsv:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    pmark = {}
    exp_ct = 0
    dbmfile = LOGDIR + 'TISSUESe_not-found.db'
    notfnd = shelve.open(dbmfile)
    skip_ct = 0
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
      pbar.update(ct)
      if row[6] == '0':
        # skip zero confidence rows
        skip_ct += 1
        continue
      # some rows look like:
      # ['ENSP00000468389', 'PSENEN {ECO:0000313|Ensembl:ENSP00000468593}', 'BTO:0002860', 'Oral mucosa', 'HPA', 'High: 1 antibody', '1']
      sym = row[1]
      if ' ' in sym:
        sym = sym.split()[0]
      k = "%s|%s" % (row[0], sym) # ENSP|sym
      if k in notfnd:
        continue
      try:
        pids = find_pids(dba, k, pmap)
      except ValueError:
        print "[ERROR] Row: %s; k: %s" % (str(row), k)
      if not pids:
        notfnd[k] = True
        continue
      etype = 'JensenLab Experiment ' + row[4]
      for pid in pids:
        pmark[pid] = True
        rv = dba.ins_expression( {'protein_id': pid, 'etype': etype, 'tissue': row[3],
                                  'string_value': row[5], 'oid': row[2], 'conf': row[6]} )
        if not rv:
          dba_err_ct += 1
          continue
        exp_ct += 1
  pbar.finish()
  elapsed = time.time() - start_time
  print "%d rows processed. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "  Skipped %d zero confidence rows" % skip_ct
  print "  %d proteins have expression(s)" % len(pmark.keys())
  print "  Inserted %d new expression rows" % exp_ct
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)
  if notfnd:
    print "No target found for %d rows. Saved to file: %s" % (len(notfnd.keys()), dbmfile)

  # Text Mining channel
  start_time = time.time()
  fn = DOWNLOAD_DIR+FILE_T
  line_ct = wcl(fn)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  if not args['--quiet']:
    print "\nProcessing %d lines in input file %s" % (line_ct, fn)
  with open(fn, 'rU') as tsv:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    pmark = {}
    exp_ct = 0
    dbmfile = LOGDIR + 'TISSUEStm_not-found.db'
    notfnd = shelve.open(dbmfile)
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
      pbar.update(ct)
      k = "%s|%s" % (row[0], row[1]) # ENSP|sym
      if k in notfnd:
        continue
      pids = find_pids(dba, k, pmap)
      if not pids:
        notfnd[k] = True
        continue
      etype = 'JensenLab Text Mining'
      for pid in pids:
        pmark[pid] = True
        rv = dba.ins_expression( {'protein_id': pid, 'etype': etype, 'tissue': row[3],
                                  'boolean_value': 1, 'oid': row[2], 'zscore': row[4], 
                                  'conf': row[5], 'url': row[6]} )
        if not rv:
          dba_err_ct += 1
          continue
        exp_ct += 1
  pbar.finish()
  elapsed = time.time() - start_time
  print "%d rows processed. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "  %d proteins have expression(s)" % len(pmark.keys())
  print "  Inserted %d new expression rows" % exp_ct
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)
  if notfnd:
    print "No target found for %d rows. Saved to file: %s" % (len(notfnd.keys()), dbmfile)


def find_pids(dba, k, k2pids):
  # k is 'ENSP|sym'
  if k in k2pids:
    pids = k2pids[k]
  else:
    pids = []
    (ensp, sym) = k.split("|")
    # First try to find target(s) by stringid - the most reliable way
    targets = dba.find_targets({'stringid': ensp})
    if targets:
      for t in targets:
        pids.append(t['components']['protein'][0]['id'])
      k2pids[k] = pids
    if not targets:
      # Next, try by symbol
      targets = dba.find_targets({'sym': sym})
      if targets:
        for t in targets:
          pids.append(t['components']['protein'][0]['id'])
        k2pids[k] = pids
    if not targets:
      # Finally, try by Ensembl xref
      targets = dba.find_targets_by_xref({'xtype': 'Ensembl', 'value': ensp})
      if targets:
        for t in targets:
          pids.append(t['components']['protein'][0]['id'])
        k2pids[k] = pids
  return pids

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
