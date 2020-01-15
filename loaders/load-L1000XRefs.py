#!/usr/bin/env python
# Time-stamp: <2019-08-27 15:38:52 smathias>
"""Load CMap Landmark Gene ID xrefs into TCRD from CSV file.

Usage:
    load-L1000XRefs.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-L1000XRefs.py -? | --help

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
__copyright__ = "Copyright 2015-2019, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "3.0.0"

import os,sys,time
from docopt import docopt
from TCRDMP import DBAdaptor
import logging
import csv
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd6logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
L1000_FILE = '../data/CMap_LandmarkGenes_n978.csv'

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
  dataset_id = dba.ins_dataset( {'name': 'LINCS L1000 XRefs', 'source': 'File %s'%os.path.basename(L1000_FILE), 'app': PROGRAM, 'app_version': __version__, 'url': 'http://support.lincscloud.org/hc/en-us/articles/202092616-The-Landmark-Genes'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'xref', 'where_clause': "dataset_id = %d"%dataset_id})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)
  
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]

  line_ct = slmf.wcl(L1000_FILE)
  if not args['--quiet']:
    print "\nProcessing {} rows in file {}".format(line_ct, L1000_FILE)
  with open(L1000_FILE, 'rU') as csvfile:
    csvreader = csv.reader(csvfile)
    ct = 0
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start()
    ct = 0
    pmark = {}
    xref_ct = 0
    notfnd = set()
    dba_err_ct = 0
    for row in csvreader:
      ct += 1
      pbar.update(ct)
      l1000 = row[0]
      sym = row[1]
      geneid = row[2]
      targets = dba.find_targets({'sym': sym})
      if not targets:
        targets = dba.find_targets({'geneid': geneid})
        if not targets:
          continue
      target = targets[0]
      pid = target['components']['protein'][0]['id']
      rv = dba.ins_xref({'protein_id': pid, 'xtype': 'L1000 ID',
                         'dataset_id': dataset_id, 'value': l1000})
      if rv:
        xref_ct += 1
        pmark[pid] = True
      else:
        dba_err_ct += 1
  pbar.finish()
  for k in notfnd:
    logger.warn("No target found for {}".format(k))
  print "{} rows processed.".format(ct)
  print "  Inserted {} new L1000 ID xref rows for {} proteins.".format(xref_ct, len(pmark))
  if len(notfnd) > 0:
    print "No target found for {} symbols/geneids. See logfile {} for details.".format(len(notfnd), logfile)
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
