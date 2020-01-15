#!/usr/bin/env python
# Time-stamp: <2019-02-06 11:46:19 smathias>
"""Load Mammalian Phenotype Ontology into TCRD from OWL file.

Usage:
    load-MPO.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-MPO.py -h | --help

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
__copyright__ = "Copyright 2019, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "1.0.0"

import os,sys,time
from docopt import docopt
from TCRDMP import DBAdaptor
import logging
import urllib
import pronto
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = 'tcrd6logs/'
LOGFILE = LOGDIR + '%s.log'%PROGRAM
DOWNLOAD_DIR = '../data/MPO/'
BASE_URL = 'http://www.informatics.jax.org/downloads/reports/'
FILENAME = 'mp.owl'

def download(args):
  fn = DOWNLOAD_DIR + FILENAME
  if os.path.exists(fn):
    os.remove(fn)
  if not args['--quiet']:
    print "\nDownloading ", BASE_URL + FILENAME
    print "         to ", fn
  urllib.urlretrieve(BASE_URL + FILENAME, fn)
  if not args['--quiet']:
    print "Done."

def parse_mp_owl(f):
  mp = []
  mpont = pronto.Ontology(f)
  for term in mpont:
    if not term.id.startswith('MP:'):
      continue
    mpid = term.id
    name = term.name
    init = {'mpid': mpid, 'name': name}
    if term.parents:
      init['parent_id'] = term.parents[0].id
    if term.desc:
      if term.desc.startswith('OBSOLETE'):
        continue
      init['def'] = term.desc
    mp.append(init)
  return mp

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

  # Parse the MP OWL file
  if not args['--quiet']:
    print "\nParsing Mammalian Phenotype Ontology file {}".format(DOWNLOAD_DIR + FILENAME)
  mp = parse_mp_owl(DOWNLOAD_DIR + FILENAME)
  print "Got {} MP terms".format(len(mp))

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'Mammalian Phenotype Ontology', 'source': 'OWL file downloaded from %s'%BASE_URL+FILENAME, 'app': PROGRAM, 'app_version': __version__} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'mpo'})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)
  
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  if not args['--quiet']:
    print "\nLoading {} Mammalian Phenotype Ontology terms".format(len(mp))
  pbar = ProgressBar(widgets=pbar_widgets, maxval=len(mp)).start()
  ct = 0
  mpo_ct = 0
  dba_err_ct = 0
  for mpd in mp:
    ct += 1
    rv = dba.ins_mpo(mpd)
    if rv:
      mpo_ct += 1
    else:
      dba_err_ct += 1
    pbar.update(ct)
  pbar.finish()
  print "{} terms processed.".format(ct)
  print "  Inserted {} new mpo rows".format(mpo_ct)
  if dba_err_ct > 0:
    print "WARNNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)


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
