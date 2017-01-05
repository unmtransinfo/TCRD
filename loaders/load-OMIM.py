#!/usr/bin/env python
# Time-stamp: <2017-01-05 16:39:48 smathias>
"""Load phenotypes into TCRD from OMIM genemap.txt file.

Usage:
    load-OMIM.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
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
  -d --debug DEBUGL    : set debugging output level (0-3) [default: 0]
  -? --help            : print this message and exit 
"""
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2015-2016, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.0.0"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import csv
import logging
import urllib
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
# One must register to get OMIM downloads. Last time I did, the link to get them was:
DOWNLOAD_DIR = '../data/OMIM/'
BASE_URL = 'http://omim.org/downloads/ey9G4kaCTGCQ-q_Yx0XAPg/'
FILENAME = 'genemap.txt'

def download():
  if os.path.exists(DOWNLOAD_DIR + FILENAME):
    os.rename(DOWNLOAD_DIR + FILENAME, DOWNLOAD_DIR + FILENAME + '.bak')
  print "\nDownloading ", BASE_URL + FILENAME
  print "         to ", DOWNLOAD_DIR + FILENAME
  urllib.urlretrieve(BASE_URL + FILENAME, DOWNLOAD_DIR + FILENAME)
  print "Done."

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
  line_ct = wcl(fname)
  line_ct -= 1 
  if not args['--quiet']:
    print '\nProcessing %d lines from input file %s' % (line_ct, fname)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start()
  outlist = []
  with open(fname, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    # there are three header lines
    tsvreader.next()
    tsvreader.next()
    tsvreader.next()
    ct = 0
    notfnd = {}
    tmark = {}
    skip_ct = 0
    pt_ct = 0
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
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
      if row[0].startswith('#'):
        # The file ends with a lot of commented lines describing the fields
        skip_ct += 1
        continue
      if row[6] != 'C':
        # only load records with confirmed status
        skip_ct += 1
        continue
      syms = row[5]
      logger.info("Checking for OMIM syms: %s" % syms)
      for sym in syms.split(', '):
        targets = dba.find_targets({'sym': sym})
        if not targets:
          notfnd['sym'] = True
          logger.warn("  Symbol %s not found" % sym)
          continue
        for t in targets:
          p = t['components']['protein'][0]
          logger.info("  %s found target %d: %s, %s" % (sym, t['id'], p['name'], p['description']))
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

  print "%d lines processed." % ct
  print "Loaded %d OMIM phenotypes for %d targets" % (pt_ct, len(tmark.keys()))
  print "  Skipped %d lines (commented lines and lines with unconfirmed status)." % skip_ct
  if notfnd:
    print "No target found for %d symbols:" % len(notfnd.keys())
    for s in notfnd.keys():
      print "    %s" % s
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)

def wcl(fname):
  with open(fname) as f:
    for i, l in enumerate(f):
      pass
  return i + 1

if __name__ == '__main__':
  print "\n%s (v%s) [%s]:" % (PROGRAM, __version__, time.strftime("%c"))
  download()
  load()
  print "\n%s: Done.\n" % PROGRAM









