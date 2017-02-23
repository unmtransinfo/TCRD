#!/usr/bin/env python
# Time-stamp: <2017-02-22 14:40:32 smathias>
"""Load compartment data into TCRD from JensenLab COMPARTMENTS TSV files.

Usage:
    load-JensenLabCOMPARTMENTS.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-JensenLabCOMPARTMENTS.py -? | --help

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
__copyright__ = "Copyright 2016-2017, Steve Mathias"
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
DOWNLOAD_DIR = '../data/JensenLab/'
BASE_URL = 'http://download.jensenlab.org/'
FILE_K = 'human_compartment_knowledge_full.tsv'
FILE_E = 'human_compartment_experiments_full.tsv'
FILE_T = 'human_compartment_textmining_full.tsv'
FILE_P = 'human_compartment_predictions_full.tsv'
SRC_FILES = [os.path.basename(FILE_K),
             os.path.basename(FILE_E),
             os.path.basename(FILE_T),
             os.path.basename(FILE_P)]
SHELVE_FILE = 'tcrd4logs/COMPARTMENTS_NotFound.db'

def download():
  for f in [FILE_K, FILE_E, FILE_T, FILE_P]:
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

  dba_params = {'dbhost': args['--dbhost'], 'dbname': args['--dbname'], 'logger_name': __name__}
  dba = DBAdaptor(dba_params)
  dbi = dba.get_dbinfo()
  logger.info("Connected to TCRD database %s (schema ver %s; data ver %s)", args['--dbname'], dbi['schema_ver'], dbi['data_ver'])
  if not args['--quiet']:
    print "\nConnected to TCRD database %s (schema ver %s; data ver %s)" % (args['--dbname'], dbi['schema_ver'], dbi['data_ver'])

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'Jensen Lab COMPARTMENTS', 'source': 'Files %s from %s'%(", ".join(SRC_FILES), BASE_URL), 'app': PROGRAM, 'app_version': __version__, 'url': 'http://compartments.jensenlab.org/', 'comments': 'Only input rows with confidence >= 3 are loaded.'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'compartment'})
  if not rv:
    print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
    sys.exit(1)

  # this dict will map syms or ensps to TCRD protein_ids, so we only
  # have to find target(s) once for each pair.
  # see find_pids() below
  pmap = {}
  # this will track not found rows keyed by channel
  s = shelve.open(SHELVE_FILE)

  # Knowledge channel
  start_time = time.time()
  fn = DOWNLOAD_DIR + FILE_K
  line_ct = wcl(fn)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  if not args['--quiet']:
    print "\nProcessing %d lines in input file %s" % (line_ct, fn)
  with open(fn, 'rU') as tsv:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    pmark = {}
    comp_ct = 0
    skip_ct = 0
    notfnd = set()
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
      pbar.update(ct)
      if int(row[6]) < 3: # skip rows with conf < 3
        skip_ct += 1
        continue
      ensp = row[0]
      sym = row[1]
      pids = find_pids(dba, ensp, sym, pmap)
      if not pids:
        notfnd.add( "%s|%s"%(ensp,sym) )
        continue
      for pid in pids:
        pmark[pid] = True
        rv = dba.ins_compartment( {'protein_id': pid, 'ctype': 'JensenLab Knowledge',
                                   'go_id': row[2], 'go_term': row[3],
                                   'evidence': "%s %s"%(row[4], row[5]), 
                                   'conf': row[6]} )
        if not rv:
          dba_err_ct += 1
          continue
        comp_ct += 1
  pbar.finish()
  elapsed = time.time() - start_time
  print "%d rows processed. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "  Skipped %d rows with conf < 3" % skip_ct
  print "  %d proteins have compartment(s)" % len(pmark.keys())
  print "  Inserted %d new compartment rows" % comp_ct
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)
  if notfnd:
    s['Knowledge'] = notfnd
    print "No target found for %d rows. See file: %s" % (len(notfnd), SHELVE_FILE)

  # Experiment channel
  start_time = time.time()
  fn = DOWNLOAD_DIR + FILE_E
  line_ct = wcl(fn)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  if not args['--quiet']:
    print "\nProcessing %d lines in input file %s" % (line_ct, fn)
  with open(fn, 'rU') as tsv:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    pmark = {}
    comp_ct = 0
    skip_ct = 0
    notfnd = set()
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
      pbar.update(ct)
      if int(row[6]) < 3: # skip rows with conf < 3
        skip_ct += 1
        continue
      ensp = row[0]
      sym = row[1]
      pids = find_pids(dba, ensp, sym, pmap)
      if not pids:
        notfnd.add( "%s|%s"%(ensp,sym) )
        continue
      for pid in pids:
        pmark[pid] = True
        rv = dba.ins_compartment( {'protein_id': pid, 'ctype': 'JensenLab Experiment',
                                   'go_id': row[2], 'go_term': row[3],
                                   'evidence': "%s %s"%(row[4], row[5]), 
                                   'conf': row[6]} )
        if not rv:
          dba_err_ct += 1
          continue
        comp_ct += 1
  pbar.finish()
  elapsed = time.time() - start_time
  print "%d rows processed. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "  Skipped %d rows with conf < 3" % skip_ct
  print "  %d proteins have compartment(s)" % len(pmark.keys())
  print "  Inserted %d new compartment rows" % comp_ct
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)
  if notfnd:
    s['Experiment'] = notfnd
    print "No target found for %d rows. See file: %s" % (len(notfnd), SHELVE_FILE)

  # Text Mining channel
  start_time = time.time()
  fn = DOWNLOAD_DIR + FILE_T
  line_ct = wcl(fn)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  if not args['--quiet']:
    print "\nProcessing %d lines in input file %s" % (line_ct, fn)
  with open(fn, 'rU') as tsv:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    pmark = {}
    comp_ct = 0
    skip_ct = 0
    notfnd = set()
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
      pbar.update(ct)
      if float(row[4]) < 3.0: # skip rows with zscore < 3
        skip_ct += 1
        continue
      ensp = row[0]
      sym = row[1]
      pids = find_pids(dba, ensp, sym, pmap)
      if not pids:
        notfnd.add( "%s|%s"%(ensp,sym) )
        continue
      for pid in pids:
        pmark[pid] = True
        rv = dba.ins_compartment( {'protein_id': pid, 'ctype': 'JensenLab Text Mining',
                                   'go_id': row[2], 'go_term': row[3],
                                   'zscore': row[4], 'conf': row[5], 
                                   'url': row[6]} )
        if not rv:
          dba_err_ct += 1
          continue
        comp_ct += 1
  pbar.finish()
  elapsed = time.time() - start_time
  print "%d rows processed. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "  Skipped %d rows with zscore < 3.0" % skip_ct
  print "  %d proteins have compartment(s)" % len(pmark.keys())
  print "  Inserted %d new compartment rows" % comp_ct
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)
  if notfnd:
    s['Text Mining'] = notfnd
    print "No target found for %d rows. Saved to file: %s" % (len(notfnd), SHELVE_FILE)

  # Prediction channel
  start_time = time.time()
  fn = DOWNLOAD_DIR + FILE_P
  line_ct = wcl(fn)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  if not args['--quiet']:
    print "\nProcessing %d lines in input file %s" % (line_ct, fn)
  with open(fn, 'rU') as tsv:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    pmark = {}
    comp_ct = 0
    skip_ct = 0
    notfnd = set()
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
      pbar.update(ct)
      if int(row[6]) < 3: # skip rows with conf < 3
        skip_ct += 1
        continue
      ensp = row[0]
      sym = row[1]
      pids = find_pids(dba, ensp, sym, pmap)
      if not pids:
        notfnd.add( "%s|%s"%(ensp,sym) )
        continue
      for pid in pids:
        pmark[pid] = True
        rv = dba.ins_compartment( {'protein_id': pid, 'ctype': 'JensenLab Prediction',
                                   'go_id': row[2], 'go_term': row[3],
                                   'evidence': "%s %s"%(row[4], row[5]), 
                                   'conf': row[6]} )
        if not rv:
          dba_err_ct += 1
          continue
        comp_ct += 1
  pbar.finish()
  elapsed = time.time() - start_time
  print "%d rows processed. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "  Skipped %d rows with conf < 3" % skip_ct
  print "  %d proteins have compartment(s)" % len(pmark.keys())
  print "  Inserted %d new compartment rows" % comp_ct
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)
  if notfnd:
    s['Prediction'] = notfnd
    print "No target found for %d rows. Saved to file: %s" % (len(notfnd), SHELVE_FILE)

  s.close()


def find_pids(dba, ensp, sym, k2pid):
  pids = []
  if ensp in k2pid:
    pids = k2pid[ensp]
  elif sym in k2pid:
    pids = k2pid[sym]
  else:
    targets = dba.find_targets({'stringid': ensp})
    if targets:
      for t in targets:
        pids.append(t['components']['protein'][0]['id'])
      k2pid[sym] = pids
    else:
      targets = dba.find_targets({'sym': sym})
      if targets:
        for t in targets:
          pids.append(t['components']['protein'][0]['id'])
        k2pid[sym] = pids
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
