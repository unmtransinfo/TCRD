#!/usr/bin/env python
# Time-stamp: <2019-02-06 12:56:04 smathias>
"""Load disease associations into TCRD from JensenLab DISEASES TSV files..

Usage:
    load-JensenLabDISEASES.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
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
  -d --debug           : turn on debugging output
  -? --help            : print this message and exit 
"""
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2014-2019, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.2.0"

import os,sys,time
from docopt import docopt
from TCRDMP import DBAdaptor
import logging
import csv
import urllib
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd6logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
DOWNLOAD_DIR = '../data/JensenLab/'
BASE_URL = 'http://download.jensenlab.org/'
FILE_K = 'human_disease_knowledge_filtered.tsv'
FILE_E = 'human_disease_experiments_filtered.tsv'
FILE_T = 'human_disease_textmining_filtered.tsv'
SRC_FILES = [os.path.basename(FILE_K),
             os.path.basename(FILE_E),
             os.path.basename(FILE_T)]

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
  dataset_id = dba.ins_dataset( {'name': 'Jensen Lab DISEASES', 'source': 'Files %s from %s'%(", ".join(SRC_FILES), BASE_URL), 'app': PROGRAM, 'app_version': __version__, 'url': 'http://diseases.jensenlab.org/'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'disease', 'where_clause': "dtype LIKE 'JensenLab %'"})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)
  
  # Knowledge channel
  fn = DOWNLOAD_DIR + FILE_K
  line_ct = slmf.wcl(fn)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  if not args['--quiet']:
    print "\nProcessing {} lines in file {}".format(line_ct, fn)
  with open(fn, 'rU') as tsv:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    pmark = {}
    notfnd = set()
    dis_ct = 0
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
      ensp = row[0]
      sym = row[1]
      k = "%s|%s"%(ensp,sym)
      if k in notfnd:
        continue
      targets = dba.find_targets({'stringid': ensp})
      if not targets:
        targets = dba.find_targets({'sym': sym}, idg = False)
      if not targets:
        notfnd.add(k)
        logger.warn("No target found for {}".format(k))
        continue
      dtype = 'JensenLab Knowledge ' + row[4]
      for t in targets:
        p = t['components']['protein'][0]
        pmark[p['id']] = True
        init = {'protein_id': p['id'], 'dtype': dtype, 'name': row[3],
                'did': row[2], 'evidence': row[5], 'conf': row[6]}

        rv = dba.ins_disease(init)
        if not rv:
          dba_err_ct += 1
          continue
        dis_ct += 1
      pbar.update(ct)
  pbar.finish()
  print "{} lines processed.".format(ct)
  print "Inserted {} new disease rows for {} proteins".format(dis_ct, len(pmark))
  if notfnd:
    print "No target found for {} stringids/symbols. See logfile {} for details.".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)
    
  # Experiment channel
  fn = DOWNLOAD_DIR + FILE_E
  line_ct = slmf.wcl(fn)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  if not args['--quiet']:
    print "\nProcessing {} lines in file {}".format(line_ct, fn)
  with open(fn, 'rU') as tsv:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    pmark = {}
    notfnd = set()
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
      k = "%s|%s"%(ensp,sym)
      if k in notfnd:
        continue
      targets = dba.find_targets({'stringid': ensp})
      if not targets:
        targets = dba.find_targets({'sym': sym}, idg = False)
      if not targets:
        notfnd.add(k)
        logger.warn("No target found for {}".format(k))
        continue
      dtype = 'JensenLab Experiment ' + row[4]
      for t in targets:
        p = t['components']['protein'][0]
        pmark[p['id']] = True
        rv = dba.ins_disease( {'protein_id': p['id'], 'dtype': dtype, 'name': row[3],
                               'did': row[2], 'evidence': row[5], 'conf': row[6]} )
        if not rv:
          dba_err_ct += 1
          continue
        dis_ct += 1
      pbar.update(ct)
  pbar.finish()
  print "{} lines processed.".format(ct)
  print "Inserted {} new disease rows for {} proteins".format(dis_ct, len(pmark))
  if skip_ct > 0:
    print "Skipped {} zero confidence rows".format(skip_ct)
  if notfnd:
    print "No target found for {} stringids/symbols. See logfile {} for details.".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

  # Text Mining channel
  fn = DOWNLOAD_DIR + FILE_T
  line_ct = slmf.wcl(fn)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  if not args['--quiet']:
    print "\nProcessing {} lines in file {}".format(line_ct, fn)
  with open(fn, 'rU') as tsv:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    pmark = {}
    notfnd = set()
    dis_ct = 0
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
      ensp = row[0]
      sym = row[1]
      k = "%s|%s"%(ensp,sym)
      if k in notfnd:
        continue
      targets = dba.find_targets({'stringid': ensp})
      if not targets:
        targets = dba.find_targets({'sym': sym}, idg = False)
      if not targets:
        notfnd.add(k)
        logger.warn("No target found for {}".format(k))
        continue
      dtype = 'JensenLab Text Mining'
      for t in targets:
        p = t['components']['protein'][0]
        pmark[p['id']] = True
        rv = dba.ins_disease( {'protein_id': p['id'], 'dtype': dtype, 'name': row[3],
                               'did': row[2], 'zscore': row[4], 'conf': row[5]} )
        if not rv:
          dba_err_ct += 1
          continue
        dis_ct += 1
      pbar.update(ct)
  pbar.finish()
  print "{} lines processed.".format(ct)
  print "Inserted {} new disease rows for {} proteins".format(dis_ct, len(pmark))
  if notfnd:
    print "No target found for {} stringids/symbols. See logfile {} for details.".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)


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
