#!/usr/bin/env python
# Time-stamp: <2019-03-19 11:28:47 smathias>
"""Load Uberon Ontology into TCRD from OBO file.

Usage:
    load-Uberon.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-Uberon.py -h | --help

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

import os,sys,time,re
from docopt import docopt
from TCRDMP import DBAdaptor
import logging
import urllib
import obo
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = 'tcrd6logs/'
LOGFILE = LOGDIR + '%s.log'%PROGRAM
DOWNLOAD_DIR = '../data/Uberon/'
BASE_URL = 'http://purl.obolibrary.org/obo/uberon/'
FILENAME = 'ext.obo'

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

def parse_uberon_obo(args, fn):
  uber_parser = obo.Parser(open(fn))
  raw_uber = {}
  for stanza in uber_parser:
    if stanza.name != 'Term':
      continue
    raw_uber[stanza.tags['id'][0].value] = stanza.tags
  uberd = {}
  for uid,ud in raw_uber.items():
    if 'is_obsolete' in ud:
      continue
    if 'name' not in ud:
      continue
    init = {'uid': uid, 'name': ud['name'][0].value}
    if 'def' in ud:
      init['def'] = ud['def'][0].value
    if 'comment' in ud:
      init['comment'] = ud['comment'][0].value
    if 'is_a' in ud:
      init['parents'] = []
      for parent in ud['is_a']:
        # some parent values have a source ie. 'UBERON:0010134 {source="MA"}'
        # get rid of this for now
        cp = parent.value.split(' ')[0]
        init['parents'].append(cp)
    if 'xref' in ud:
      init['xrefs'] = []
      for xref in ud['xref']:
        if xref.value.startswith('http'):
          continue
        try:
          (db, val) = xref.value.split(':')
        except:
          pass
        if not db.isupper():
          # there are all kinds of xrefs like xref: Wolffian:duct
          # skip these
          continue
        if db.endswith('_RETIRED'):
          continue
        init['xrefs'].append({'db': db, 'value': val})
    uberd[uid] = init
  return uberd
  
def load(args, uberd):
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
  dataset_id = dba.ins_dataset( {'name': 'Uberon Ontology', 'source': 'File %s, version %s'%(BASE_URL+FILENAME, ver), 'app': PROGRAM, 'app_version': __version__, 'url': 'http://uberon.github.io/'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'uberon'} ,
            {'dataset_id': dataset_id, 'table_name': 'uberon_parent'},
            {'dataset_id': dataset_id, 'table_name': 'uberon_xref'} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)
    
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  if not args['--quiet']:
    print "\nLoading {} Uberon terms".format(len(uberd))
  pbar = ProgressBar(widgets=pbar_widgets, maxval=len(uberd)).start()
  ct = 0
  uberon_ct = 0
  dba_err_ct = 0
  for uid,ud in uberd.items():
    ct += 1
    ud['uid'] = uid
    rv = dba.ins_uberon(ud)
    if rv:
      uberon_ct += 1
    else:
      dba_err_ct += 1
    pbar.update(ct)
  pbar.finish()
  print "{} terms processed.".format(ct)
  print "  Inserted {} new uberon rows".format(uberon_ct)
  if dba_err_ct > 0:
    print "WARNNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)


if __name__ == '__main__':
  print "\n{} (v{}) [{}]:".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  start_time = time.time()
  download(args)
  if not args['--quiet']:
    print "\nParsing Uberon file {}".format(DOWNLOAD_DIR+FILENAME)
  uberd = parse_uberon_obo(args, DOWNLOAD_DIR+FILENAME)
  if not args['--quiet']:
    print "Got {} good Uberon terms".format(len(uberd))
  load(args, uberd)
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))
