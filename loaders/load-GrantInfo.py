#!/usr/bin/env python
# Time-stamp: <2015-12-11 12:06:50 smathias
"""Load grant_info data into TCRD from pickle files produced from tagging NIHExporter data.

Usage:
    load-GrantInfo.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-GrantInfo.py -h | --help

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
__copyright__ = "Copyright 2015-2018, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.1.0"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import cPickle as pickle
import logging
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = 'tcrd5logs/'
LOGFILE = LOGDIR + '%s.log'%PROGRAM
PROJECTS_P = '../data/NIHExporter/ProjectInfo2000-2017.p'
TAGGING_RESULTS_DIR = '../data/NIHExporter/TCRDv5/'

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

  if not args['--quiet']:
    print "\nLoading project info from pickle file %s" % PROJECTS_P
    projects = pickle.load( open(PROJECTS_P, 'rb') )

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'NIH Grant Textmining Info', 'source': 'IDG-KMC generated data by Steve Mathias at UNM.', 'app': PROGRAM, 'app_version': __version__, 'comments': "Grant info is generated from textmining results of running Lars Jensen's tagger software on project info downloaded from NIHExporter."} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'grant'},
            {'dataset_id': dataset_id, 'table_name': 'tdl_info', 'where_clause': 'itype is "NIHRePORTER 2000-2017 R01 Count"'} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)
  
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]

  if not args['--quiet']:
    print "\nLoading tagging results in %s" % TAGGING_RESULTS_DIR
  r01cts = {}
  for year in [str(yr) for yr in range(2000, 2018)]: # 2000-2017
    pfile = "%s/Target2AppIDs%s.p" % (TAGGING_RESULTS_DIR, year)
    target2appids = pickle.load( open(pfile, 'rb') )
    tct = len(target2appids.keys())
    if not args['--quiet']:
      print "\nProcessing tagging results for {}: {} targets".format(year, tct)
    pfile = "%s/AppID2Targets%s.p" % (TAGGING_RESULTS_DIR, year)
    appid2targets = pickle.load( open(pfile, 'rb') )
    pbar = ProgressBar(widgets=pbar_widgets, maxval=tct).start()
    ct = 0
    t2g_ct = 0
    dba_err_ct = 0
    for tid,appids in target2appids.items():
      ct += 1
      pbar.update(ct)
      for appid in appids:
        if appid not in appid2targets:
          # need to do this check because of projects removed with > 10 targets tagged
          continue
        app_target_ct = len(appid2targets[appid]) # number of targets tagged in this grant
        ginfo = projects[year][appid]
        # gcost is total grant dollars
        if ginfo['TOTAL_COST']:
          gcost = float(ginfo['TOTAL_COST'])
        elif ginfo['TOTAL_COST_SUB_PROJECT']:
          gcost = float(ginfo['TOTAL_COST_SUB_PROJECT'])
        else:
          continue
        # grant_target_cost is dollars per target for this grant
        grant_target_cost = gcost/app_target_ct
        rv = dba.ins_grant( {'target_id': tid, 'appid': appid, 'year': year,
                             'full_project_num': ginfo['FULL_PROJECT_NUM'],
                             'activity': ginfo['ACTIVITY'],
                             'funding_ics': ginfo['FUNDING_ICs'],
                             'cost': "%.2f"%grant_target_cost } )
        if not rv:
          dba_err_ct += 1
          continue
        t2g_ct += 1
        # track R01s
        if ginfo['ACTIVITY'] == 'R01':
          if tid in r01cts:
            r01cts[tid] += 1
          else:
            r01cts[tid] = 1
    pbar.finish()
    print "Processed {} target tagging records.".format(ct)
    print "  Inserted {} new target2grant rows".format(t2g_ct)

  # Now load 'NIHRePORTER 2000-2017 R01 Count' tdl_infos
  print "\nLoading 'NIHRePORTER 2010-2017 R01 Count' tdl_infos for {} targets".format(len(r01cts))
  ti_ct = 0
  for tid in r01cts:
    rv = dba.ins_tdl_info( {'target_id': tid, 'itype': 'NIHRePORTER 2000-2017 R01 Count',
                            'integer_value': r01cts[tid]} )
    if not rv:
      dba_err_ct += 1
      continue
    ti_ct += 1
  print "  Inserted {} new tdl_info rows".format(ti_ct)
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

