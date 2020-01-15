#!/usr/bin/env python
# Time-stamp: <2019-08-21 09:30:16 smathias>
"""Load compartment data into TCRD from JensenLab COMPARTMENTS TSV files.

Usage:
    load-JensenLabCOMPARTMENTS.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
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
  -d --debug           : turn on debugging output
  -? --help            : print this message and exit 
"""
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2016-2019, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "3.0.0"

import os,sys,time
from docopt import docopt
from TCRDMP import DBAdaptor
import logging
import csv
import urllib
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = 'tcrd6logs/'
LOGFILE = LOGDIR + '%s.log'%PROGRAM
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

def download(args):
  for f in [FILE_K, FILE_E, FILE_T, FILE_P]:
    if os.path.exists(DOWNLOAD_DIR + f):
      os.remove(DOWNLOAD_DIR + f)
    if not args['--quiet']:
      print "Downloading ", BASE_URL + f
      print "         to ", DOWNLOAD_DIR + f
    urllib.urlretrieve(BASE_URL + f, DOWNLOAD_DIR + f)

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
  dataset_id = dba.ins_dataset( {'name': 'Jensen Lab COMPARTMENTS', 'source': 'Files %s from %s'%(", ".join(SRC_FILES), BASE_URL), 'app': PROGRAM, 'app_version': __version__, 'url': 'http://compartments.jensenlab.org/', 'comments': 'Only input rows with confidence >= 3 are loaded.'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'compartment'})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

  # this dict will map syms or ensps to TCRD protein_ids, so we only
  # have to find target(s) once for each pair.
  # see find_pids() below
  pmap = {}

  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]

  # Knowledge channel
  fn = DOWNLOAD_DIR + FILE_K
  line_ct = slmf.wcl(fn)
  if not args['--quiet']:
    print "\nProcessing {} lines in input file {}".format(line_ct, fn)
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
      k = "%s|%s"%(ensp,sym)
      if k in pmap:
        # we've already found it
        pids = pmap[k]
      elif k in notfnd:
        # we've already not found it
        continue
      else:
        # look it up
        pids = find_pids(dba, ensp, sym, pmap)
        if not pids:
          notfnd.add(k)
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
  for k in notfnd:
    logger.warn("No target found for {}".format(k))
  print "{} lines processed.".format(ct)
  print "  Inserted {} new compartment rows for {} proteins".format(comp_ct, len(pmark))
  print "  Skipped {} lines with conf < 3".format(skip_ct)
  if notfnd:
    print "No target found for {} ENSPs/symbols. See logfile {} for details.".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)
  
  # Experiment channel
  fn = DOWNLOAD_DIR + FILE_E
  line_ct = slmf.wcl(fn)
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
      if float(row[6]) < 3: # skip rows with conf < 3
        skip_ct += 1
        continue
      ensp = row[0]
      sym = row[1]
      k = "%s|%s"%(ensp,sym)
      if k in pmap:
        # we've already found it
        pids = pmap[k]
      elif k in notfnd:
        # we've already not found it
        continue
      else:
        # look it up
        pids = find_pids(dba, ensp, sym, pmap)
        if not pids:
          notfnd.add(k)
          continue
      for pid in pids:
        rv = dba.ins_compartment( {'protein_id': pid, 'ctype': 'JensenLab Experiment',
                                   'go_id': row[2], 'go_term': row[3],
                                   'evidence': "%s %s"%(row[4], row[5]), 
                                   'conf': row[6]} )
        if not rv:
          dba_err_ct += 1
          continue
        comp_ct += 1
        pmark[pid] = True
  pbar.finish()
  for k in notfnd:
    logger.warn("No target found for {}".format(k))
  print "{} lines processed.".format(ct)
  print "  Inserted {} new compartment rows for {} proteins".format(comp_ct, len(pmark))
  print "  Skipped {} lines with conf < 3".format(skip_ct)
  if notfnd:
    print "No target found for {} ENSPs/symbols. See logfile {} for details.".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)
  
  # Text Mining channel
  fn = DOWNLOAD_DIR + FILE_T
  line_ct = slmf.wcl(fn)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  if not args['--quiet']:
    print "\nProcessing {} lines in input file {}".format(line_ct, fn)
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
      k = "%s|%s"%(ensp,sym)
      if k in pmap:
        # we've already found it
        pids = pmap[k]
      elif k in notfnd:
        # we've already not found it
        continue
      else:
        # look it up
        pids = find_pids(dba, ensp, sym, pmap)
        if not pids:
          notfnd.add(k)
          continue
      for pid in pids:
        rv = dba.ins_compartment( {'protein_id': pid, 'ctype': 'JensenLab Text Mining',
                                   'go_id': row[2], 'go_term': row[3],
                                   'zscore': row[4], 'conf': row[5], 
                                   'url': row[6]} )
        if not rv:
          dba_err_ct += 1
          continue
        comp_ct += 1
        pmark[pid] = True
  pbar.finish()
  for k in notfnd:
    logger.warn("No target found for {}".format(k))
  print "{} lines processed.".format(ct)
  print "  Inserted {} new compartment rows for {} proteins".format(comp_ct, len(pmark))
  print "  Skipped {} lines with conf < 3".format(skip_ct)
  if notfnd:
    print "No target found for {} ENSPs/symbols. See logfile {} for details.".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

  # Prediction channel
  fn = DOWNLOAD_DIR + FILE_P
  line_ct = slmf.wcl(fn)
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
      k = "%s|%s"%(ensp,sym)
      if k in pmap:
        # we've already found it
        pids = pmap[k]
      elif k in notfnd:
        # we've already not found it
        continue
      else:
        # look it up
        pids = find_pids(dba, ensp, sym, pmap)
        if not pids:
          notfnd.add(k)
          continue
      for pid in pids:
        rv = dba.ins_compartment( {'protein_id': pid, 'ctype': 'JensenLab Prediction',
                                   'go_id': row[2], 'go_term': row[3],
                                   'evidence': "%s %s"%(row[4], row[5]), 
                                   'conf': row[6]} )
        if not rv:
          dba_err_ct += 1
          continue
        comp_ct += 1
        pmark[pid] = True
  pbar.finish()
  for k in notfnd:
    logger.warn("No target found for {}".format(k))
  print "{} lines processed.".format(ct)
  print "  Inserted {} new compartment rows for {} proteins".format(comp_ct, len(pmark))
  print "  Skipped {} lines with conf < 3".format(skip_ct)
  if notfnd:
    print "No target found for {} ENSPs/symbols. See logfile {} for details.".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)


def find_pids(dba, ensp, sym, k2pids):
  pids = []
  k = "%s|%s"%(ensp,sym)
  if k in k2pids:
    pids = k2pids[ensp]
  else:
    targets = dba.find_targets({'stringid': ensp})
    if not targets:
      targets = dba.find_targets({'sym': sym})
    if targets:
      for t in targets:
        pids.append(t['components']['protein'][0]['id'])
      k2pids[k] = pids # save mapping - k2pids is pmap in load()
  return pids


if __name__ == '__main__':
  print "\n{} (v{}) [{}]:\n".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  start_time = time.time()
  download(args)
  load(args)
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))
