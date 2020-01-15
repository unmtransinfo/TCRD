#!/usr/bin/env python
# Time-stamp: <2019-08-21 10:33:02 smathias>
"""Load Uberon IDs into TCRD expression table.

Usage:
    load-Uberon-IDs.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-Uberon-IDs.py -h | --help

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
import ast
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = 'tcrd6logs/'
LOGFILE = LOGDIR + '%s.log'%PROGRAM
# This file contains a manually currated dict mapping tissue names to Uberon IDs.
# These are ones for which TCRDMP.get_uberon_id does not return a uid.
TISSUE2UBERON_FILE = '../data/Tissue2Uberon.txt'
ETYPE = 'UniProt Tissue'
  
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

  with open(TISSUE2UBERON_FILE, 'r') as ifh:
    tiss2uid = ast.literal_eval(ifh.read())
  if not args['--quiet']:
    print "\nGot {} tissue to Uberon ID mappings from file {}".format(len(tiss2uid), TISSUE2UBERON_FILE)
    
  exp_ct = dba.get_expression_count(etype=ETYPE)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  if not args['--quiet']:
    print "\nProcessing {} {} expression rows".format(exp_ct, ETYPE)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=exp_ct).start()
  ct = 0
  nouid = set()
  upd_ct = 0
  dba_err_ct = 0
  for exp in dba.get_expressions(etype=ETYPE):
    ct += 1
    uberon_id = None
    if exp['oid']:
      uberon_id = dba.get_uberon_id({'oid': exp['oid']})
    if not uberon_id:
      uberon_id = dba.get_uberon_id({'name': exp['tissue']})
    if not uberon_id and exp['tissue'] in tiss2uid:
      uberon_id = tiss2uid[exp['tissue']]
    if not uberon_id:
      nouid.add(exp['tissue'])
      continue
    rv = dba.do_update({'table': 'expression', 'id': exp['id'],
                        'col': 'uberon_id', 'val': uberon_id})
    if rv:
      upd_ct += 1
    else:
      dba_err_ct += 1
    pbar.update(ct)
  pbar.finish()
  for t in nouid:
    logger.warn("No Uberon ID found for {}".format(t))
  print "{} {} expression rows processed.".format(ct, ETYPE)
  print "  Updated {} with Uberon IDs".format(upd_ct)
  if nouid:
    print "No Uberon ID found for {} tissues. See logfile {} for details.".format(len(nouid), logfile)
  if dba_err_ct > 0:
    print "WARNNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)


if __name__ == '__main__':
  print "\n{} (v{}) [{}]:".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  start_time = time.time()
  load(args)
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))
