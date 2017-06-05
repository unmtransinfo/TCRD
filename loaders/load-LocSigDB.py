#!/usr/bin/env python
# Time-stamp: <2017-05-04 12:38:41 smathias>
"""Load signal localization data into TCRD from LocSigDB CSV file.

Usage:
    load-LocSigDB.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-LocSigDB.py -? | --help

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
__copyright__ = "Copyright 2017, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "1.0.0"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import logging
import urllib
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
DOWNLOAD_DIR = '../data/LocSigDB/'
BASE_URL = 'http://genome.unmc.edu/LocSigDB/doc/LocSigDB.csv'
FILENAME = 'LocSigDB.csv'

def download():
  if os.path.exists(DOWNLOAD_DIR + FILENAME):
    os.remove(DOWNLOAD_DIR + FILENAME)
  print "Downloading ", BASE_URL + FILENAME
  print "         to ", DOWNLOAD_DIR + FILENAME
  urllib.urlretrieve(BASE_URL + FILENAME, DOWNLOAD_DIR + FILENAME)

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
    print "Connected to TCRD database %s (schema ver %s; data ver %s)" % (args['--dbname'], dbi['schema_ver'], dbi['data_ver'])

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'LocSigDB', 'source': 'File %s from %s'%(FILENAME, BASE_URL), 'app': PROGRAM, 'app_version': __version__, 'url': 'http://genome.unmc.edu/LocSigDB/'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'locsig'})
  if not rv:
    print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
    sys.exit(1)

  start_time = time.time()
  fn = DOWNLOAD_DIR + FILENAME
  line_ct = wcl(fn)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  if not args['--quiet']:
    print "\nProcessing %d lines in input file %s" % (line_ct, fn)
  with open(fn, 'rU') as f:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    ct = 0
    up2pid = {}
    up_notfnd = {}
    ls_ct = 0
    skip_ct = 0
    pmark = set()
    notfnd = set()
    dba_err_ct = 0
    for line in f:
      ct += 1
      pbar.update(ct)
      data = line.split(',')
      if 'Homo sapiens' not in data[5]:
        skip_ct += 1
        continue
      fnd = False
      for up in data[4].split(';'):
        if up in up2pid:
          fnd = True
          pid = up2pid[up]
          rv = dba.ins_locsig( {'protein_id': pid, 'location': data[2],
                                'signal': data[0], 'pmids': data[3]} )
          if not rv:
            dba_err_ct += 1
            continue
          ls_ct += 1
        elif up in up_notfnd:
          continue
        else:
          targets = dba.find_targets({'uniprot': up})
          if targets:
            fnd = True
            t = targets[0]
            pid = t['components']['protein'][0]['id']
            pmark.add(pid)
            up2pid[up] = pid
            rv = dba.ins_locsig( {'protein_id': pid, 'location': data[2],
                                  'signal': data[0], 'pmids': data[3]} )
            if not rv:
              dba_err_ct += 1
              continue
            ls_ct += 1
      if not fnd:
        notfnd.add(data[1])
        logger.warn("No target found for Protein(s): %s" % data[1])
        continue

  pbar.finish()
  elapsed = time.time() - start_time
  print "%d rows processed. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "  Skipped %d non-human rows" % skip_ct
  print "  %d proteins have locsig(s)" % len(pmark)
  print "  Inserted %d new locsig rows" % ls_ct
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)
  if notfnd:
    print "No target found for %d input lines. See logfile %s for details" % (len(notfnd), logfile)


def wcl(fname):
  with open(fname) as f:
    for i, l in enumerate(f):
      pass
  return i + 1

def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])

if __name__ == '__main__':
  print "\n%s (v%s) [%s]:\n" % (PROGRAM, __version__, time.strftime("%c"))
  #download()
  load()
  print "\n%s: Done.\n" % PROGRAM
