#!/usr/bin/env python
# Time-stamp: <2017-01-05 16:35:08 smathias>
"""Load antibody count and URL tdl_infos into TCRD via Antibodtpedia.com API.

Usage:
    load-Antibodtpedia.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-Antibodtpedia.py -h | --help

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
__author__ = "Steve Mathias"
__email__ = "smathias@salud.unm.edu"
__org__ = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2016, Steve Mathias"
__license__ = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__ = "2.0.0"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import logging
import requests
import json
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
DBHOST = 'localhost'
DBPORT = 3306
DBNAME = 'tcrdev'
LOGFILE = "%s.log" % PROGRAM
ABPC_API_URL = 'http://www.antibodypedia.com/tools/antibodies.php?uniprot='

def main():
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
    print "\n%s (v%s) [%s]:" % (PROGRAM, __version__, time.strftime("%c"))
    print "\nConnected to TCRD database %s (schema ver %s; data ver %s)" % (args['--dbname'], dbi['schema_ver'], dbi['data_ver'])

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'Aintibodypedia.com', 'source': 'Web API at %s'%ABPC_API_URL, 'app': PROGRAM, 'app_version': __version__, 'url': 'http://www.antibodypedia.com'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'tdl_info', 'where_clause': 'itype == "Ab Count"'},
            {'dataset_id': dataset_id, 'table_name': 'tdl_info', 'where_clause': 'itype == "MAb Count"'},
            {'dataset_id': dataset_id, 'table_name': 'tdl_info', 'where_clause': 'itype == "Antibodypedia.com URL"'} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    if not rv:
      print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
      sys.exit(1)

  start_time = time.time()
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  tct = dba.get_target_count()
  if not args['--quiet']:
    print "\nLoading Antibodypedia annotations for %d TCRD targets" % tct
  logger.info("Loading Antibodypedia annotations for %d TCRD targets" % tct)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=tct).start()  
  ct = 0
  tiab_ct = 0
  timab_ct = 0
  tiurl_ct = 0
  dba_err_ct = 0
  net_err_ct = 0
  for target in dba.get_targets():
    ct += 1
    pbar.update(ct)
    tid = target['id']
    p = target['components']['protein'][0]
    pid = p['id']
    up = p['uniprot']
    url = ABPC_API_URL + up
    r = None
    attempts = 1
    while attempts <= 5:
      try:
        logger.info("Getting %s [Target %d, attempt %d]" % (url, tid, attempts))
        r = requests.get(url)
        break
      except:
        attempts += 1
        time.sleep(1)
    if not r:
      net_err_ct += 1
      logger.error("No response for %s [Target %d, attempt %d]" % (url, tid, attempts))
      continue
    if r.status_code != 200:
      net_err_ct += 1
      logger.error("Bad response: %s for %s [Target %d, attempt %d]" % (r.status_code, url, tid, attempts))
      continue
    abpd = json.loads(r.text)
    rv = dba.ins_tdl_info({'protein_id': pid, 'itype': 'Ab Count',
                           'integer_value': int(abpd['num_antibodies'])})
    if rv:
      tiab_ct += 1
    else:
      dba_err_ct += 1
    if 'ab_type_monoclonal' in abpd:
      mab_ct = int(abpd['ab_type_monoclonal'])
    else:
      mab_ct = 0
    rv = dba.ins_tdl_info({'protein_id': pid, 'itype': 'MAb Count',
                           'integer_value': mab_ct})
    if rv:
      timab_ct += 1
    else:
      dba_err_ct += 1
    rv = dba.ins_tdl_info({'protein_id': pid, 'itype': 'Antibodypedia.com URL',
                           'string_value': abpd['url']})
    if rv:
      timab_ct += 1
    else:
      dba_err_ct += 1
    tiurl_ct += 1
    time.sleep(1)
    pbar.update(ct)
  pbar.finish()
  elapsed = time.time() - start_time
  print "%d TCRD targets processed. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "  Inserted %d Ab Count tdl_info rows" % tiab_ct
  print "  Inserted %d MAb Count tdl_info rows" % timab_ct
  print "  Inserted %d Antibodypedia URL tdl_info rows" % tiurl_ct
  if net_err_ct > 0:
    print "WARNING: Network error for %d targets. See logfile %s for details." % (net_err_ct, logfile)
  print "\n%s: Done." % PROGRAM
  print

def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])


if __name__ == '__main__':
    main()
