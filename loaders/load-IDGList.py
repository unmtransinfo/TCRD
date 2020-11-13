#!/usr/bin/env python
# Time-stamp: <2020-05-08 12:25:12 smathias>
"""Load IDG Phase 2 flags and families into TCRD from CSV file.

Usage:
    load-IDG2List.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-IDG2List.py | --help

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

import os,sys,time
from docopt import docopt
from TCRD7 import DBAdaptor
import logging
import csv
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd7logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
IDG_LIST_FILE = '../data/IDG_Lists/IDG_List_v3.2_SLM20200508.csv'

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
  dataset_id = dba.ins_dataset( {'name': 'IDG Eligible Targets List', 'source': 'IDG generated data in file %s.'%IDG_LIST_FILE, 'app': PROGRAM, 'app_version': __version__, 'comments': 'IDG Flags and Families set from list of targets on GitHub.', 'url': 'https://github.com/druggablegenome/IDGTargets'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'target', 'column_name': 'idg', 'where_clause': 'column_name == "idg"'},
            {'dataset_id': dataset_id, 'table_name': 'target', 'column_name': 'fam', 'where_clause': 'column_name == "fam"', 'where_clause': 'idg == 1'},
            {'dataset_id': dataset_id, 'table_name': 'target', 'column_name': 'famext', 'where_clause': 'column_name == "fam"', 'where_clause': 'idg == 1'}]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

  pbar_widgets = ['Progress: ', Percentage(), ' ', Bar(marker='#',left='[',right=']'), ' ', ETA()]
  line_ct = slmf.wcl(IDG_LIST_FILE)
  print '\nProcessing {} lines in list file {}'.format(line_ct, IDG_LIST_FILE)
  logger.info("Processing {} lines in list file {}".format(line_ct, IDG_LIST_FILE))
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start()
  notfnd = []
  multfnd = []
  ct = 0
  idg_ct = 0
  fam_ct = 0
  famext_ct = 0
  dba_err_ct = 0
  with open(IDG_LIST_FILE, 'rU') as ifh:
    csvreader = csv.reader(ifh)
    #header = csvreader.next() # skip header line
    #ct += 1
    for row in csvreader:
      ct += 1
      sym = row[0]
      fam = row[2]
      targets = dba.find_targets({'sym': sym}, idg=False, include_annotations=False)
      if not targets:
        notfnd.append(sym)
        continue
      if len(targets) > 1:
        multfnd.append(sym)
      for t in targets:
        rv = dba.upd_target(t['id'], 'idg', 1)
        if rv:
          idg_ct += 1
        else:
          dba_err_ct += 1
        rv = dba.upd_target(t['id'], 'fam', fam)
        if rv:
          fam_ct += 1
        else:
          dba_err_ct += 1
        if row[3]:
          famext = row[3]
          rv = dba.upd_target(t['id'], 'famext', famext)
          if rv:
            famext_ct += 1
          else:
            dba_err_ct += 1
      pbar.update(ct)
  pbar.finish()
  print "{} lines processed".format(ct)
  print "{} targets updated with IDG flags".format(idg_ct)
  print "{} targets updated with fams".format(fam_ct)
  print "  {} targets updated with famexts".format(famext_ct)
  if notfnd:
    print "No target found for {} symbols: {}".format(len(notfnd), ", ".join(notfnd))
  if multfnd:
    print "Multiple targets found for {} symbols: {}".format(len(multfnd), ", ".join(multfnd))
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

