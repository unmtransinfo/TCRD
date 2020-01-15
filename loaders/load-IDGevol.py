#!/usr/bin/env python
# Time-stamp: <2020-01-10 13:29:54 smathias>
"""Load previous versions IDG flag data into TCRD from CSV files.

Usage:
    load-IDGevol.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-IDGevol.py -? | --help

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
__copyright__ = "Copyright 2020, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "1.0.0"

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
DATA_DIR = '../data/IDGevol/'
INPUTFILES = [ ('1', 'TCRDv1.5.6_IDG.csv'),
               ('2', 'TCRDv2.4.2_IDG.csv'),
               ('3', 'TCRDv3.1.5_IDG.csv'),
               ('4', 'TCRDv4.1.0_IDG.csv'),
               ('5', 'TCRDv5.4.4_IDG.csv'),
               ('6', 'TCRDv6.3.0_IDG.csv') ]
    
def load(args, dba, logfile, logger, ver, fn):
  line_ct = slmf.wcl(fn)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  if not args['--quiet']:
    print "\nProcessing {} lines in file {}".format(line_ct, fn)
  ct = 0
  ins_ct = 0
  dba_err_ct = 0
  with open(fn, 'rU') as ifh:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    csvreader = csv.reader(ifh)
    for row in csvreader:
      # 0: TCRD DB ID in version
      # 1: Name
      # 2: Description
      # 3: UniProt
      # 4: Symbol
      # 5: Gene ID
      # 6: TDL
      # 7: Family
      ct += 1
      geneid = None
      if row[5] != '\\N':
        geneid = row[5]
      rv = dba.ins_idg_evol( {'tcrd_ver': ver, 'tcrd_dbid': row[0], 'name': row[1], 'description': row[2], 'uniprot': row[3], 'sym': row[4], 'geneid': geneid, 'tdl': row[6], 'fam': row[7]} )
      if not rv:
        dba_err_ct += 1
        continue
      ins_ct += 1
      pbar.update(ct)
  pbar.finish()
  print "{} lines processed.".format(ct)
  print "  Inserted {} new idg_evol rows".format(ins_ct)
  if dba_err_ct > 0:
    print "WARNNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)
  
  return True


if __name__ == '__main__':
  print "\n%s (v%s) [%s]:\n" % (PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  debug = int(args['--debug'])
  if debug:
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
  
  for ver,fn in INPUTFILES:
    fn = DATA_DIR + fn
    load(args, dba, logfile, logger, ver, fn)

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'IDG Eligible Lists', 'source': 'CSV files exported by Steve Mathias at UNM from TCRD versions 1-6.', 'app': PROGRAM, 'app_version': __version__,} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'idg_evol'})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)
  
  print "\n%s: Done.\n" % PROGRAM
