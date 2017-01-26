#!/usr/local/bin/python
# Time-stamp: <2017-01-13 13:01:34 smathias>
"""Calculate and load all neareast upstream and downstream Tclin from KEGG Pathways into TCRD.

Usage:
    load-KEGGNearestTclins.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
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
  -d --debug DEBUGL    : set debugging output level (0-3) [default: 0]
  -? --help            : print this message and exit 
"""
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2016-2017, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.0.0"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import logging
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])

def calc_and_load():
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
  dataset_id = dba.ins_dataset( {'name': 'KEGG Nearest Tclins', 'source': 'IDG-KMC generated data by Steve Mathias at UNM.', 'app': PROGRAM, 'app_version': __version__, 'comments': 'Nearest upstream and downstream Tclin targets are found and stored based on KEGG Distances.'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'kegg_nearest_tclin'})
  if not rv:
    print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
    sys.exit(1)

  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  tct = dba.get_target_count()
  if not args['--quiet']:
    print "\nProcessing all %d TCRD targets" % tct
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
    print "\n%d targets processed." % ct
    print "  %d non-Tclin targets have upstream Tclin targets" % len(umark)
    print "    Inserted %d upstream kegg_nearest_tclin rows" % uct
    print "  %d non-Tclin targets have downstream Tclin targets" % len(dmark)
    print "    Inserted %d upstream kegg_nearest_tclin rows" % dct
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)


def wcl(fname):
  with open(fname) as f:
    for i, l in enumerate(f):
      pass
  return i + 1

def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])

if __name__ == '__main__':
  print "\n%s (v%s) [%s]:\n" % (PROGRAM, __version__, time.strftime("%c"))
  start_time = time.time()
  calc_and_load()
  elapsed = time.time() - start_time
  print "\n%s: Done. Elapsed time: %s\n" % (PROGRAM, secs2str(elapsed))
