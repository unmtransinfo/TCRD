#!/usr/bin/env python
# Time-stamp: <2015-12-11 12:06:50 smathias
"""Load grant_info data into TCRD from pickle files produced from tagging NIHExporter data.

Usage:
    load-GrantInfo.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
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
  -d --debug DEBUGL    : set debugging output level (0-3) [default: 0]
  -? --help            : print this message and exit 
"""
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2015-2016, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.0.0"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import cPickle as pickle
import logging
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
LOGFILE = "%s.log" % PROGRAM
PROJECTS_P = '../data/NIHExporter/ProjectInfo2000-2015.p'
TAGGING_RESULTS_DIR = '../data/NIHExporter/TCRDv4/'

def main():
  args = docopt(__doc__, version=__version__)
  loglevel = int(args['--loglevel'])
  if args['--logfile']:
    logfile = args['--logfile']
  else:
    logfile = "%s.log" % PROGRAM
  debug = int(args['--debug'])
  quiet = args['--quiet']
  if debug:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
    
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
  if not quiet:
    print "\n%s (v%s) [%s]:" % (PROGRAM, __version__, time.strftime("%c"))
    print "\nConnected to TCRD database %s (schema ver %s; data ver %s)" % (args['--dbname'], dbi['schema_ver'], dbi['data_ver'])

  if not quiet:
    print "\nLoading project info from pickle file %s" % PROJECTS_P
    projects = pickle.load( open(PROJECTS_P, 'rb') )

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'NIH Grant Info', 'source': 'IDG-KMC generated data by Steve Mathias at UNM.', 'app': PROGRAM, 'app_version': __version__, 'comments': "Grant info is generated from textmining results of running Lars Jensen's tagger software on project info downloaded from NIHExporter."} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'grant'},
            {'dataset_id': dataset_id, 'table_name': 'tdl_info', 'where_clause': 'itype is "NIHRePORTER 2000-2015 R01 Count"'} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    if not rv:
      print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
      sys.exit(1)
  
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]

  if not quiet:
    print "\nLoading tagging results in %s" % TAGGING_RESULTS_DIR
  r01cts = {}
  for year in [str(yr) for yr in range(2000, 2016)]: # 2000-2015
    start_time = time.time()
    pfile = "%s/Target2AppIDs%s.p" % (TAGGING_RESULTS_DIR, year)
    target2appids = pickle.load( open(pfile, 'rb') )
    tct = len(target2appids.keys())
    print "\nProcessing tagging results for %s: %d targets" % (year, tct)
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
    elapsed = time.time() - start_time
    print "Processed %d target tagging records. Elapsed time: %s" % (ct, secs2str(elapsed))
    print "  Inserted %d new target2grant rows" % t2g_ct

  # Now save 'NIHRePORTER 2000-2015 R01 Count' tdl_infos
  print "\nLoading 'NIHRePORTER 2010-2015 R01 Count' tdl_infos for %d targets" % len(r01cts.keys())
  ti_ct = 0
  for tid in r01cts:
    rv = dba.ins_tdl_info( {'target_id': tid, 'itype': 'NIHRePORTER 2000-2015 R01 Count',
                            'integer_value': r01cts[tid]} )
    if not rv:
      dba_err_ct += 1
      continue
    ti_ct += 1
  print "  Inserted %d new tdl_info rows" % ti_ct
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)
  
  print "\n%s: Done.\n" % PROGRAM


def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])

if __name__ == '__main__':
  main()
