#!/usr/bin/env python
# Time-stamp: <2017-01-26 09:08:03 smathias>
"""Load Disease Ontology into TCRD from OBO file.

Usage:
    load-DiseaseOntology.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
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
  -d --debug DEBUGL    : set debugging output level (0-3) [default: 0]
  -? --help            : print this message and exit 
"""
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2016-2017, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.0.0"

import os,sys,time,re
from docopt import docopt
from TCRD import DBAdaptor
import logging
import urllib
import obo
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
LOGFILE = "%s.log" % PROGRAM
DOWNLOAD_DIR = '../data/DiseaseOntology/'
BASE_URL = 'http://purl.obolibrary.org/obo/'
FILENAME = 'doid.obo'
# http://www.obofoundry.org/ontology/doid.html

def download():
  fn = DOWNLOAD_DIR + FILENAME
  if os.path.exists(fn):
    os.remove(fn)
  start_time = time.time()
  print "\nDownloading ", BASE_URL + FILENAME
  print "         to ", fn
  urllib.urlretrieve(BASE_URL + FILENAME, fn)
  elapsed = time.time() - start_time
  print "Done. Elapsed time: %s" % secs2str(elapsed)

def load():
  args = docopt(__doc__, version=__version__)
  dbhost = args['--dbhost']
  dbname = args['--dbname']
  loglevel = int(args['--loglevel'])
  if args['--logfile']:
    logfile = LOGFILE
  else:
    logfile = "%s.log" % PROGRAM
  debug = int(args['--debug'])
  quiet = args['--quiet']
  if debug:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
    
  logger = logging.getLogger(__name__)
  logger.setLevel(loglevel)
  if not debug:
    logger.propagate = False # turns off console logging when debug is 0
  fh = logging.FileHandler(logfile)
  fmtr = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
  fh.setFormatter(fmtr)
  logger.addHandler(fh)

  dba_params = {'dbhost': dbhost, 'dbname': dbname, 'logger_name': __name__}
  dba = DBAdaptor(dba_params)
  dbi = dba.get_dbinfo()
  logger.info("Connected to TCRD database %s (schema ver %s; data ver %s)", args['--dbname'], dbi['schema_ver'], dbi['data_ver'])
  if not quiet:
    print "\nConnected to TCRD database %s (schema ver %s; data ver %s)" % (args['--dbname'], dbi['schema_ver'], dbi['data_ver'])

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
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'do'})
  if not rv:
    print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
    sys.exit(1)
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'do_parent'})
  if not rv:
    print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
    sys.exit(1)
    
  start_time = time.time()
  
  # Parse the Disease Ontology OBO file
  print "\nParsing Disease Ontology file %s" % DOWNLOAD_DIR + FILENAME
  do_parser = obo.Parser(open(DOWNLOAD_DIR + FILENAME))
  do = {}
  for stanza in do_parser:
    do[stanza.tags['id'][0].value] = stanza.tags
  print "Got %d Disease Ontology terms" % len(do.keys())
  
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  if not quiet:
    print "\nLoading %d Disease Ontology terms" % len(do.keys())
  pbar = ProgressBar(widgets=pbar_widgets, maxval=len(do.keys())).start() 
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
  print "%d terms processed." % ct
  print "  Inserted %d new do rows" % do_ct
  print "  Skipped %d non-DOID terms" % skip_ct
  print "  Skipped %d obsolete terms" % obs_ct
  if dba_err_ct > 0:
    print "WARNNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)


def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])

if __name__ == '__main__':
  print "\n%s (v%s) [%s]:" % (PROGRAM, __version__, time.strftime("%c"))
  download()
  load()
  print "\n%s: Done.\n" % PROGRAM
