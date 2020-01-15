#!/usr/bin/env python
# Time-stamp: <2019-08-15 15:53:36 smathias>
"""Load expression data into TCRD from JensenLab TISSUES TSV files..

Usage:
    load-JensenLabTISSUES.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
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
  -d --debug           : turn on debugging output
  -? --help            : print this message and exit 
"""
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2014-2019, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.3.0"

import os,sys,time
from docopt import docopt
from TCRDMP import DBAdaptor
import logging
import ast
import csv
import urllib
import shelve
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd6logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
DOWNLOAD_DIR = '../data/JensenLab/'
BASE_URL = 'http://download.jensenlab.org/'
FILE_K = 'human_tissue_knowledge_filtered.tsv'
FILE_E = 'human_tissue_experiments_filtered.tsv'
FILE_T = 'human_tissue_textmining_filtered.tsv'
SRC_FILES = [os.path.basename(FILE_K),
             os.path.basename(FILE_E),
             os.path.basename(FILE_T)]
# This file contains a manually currated dict mapping tissue names to Uberon IDs.
# These are ones for which TCRDMP.get_uberon_id does not return a uid.
TISSUE2UBERON_FILE = '../data/Tissue2Uberon.txt'

def download(args):
  for f in [FILE_K, FILE_E, FILE_T]:
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
  dataset_id = dba.ins_dataset( {'name': 'Jensen Lab TISSUES', 'source': 'Files %s from %s'%(", ".join(SRC_FILES), BASE_URL), 'app': PROGRAM, 'app_version': __version__, 'url': 'http://tissues.jensenlab.org/'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'expression', 'where_clause': "type LIKE 'JensenLab %'"})
  if not rv:
    print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
    sys.exit(1)

  with open(TISSUE2UBERON_FILE, 'r') as ifh:
    tiss2uid = ast.literal_eval(ifh.read())
  if not args['--quiet']:
    print "\nGot {} tissue to Uberon ID mappings from file {}".format(len(tiss2uid), TISSUE2UBERON_FILE)

  # this dict will map ENSP|sym from input files to TCRD protein_id(s)
  # so we only have to find target(s) once for each pair.
  # See find_pids() below
  pmap = {}

  # Knowledge channel
  fn = DOWNLOAD_DIR+FILE_K
  line_ct = slmf.wcl(fn)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  if not args['--quiet']:
    print "\nProcessing {} lines in input file {}".format(line_ct, fn)
  with open(fn, 'rU') as tsv:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    pmark = {}
    exp_ct = 0
    notfnd = set()
    nouid = set()
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
      pbar.update(ct)
      k = "%s|%s" % (row[0], row[1]) # ENSP|sym
      if k in notfnd:
        continue
      pids = find_pids(dba, k, pmap)
      if not pids:
        notfnd.add(k)
        continue
      etype = 'JensenLab Knowledge ' + row[4]
      init = {'etype': etype, 'tissue': row[3],'boolean_value': 1, 
              'oid': row[2], 'evidence': row[5], 'conf': row[6]}
      # Add Uberon ID, if we can find one
      if row[2]:
        uberon_id = dba.get_uberon_id({'oid': row[2]})
      if not uberon_id:
        uberon_id = dba.get_uberon_id({'name': row[3]})
      if not uberon_id and row[3] in tiss2uid:
        uberon_id = tiss2uid[row[3]]
      if uberon_id:
        init['uberon_id'] = uberon_id
      else:
        nouid.add(row[3])
      for pid in pids:
        init['protein_id'] = pid
        rv = dba.ins_expression(init)
        if not rv:
          dba_err_ct += 1
          continue
        exp_ct += 1
        pmark[pid] = True
  pbar.finish()
  for k in notfnd:
    logger.warn("No target found for {}".format(k))
  for t in nouid:
    logger.warn("No Uberon ID found for {}".format(t))
  print "{} rows processed.".format(ct)
  print "  Inserted {} new expression rows for {} proteins".format(exp_ct, len(pmark))
  if notfnd:
    print "No target found for {} stringids/symbols. See logfile {} for details.".format(len(notfnd), logfile)
  if nouid:
    print "No Uberon ID found for {} tissues. See logfile {} for details.".format(len(nouid), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)
  
  # Experiment channel
  fn = DOWNLOAD_DIR+FILE_E
  line_ct = slmf.wcl(fn)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  if not args['--quiet']:
    print "\nProcessing {} lines in input file {}".format(line_ct, fn)
  with open(fn, 'rU') as tsv:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    pmark = {}
    exp_ct = 0
    notfnd = set()
    nouid = set()
    skip_ct = 0
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
      pbar.update(ct)
      if row[6] == '0':
        # skip zero confidence rows
        skip_ct += 1
        continue
      sym = row[1]
      # some rows look like:
      # ['ENSP00000468389', 'PSENEN {ECO:0000313|Ensembl:ENSP00000468593}', 'BTO:0002860', 'Oral mucosa', 'HPA', 'High: 1 antibody', '1']
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
        notfnd.add(k)
        continue
      etype = 'JensenLab Experiment ' + row[4]
      init = {'etype': etype, 'tissue': row[3],
              'string_value': row[5], 'oid': row[2], 'conf': row[6]}
      # Add Uberon ID, if we can find one
      if row[2]:
        uberon_id = dba.get_uberon_id({'oid': row[2]})
      if not uberon_id:
        uberon_id = dba.get_uberon_id({'name': row[3]})
      if not uberon_id and row[3] in tiss2uid:
        uberon_id = tiss2uid[row[3]]
      if uberon_id:
        init['uberon_id'] = uberon_id
      else:
        nouid.add(row[3])
      for pid in pids:
        pmark[pid] = True
        init['protein_id'] = pid
        rv = dba.ins_expression(init)
        if not rv:
          dba_err_ct += 1
          continue
        exp_ct += 1
  pbar.finish()
  for k in notfnd:
    logger.warn("No target found for {}".format(k))
  for t in nouid:
    logger.warn("No Uberon ID found for {}".format(t))
  print "{} rows processed.".format(ct)
  print "  Inserted {} new expression rows for {} proteins".format(exp_ct, len(pmark))
  print "  Skipped {} zero confidence rows".format(skip_ct)
  if notfnd:
    print "No target found for {} stringids/symbols. See logfile {} for details.".format(len(notfnd), logfile)
  if nouid:
    print "No Uberon ID found for {} tissues. See logfile {} for details.".format(len(nouid), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

  # Text Mining channel
  fn = DOWNLOAD_DIR+FILE_T
  line_ct = slmf.wcl(fn)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  if not args['--quiet']:
    print "\nProcessing {} lines in input file {}".format(line_ct, fn)
  with open(fn, 'rU') as tsv:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    pmark = {}
    exp_ct = 0
    notfnd = set()
    nouid = set()
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
      pbar.update(ct)
      k = "%s|%s" % (row[0], row[1]) # ENSP|sym
      if k in notfnd:
        continue
      pids = find_pids(dba, k, pmap)
      if not pids:
        notfnd.add(k)
        logger.warn("No target found for {}".format(k))
        continue
      etype = 'JensenLab Text Mining'
      init = {'etype': etype, 'tissue': row[3], 'boolean_value': 1,
              'oid': row[2], 'zscore': row[4], 'conf': row[5], 'url': row[6]}
      # Add Uberon ID, if we can find one
      if row[2]:
        uberon_id = dba.get_uberon_id({'oid': row[2]})
      if not uberon_id:
        uberon_id = dba.get_uberon_id({'name': row[3]})
      if not uberon_id and row[3] in tiss2uid:
        uberon_id = tiss2uid[row[3]]
      if uberon_id:
        init['uberon_id'] = uberon_id
      else:
        nouid.add(row[3])
      for pid in pids:
        pmark[pid] = True
        init['protein_id'] = pid
        rv = dba.ins_expression(init)
        if not rv:
          dba_err_ct += 1
          continue
        exp_ct += 1
  pbar.finish()
  for k in notfnd:
    logger.warn("No target found for {}".format(k))
  for t in nouid:
    logger.warn("No Uberon ID found for {}".format(t))
  print "{} rows processed.".format(ct)
  print "  Inserted {} new expression rows for {} proteins".format(exp_ct, len(pmark))
  if notfnd:
    print "No target found for {} stringids/symbols. See logfile {} for details.".format(len(notfnd), logfile)
  if nouid:
    print "No Uberon ID found for {} tissues. See logfile {} for details.".format(len(nouid), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

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
