#!/usr/bin/env python
# Time-stamp: <2018-05-17 11:04:59 smathias>
"""Load Disease Ontology into TCRD from OBO file.

Usage:
    load-DiseaseOntology.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-DiseaseOntology.py -h | --help

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
__copyright__ = "Copyright 2016-2018, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.1.0"

import os,sys,time,re
from docopt import docopt
from TCRD import DBAdaptor
import logging
import urllib
import obo
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = 'tcrd5logs/'
LOGFILE = LOGDIR + '%s.log'%PROGRAM
DOWNLOAD_DIR = '../data/DiseaseOntology/'
BASE_URL = 'http://purl.obolibrary.org/obo/'
FILENAME = 'doid.obo'
# http://www.obofoundry.org/ontology/doid.html

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
  # data-version field in the header of the OBO file has a relase version:
  # data-version: releases/2016-03-25
  f = os.popen("head %s"%DOWNLOAD_DIR + FILENAME)
  for line in f:
    if line.startswith("data-version:"):
      ver = line.replace('data-version: ', '')
      break
  f.close()
  dataset_id = dba.ins_dataset( {'name': 'Disease Ontology', 'source': 'File %s, version %s'%(BASE_URL+FILENAME, ver), 'app': PROGRAM, 'app_version': __version__, 'url': 'http://disease-ontology.org/'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'do'})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'do_parent'})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)
    
  # Parse the Disease Ontology OBO file
  if not args['--quiet']:
    print "\nParsing Disease Ontology file {}".format(DOWNLOAD_DIR + FILENAME)
  do_parser = obo.Parser(open(DOWNLOAD_DIR + FILENAME))
  do = {}
  for stanza in do_parser:
    do[stanza.tags['id'][0].value] = stanza.tags
  print "Got {} Disease Ontology terms".format(len(do))
  
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  if not args['--quiet']:
    print "\nLoading {} Disease Ontology terms".format(len(do))
  pbar = ProgressBar(widgets=pbar_widgets, maxval=len(do)).start()
  ct = 0
  do_ct = 0
  skip_ct = 0
  obs_ct = 0
  dba_err_ct = 0
  for doid,dod in do.items():
    ct += 1
    if not doid.startswith('DOID:'):
      skip_ct += 1
      continue
    if 'is_obsolete' in dod:
      obs_ct += 1
      continue
    init = {'id': doid, 'name': dod['name'][0].value}
    if 'def' in dod:
      init['def'] = dod['def'][0].value
    if 'is_a' in dod:
      init['parents'] = []
      for parent in dod['is_a']:
        init['parents'].append(parent.value)
    rv = dba.ins_do(init)
    if rv:
      do_ct += 1
    else:
      dba_err_ct += 1
    pbar.update(ct)
  pbar.finish()
  print "{} terms processed.".format(ct)
  print "  Inserted {} new do rows".format(do_ct)
  print "  Skipped {} non-DOID terms".format(skip_ct)
  print "  Skipped {} obsolete terms".format(obs_ct)
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
