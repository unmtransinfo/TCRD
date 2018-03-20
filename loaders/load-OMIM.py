#!/usr/bin/env python
# Time-stamp: <2018-02-06 11:18:45 smathias>
"""Load phenotypes into TCRD from OMIM genemap.txt file.

Usage:
    load-OMIM.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-OMIM.py -h | --help

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

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import csv
import logging
import urllib
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd5logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
# One must register to get OMIM downloads. Last time I did, the link to get them was:
DOWNLOAD_DIR = '../data/OMIM/'
BASE_URL = 'https://data.omim.org/downloads/ey9G4kaCTGCQ-q_Yx0XAPg/'
FILENAME = 'genemap.txt'

def download(args):
  if os.path.exists(DOWNLOAD_DIR + FILENAME):
    os.rename(DOWNLOAD_DIR + FILENAME, DOWNLOAD_DIR + FILENAME + '.bak')
  print "\nDownloading ", BASE_URL + FILENAME
  print "         to ", DOWNLOAD_DIR + FILENAME
  urllib.urlretrieve(BASE_URL + FILENAME, DOWNLOAD_DIR + FILENAME)
  print "Done."

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
  dataset_id = dba.ins_dataset( {'name': 'OMIM Confirmed Phenotypes', 'source': 'File %s from ftp.omim.org'%FILENAME, 'app': PROGRAM, 'app_version': __version__, 'url': 'http://omim.org/'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'phenotype', 'where_clause': "ptype = 'OMIM'"})
  if not rv:
    print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
    sys.exit(1)

  fname = DOWNLOAD_DIR + FILENAME
  line_ct = slmf.wcl(fname)
  line_ct -= 1 
  if not args['--quiet']:
    print '\nProcessing %d lines from input file %s' % (line_ct, fname)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start()
  outlist = []
  with open(fname, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    notfnd = {}
    tmark = {}
    skip_ct = 0
    pt_ct = 0
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
      if row[0].startswith('#'):
        # The file has commented lines at the beginning and end
        skip_ct += 1
        continue
# The fields are:
# 0  - Sort ???
# 1  - Month
# 2  - Day
# 3  - Year
# 4  - Cytogenetic location
# 5  - Gene Symbol(s)
# 6  - Confidence
# 7  - Gene Name
# 8 - MIM Number
# 9 - Mapping Method
# 10 - Comments
# 11 - Phenotypes
# 12 - Mouse Gene Symbol
      if row[6] != 'C':
        # only load records with confirmed status
        skip_ct += 1
        continue
      syms = row[5]
      logger.info("Checking for OMIM syms: {}".format(syms))
      for sym in syms.split(', '):
        targets = dba.find_targets({'sym': sym})
        if not targets:
          notfnd[sym] = True
          logger.warn("  Symbol {} not found".format(sym))
          logger.warn("  Row: {}".format(row))
          continue
        for t in targets:
          p = t['components']['protein'][0]
          logger.info("  Symbol {} found target {}: {}, {}".format(sym, t['id'], p['name'], p['description']))
          tmark[t['id']] = True
          val = "MIM Number: %s" % row[8]
          if row[11]:
            val += "; Phenotype: %s" % row[11]
          rv = dba.ins_phenotype({'protein_id': p['id'], 'ptype': 'OMIM', 'trait': val})
          if not rv:
            dba_err_ct += 1
            continue
          pt_ct += 1
      pbar.update(ct)
  pbar.finish()
  print "{} lines processed".format(ct)
  print "  Skipped {} lines (commented lines and lines with unconfirmed status).".format(skip_ct)
  print "Loaded {} OMIM phenotypes for {} targets".format(pt_ct, len(tmark))
  if notfnd:
    print "No target found for {} symbols. See logfile {} for details.".format(len(notfnd), logfile)
    # for s in notfnd.keys():
    #   print "    %s" % s
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details.".format(dba_err_ct, logfile)


if __name__ == '__main__':
  print "\n{} (v{}) [{}]:".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  download(args)
  start_time = time.time()
  load(args)
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))








