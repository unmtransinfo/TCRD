#!/usr/bin/env python
# Time-stamp: <2018-05-18 12:03:58 smathias>
"""Load IDG Phase 2 flags into TCRD.

Usage:
    load-IDG2.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-IDG2.py | --help

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
__copyright__ = "Copyright 2018, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.1.0"

import sys
from docopt import docopt
from TCRD import DBAdaptor
import csv
import logging
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = 'tcrd5logs/'
LOGFILE = LOGDIR + '%s.log'%PROGRAM
INFILE = '../data/DRGC_RevisedTargetLists.csv'

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
  logger.info("Connected to TCRD database %s (schema ver %s; data ver %s)", args['--dbname'], dbi['schema_ver'], dbi['data_ver'])
  if not args['--quiet']:
    print "\nConnected to TCRD database %s (schema ver %s; data ver %s)" % (args['--dbname'], dbi['schema_ver'], dbi['data_ver'])
  
  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'IDG Phase 2 Flags', 'source': 'IDG generated data.', 'app': PROGRAM, 'app_version': __version__, 'comments': 'Flags set from lists of targets from the DRGCs.'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'target', 'column_name': 'idg2'})
  if not rv:
    print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
    sys.exit(1)

  line_ct = slmf.wcl(INFILE)
  if not args['--quiet']:
    print "\nProcessing {} lines in input file {}".format(line_ct, INFILE)
  pbar_widgets = ['Progress: ', Percentage(), ' ', Bar(marker='#',left='[',right=']'), ' ', ETA()]
  with open(INFILE, 'rU') as ifh:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    tsvreader = csv.reader(ifh)
    ct = 0
    notfnd = set()
    multfnd = set()
    upd_ct = 0
    skip_ct = 0
    dba_err_ct = 0
    tmark = {}
    dups = set()
    for row in tsvreader:
      ct += 1
      sym = row[0]
      if sym in tmark:
        #print "Skipping dup sym {}".format(sym)
        dups.add(sym)
        continue
      flag = row[1].lower().strip()
      if flag == 'removed':
        skip_ct += 1
        continue
      elif flag == 'deprioritized':
        flag = 2
      else:
        # Add and yes
        flag = 1
      targets = dba.find_targets({'sym': sym}, idg=False, include_annotations=False)
      if not targets:
        notfnd.add(sym)
        continue
      if len(targets) > 1:
        multfnd.add(sym)
      for t in targets:
        tmark[sym] = True
        rv = dba.upd_target(t['id'], 'idg2', flag)
        if rv:
          upd_ct += 1
        else:
          dba_err_ct += 1
      pbar.update(ct)
  pbar.finish()
  print "{} lines processed".format(ct)
  print "{} targets updated with IDG2 flags".format(upd_ct)
  print "Skipped {} 'removed' lines".format(skip_ct)
  if notfnd:
    print "No target found for {} symbols: {}".format(len(notfnd), ", ".join(notfnd))
  if multfnd:
    print "Multiple targets found for {} symbols: {}".format(len(multfnd), ", ".join(multfnd))
  if dups:
    print "Encountered {} duplicate symbols: {}".format(len(dups), ", ".join(dups))
  if dba_err_ct > 0:
    print "WARNING: {} database errors occured. See logfile {} for details.".format(dba_err_ct, logfile)
  

if __name__ == '__main__':
  print "\n{} (v{}) [{}]:".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  start_time = time.time()
  load(args)
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))

