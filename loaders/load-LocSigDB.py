#!/usr/bin/env python
# Time-stamp: <2018-05-31 14:39:06 smathias>
"""Load signal localization data into TCRD from LocSigDB CSV file.

Usage:
    load-LocSigDB.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
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
  -d --debug           : turn on debugging output
  -? --help            : print this message and exit 
"""
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2017-2018, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "1.1.0"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import logging
import urllib
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd5logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
DOWNLOAD_DIR = '../data/LocSigDB/'
BASE_URL = 'http://genome.unmc.edu/LocSigDB/doc/'
FILENAME = 'LocSigDB.csv'

def download(args):
  if os.path.exists(DOWNLOAD_DIR + FILENAME):
    os.remove(DOWNLOAD_DIR + FILENAME)
  if not args['--quiet']:
    print "Downloading ", BASE_URL + FILENAME
    print "         to ", DOWNLOAD_DIR + FILENAME
  urllib.urlretrieve(BASE_URL + FILENAME, DOWNLOAD_DIR + FILENAME)

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
  dataset_id = dba.ins_dataset( {'name': 'LocSigDB', 'source': 'File %s from %s'%(FILENAME, BASE_URL), 'app': PROGRAM, 'app_version': __version__, 'url': 'http://genome.unmc.edu/LocSigDB/'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'locsig'})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

  fn = DOWNLOAD_DIR + FILENAME
  line_ct = slmf.wcl(fn)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  if not args['--quiet']:
    print "\nProcessing {} lines in input file {}".format(line_ct, fn)
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
        logger.warn("No target found for Protein(s): {}".format(data[1]))
  pbar.finish()
  print "{} lines processed.".format(ct)
  print "  Skipped {} non-human rows".format(skip_ct)
  print "  Inserted {} new locsig rows for {} proteins".format(ls_ct, len(pmark))
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)
  if notfnd:
    print "No target found for {} input lines. See logfile {} for details".format(len(notfnd), logfile)


if __name__ == '__main__':
  print "\n{} (v{}) [{}]:".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  start_time = time.time()
  download(args)
  load(args)
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))
