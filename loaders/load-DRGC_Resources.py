#!/usr/bin/env python
# Time-stamp: <2020-11-23 12:18:13 smathias>
"""Load DRGC resource data into TCRD via RSS API.

Usage:
    load-DRGC_Resources.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-DRGC_Resources.py -? | --help

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
__copyright__ = "Copyright 2019-2020, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "3.0.0"

import os,sys,time,re
from docopt import docopt
from TCRD7 import DBAdaptor
import urllib,json,codecs
import logging
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd6logs"
#LOGDIR = "./tcrd7logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
# API Docs: https://rss.ccs.miami.edu/rss-apis/
RSS_API_BASE_URL = 'https://rss.ccs.miami.edu/rss-api/'

def load(args, dba, logfile, logger):
  
    
  if not args['--quiet']:
    print "\nGetting targets from RSS..."
  target_data = get_target_data()
  if not args['--quiet']:
    print "  Got {} targets with DRGC resource(s)".format(len(target_data['data']))
  ct = 0
  res_ct = 0
  tmark = {}
  notfnd = set()
  derr_ct = 0
  dba_err_ct = 0
  re1 = re.compile(r'NanoLuc.+-\s*(\w+)')
  re2 = re.compile(r'(\w+)\s*-NanoLuc.+')
  re3 = re.compile(r'NanoLuc.+-fused\s*(\w+)')
  for d in target_data['data']:
    ct += 1
    logger.info("Processing target data: {}".format(d))
    rt = d['resourceType'].replace(' ', '').lower()
    # for now, skip Datasets
    if rt == 'dataset':
      continue
      # m = re1.search(d['target'])
      # if not m:
      #   m = re2.search(d['target'])
      # if not m:
      #   m = re3.search(d['target'])
      # if not m:
      #   logger.warn("No target symbol found for data dict: {}".format(d))
      #   derr_ct += 1
      #   continue
      # sym = m.groups(1)
    else:
      sym = d['target']
    resource_data = get_resource_data(rt, d['id'])
    dbjson = json.dumps(resource_data['data'][0]['resource'])
    targets = dba.find_targets({'sym': sym}, False)
    if not targets:
      notfnd.add(sym)
      logger.warn("No target found for {}".format(sym))
      continue
    tid = targets[0]['id']
    rv = dba.ins_drgc_resource( {'target_id': tid, 'resource_type': d['resourceType'],
                                 'json': dbjson} )
    if not rv:
      dba_err_ct += 1
      continue
    tmark[tid] = True
    res_ct += 1
  print "{} targets processed.".format(ct)
  print "  Inserted {} new drgc_resource rows for {} targets".format(res_ct, len(tmark))
  if notfnd:
    print "No target found for {} symbols. See logfile {} for details.".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

def get_target_data():
  url = RSS_API_BASE_URL + 'target'
  jsondata = None
  attempts = 0
  while attempts < 5:
    try:
      jsondata = json.loads(urllib.urlopen(url).read().decode('latin-1'))
      break
    except Exception as e:
      attempts += 1
  if jsondata:
    return jsondata
  else:
    return False

def get_resource_data(resource_type, resource_id):
  url = "%sreagents/%s/id?id=%s" % (RSS_API_BASE_URL, resource_type, resource_id)
  jsondata = None
  attempts = 0
  while attempts < 5:
    try:
      jsondata = json.loads(urllib.urlopen(url).read())
      break
    except Exception as e:
      attempts += 1
  if jsondata:
    return jsondata
  else:
    return False


if __name__ == '__main__':
  print "\n%s (v%s) [%s]:\n" % (PROGRAM, __version__, time.strftime("%c"))
  
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  if args['--logfile']:
    logfile =  args['--logfile']
  else:
    logfile = LOGFILE
  loglevel = int(args['--loglevel'])
  logger = logging.getLogger(__name__)
  logger.setLevel(loglevel)
  if not args['--debug']:
    logger.propagate = False # turns off console logging
  fh = logging.FileHandler(LOGFILE)
  fmtr = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
  fh.setFormatter(fmtr)
  logger.addHandler(fh)

  dba_params = {'dbhost': args['--dbhost'], 'dbname': args['--dbname'], 'logger_name': __name__}
  dba = DBAdaptor(dba_params)
  dbi = dba.get_dbinfo()
  logger.info("Connected to TCRD database {} (schema ver {}; data ver {})".format(args['--dbname'], dbi['schema_ver'], dbi['data_ver']))
  if not args['--quiet']:
    print "Connected to TCRD database {} (schema ver {}; data ver {})".format(args['--dbname'], dbi['schema_ver'], dbi['data_ver'])

  download(args)
  start_time = time.time()
  load(args, dba, logfile, logger)
  elapsed = time.time() - start_time

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'DRGC Resources', 'source': 'RSS APIs at http://dev3.ccs.miami.edu:8080/rss-apis/', 'app': PROGRAM, 'app_version': __version__, 'url': 'http://dev3.ccs.miami.edu:8080/rss-apis/'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'drgc_resource'})
  if not rv:
    print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
    sys.exit(1)
      
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))

