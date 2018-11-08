#!/usr/local/bin/python
# Time-stamp: <2018-05-31 09:49:34 smathias>
"""Calculate and load all neareast upstream and downstream Tclin from KEGG Pathways into TCRD.

Usage:
    load-KEGGNearestTclins.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-KEGGNearestTclins.py -? | --help

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

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import logging
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd5logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)

def calc_and_load(args):
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
  dataset_id = dba.ins_dataset( {'name': 'KEGG Nearest Tclins', 'source': 'IDG-KMC generated data by Steve Mathias at UNM.', 'app': PROGRAM, 'app_version': __version__, 'comments': 'Nearest upstream and downstream Tclin targets are found and stored based on KEGG Distances.'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'kegg_nearest_tclin'})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  
  tct = dba.get_target_count()
  if not args['--quiet']:
    print "\nProcessing {} TCRD targets".format(tct)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=tct).start() 
  ct = 0
  uct = 0
  umark = set()
  dct = 0
  dmark = set()
  dba_err_ct = 0
  for target in dba.get_targets():
  #tids = [1983, 7166]
  #for tid in tids:
  #  target = dba.get_target(tid)
    ct += 1
    if target['tdl'] == 'Tclin':
      continue
    pid = target['components']['protein'][0]['id']
    ups = dba.get_nearest_kegg_tclins(pid, 'upstream')
    if ups:
      umark.add(pid)
      for d in ups:
        d['tclin_id'] = d['protein_id']
        d['protein_id'] = pid
        d['direction'] = 'upstream'
        rv = dba.ins_kegg_nearest_tclin(d)
        if rv:
          uct += 1
        else:
          dba_err_ct += 1
    dns = dba.get_nearest_kegg_tclins(pid, 'downstream')
    if dns:
      dmark.add(pid)
      for d in dns:
        d['tclin_id'] = d['protein_id']
        d['protein_id'] = pid
        d['direction'] = 'downstream'
        rv = dba.ins_kegg_nearest_tclin(d)
        if rv:
          dct += 1
        else:
          dba_err_ct += 1
    pbar.update(ct)
  pbar.finish()

  if not args['--quiet']:
    print "\n{} targets processed.".format(ct)
    print "  {} non-Tclin targets have upstream Tclin targets".format(len(umark))
    print "    Inserted {} upstream kegg_nearest_tclin rows".format(uct)
    print "  {} non-Tclin targets have downstream Tclin targets".format(len(dmark))
    print "    Inserted {} upstream kegg_nearest_tclin rows".format(dct)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)


if __name__ == '__main__':
  print "\n{} (v{}) [{}]:".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  start_time = time.time()
  calc_and_load(args)
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))
