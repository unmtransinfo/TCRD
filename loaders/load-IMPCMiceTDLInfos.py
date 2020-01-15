#!/usr/bin/env python
# Time-stamp: <2019-09-04 12:10:52 smathias>
"""Load IMPC mice tdl_infod into TCRD from CSV file.

Usage:
    load-IMPCMiceTDLInfos.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-IMPCMiceTDLInfos.py -? | --help

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
__copyright__ = "Copyright 2016-2019, Steve Mathias"
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
IMPC_FILE = '../data/IMPC/notifications_by_gene_for_idg-04-09-19--11-09.csv'
OUT_FILE = '../data/IMPC/IDGSummary-TCRDv6.csv'

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
  dataset_id = dba.ins_dataset( {'name': 'IMPC Mouse Clones', 'source': "File %s obtained directly from Terry Meehan/Alba Gomez at EBI."%os.path.basename(IMPC_FILE), 'app': PROGRAM, 'app_version': __version__, 'url': 'http://www.mousephenotype.org/'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'tdl_info', 'where_clause': "itype = 'IMPC Clones'"},
            {'dataset_id': dataset_id, 'table_name': 'tdl_info', 'where_clause': "itype = 'IMPC Status'"} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]

  line_ct = slmf.wcl(IMPC_FILE)
  if not args['--quiet']:
    print "\nProcessing {} rows from input file {}".format(line_ct, IMPC_FILE)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  ct = 0
  skip_ct = 0
  notfnd = set()
  ti1_ct = 0
  ti2_ct = 0
  dba_err_ct = 0
  with open(IMPC_FILE, 'rU') as csvfile:
    csvreader = csv.DictReader(csvfile)
    for d in csvreader:
      # Gene,MGI Accession,Public IDG,Public CMG Tier1,Public CMG Tier 2,Number of notifications,Status,# Clones,Non-Assigned Plans,Assigned plans,Aborted MIs,MIs in Progress,GLT Mice,Private
      ct += 1
      sym = d['Gene'].upper()
      targets = dba.find_targets({'sym': sym})
      if not targets:
        targets = dba.find_targets_by_xref({'xtype': 'MGI ID', 'value': d['MGI Accession']})
      if not targets:
        k = "%s,%s"%(d['Gene'], d['MGI Accession'])
        notfnd.add(k)
        continue
      if not d['Status'] and not d['# Clones']:
        skip_ct += 1
        continue
      tids = list()
      for t in targets:
        pid = t['components']['protein'][0]['id']
        if not d['Status']:
          status = '?'
        else:
          status = d['Status']
        rv = dba.ins_tdl_info({'protein_id': pid, 'itype': 'IMPC Status',
                               'string_value': status})
        if rv:
          ti1_ct += 1
        else:
          dba_err_ct += 1
        if not d['# Clones']:
          continue
        rv = dba.ins_tdl_info({'protein_id': pid, 'itype': 'IMPC Clones',
                               'string_value': d['# Clones']})
        if rv:
          ti2_ct += 1
        else:
          dba_err_ct += 1
      pbar.update(ct)
  pbar.finish()
  for k in notfnd:
    logger.warn("No target found for: {}".format(k))
  if not args['--quiet']:
    print "{} rows processed.".format(ct)
  print "Inserted {} new 'IMPC Status' tdl_info rows".format(ti1_ct)
  print "Inserted {} new 'IMPC Clones' tdl_info rows".format(ti2_ct)
  print "Skipped {} rows with no relevant info".format(skip_ct)
  if notfnd:
    print "No target found for {} rows. See logfile {} for details.".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)
    

if __name__ == '__main__':
  print "\n{} (v{}) [{}]:".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  start_time = time.time()
  load(args)
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))
