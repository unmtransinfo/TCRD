#!/usr/bin/env python
# Time-stamp: <2020-11-12 09:55:41 smathias>
"""Calculate and load target TDL assignments.

Usage:
    load-TDLs.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-TDLs.py | --help

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
__copyright__ = "Copyright 2015-2020, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "3.0.0"

import os,sys,time,re
from docopt import docopt
from TCRD7 import DBAdaptor
import logging
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd6logs"
#LOGDIR = "./tcrd7logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)

def load(args, dba, logfile, logger):
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  tids = dba.get_target_ids()
  if not args['--quiet']:
    print "\nProcessing {} TCRD targets".format(len(tids))
  pbar = ProgressBar(widgets=pbar_widgets, maxval=len(tids)).start() 
  ct = 0
  tdl_cts = {'Tclin': 0, 'Tchem': 0, 'Tbio': 0, 'Tdark': 0}
  bump_ct = 0
  dba_err_ct = 0
  upd_ct = 0
  for tid in tids:
    target = dba.get_target4tdlcalc(tid)
    ct += 1
    pbar.update(ct)
    (tdl, bump_flag) = compute_tdl(target)
    tdl_cts[tdl] += 1
    if bump_flag:
      bump_ct += 1
    rv = dba.upd_target(target['id'], 'tdl', tdl)
    if rv:
      upd_ct += 1
    else:
      dba_err_ct += 1
  pbar.finish()
  print "{} TCRD targets processed.".format(ct)
  print "Set TDL values for {} targets:".format(upd_ct)
  print "  {} targets are Tclin".format(tdl_cts['Tclin'])
  print "  {} targets are Tchem".format(tdl_cts['Tchem'])
  print "  {} targets are Tbio - {} bumped from Tdark".format(tdl_cts['Tbio'], bump_ct)
  print "  {} targets are Tdark".format(tdl_cts['Tdark'])
  if dba_err_ct > 0:
    print "WARNING: {} database errors occured. See logfile {} for details.".format(dba_err_ct, logfile)

def compute_tdl(target):
  '''
  Returns (tdl, bump_flag)
  '''
  bump_flag = False
  if 'drug_activities' in target:
    if len([a for a in target['drug_activities'] if a['has_moa'] == 1]) > 0:
      # MoA drug activities qualify a target as Tclin
      tdl = 'Tclin'
    else:
      # Non-MoA drug activities qualify a target as Tchem
      tdl = 'Tchem'
  elif 'cmpd_activities' in target:
    # cmpd activities qualify a target as Tchem
    tdl = 'Tchem'
  else:
    # Collect info needed to decide between Tbio and Tdark
    p = target['components']['protein'][0]
    ptdlis = p['tdl_infos']
    # JensenLab PubMed Score
    pms = float(ptdlis['JensenLab PubMed Score']['value'])
    # GeneRIF Count
    rif_ct = 0
    if 'generifs' in p:
      rif_ct = len(p['generifs'])
    # Ab Count
    ab_ct = int(ptdlis['Ab Count']['value']) 
    # Experimental MF/BP Leaf Term GOA
    efl_goa = False
    if 'Experimental MF/BP Leaf Term GOA' in ptdlis:
      efl_goa = True
    # # OMIM Phenotype
    # omim = False
    # if 'phenotypes' in p and len([d for d in p['phenotypes'] if d['ptype'] == 'OMIM']) > 0:
    #   omim = True
    # Decide between Tbio and Tdark
    dark_pts = 0    
    if pms < 5:     # PubMed Score < 5
      dark_pts += 1
    if rif_ct <= 3: # GeneRIF Count <= 3
      dark_pts += 1
    if ab_ct <= 50: # Ab Count <= 50
      dark_pts += 1
    if dark_pts >= 2:
      # if at least 2 of the above, target is Tdark...
      tdl = 'Tdark'
      if efl_goa:
        # ...unless target has Experimental MF/BP Leaf Term GOA, then bump to Tbio
        tdl = 'Tbio'
        bump_flag = True
    else:
      tdl = 'Tbio'
  return (tdl, bump_flag)


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

  start_time = time.time()
  load(args, dba, logfile, logger)
  elapsed = time.time() - start_time

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'TDLs', 'source': 'IDG-KMC generated data by Steve Mathias at UNM.', 'app': PROGRAM, 'app_version': __version__, 'comments': 'TDLs are generated by the loading app from data in TCRD.'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile {} for details.".format(logfile)
    sys.exit(1)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'target', 'column_name': 'tdl'})
  if not rv:
    print "WARNING: Error inserting provenance. See logfile {} for details.".format(logfile)
    sys.exit(1)
  
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))
