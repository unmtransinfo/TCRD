#!/usr/bin/env python
# Time-stamp: <2018-05-10 10:15:18 smathias>
"""Use JensenLab tagger on NIHExporter project info and save results to pickle files.

Usage:
    grant_tagger.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>]
    grant_tagger.py -h | --help

Options:
  -h --dbhost DBHOST   : MySQL database host name [default: localhost]
  -n --dbname DBNAME   : MySQL database name [default: tcrdev]
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

import os,sys,time,re
from docopt import docopt
from TCRD import DBAdaptor
from collections import defaultdict
# tagger comes from here: https://bitbucket.org/larsjuhljensen/tagger
sys.path.append('/home/app/tagger')
from tagger import Tagger
import cPickle as pickle
import copy
import logging
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = 'tcrd5logs/'
LOGFILE = LOGDIR + '%s.log'%PROGRAM
LOGLEVEL = 20

REPORTER_DATA_DIR = '../data/NIHExporter/'
PROJECTS_P = '../data/NIHExporter/ProjectInfo2000-2015.p'
TAGGING_RESULTS_DIR = '../data/NIHExporter/TCRDv4/'
# The following *_FILE vars point to the dictionary files for the tagger
# get dictionary here http://download.jensenlab.org/human_dictionary.tar.gz
ENTITIES_FILE = '/home/app/JensenLab/human_dictionary/human_entities.tsv'
NAMES_FILE = '/home/app/JensenLab/human_dictionary/human_names.tsv'
GLOBAL_FILE = '/home/app/JensenLab/human_dictionary/human_global_SLM.tsv'

def main(args):
  loglevel = int(args['--loglevel'])
  if args['--logfile']:
    logfile = args['--logfile']
  else:
    logfile = LOGFILE
  logger = logging.getLogger(__name__)
  logger.setLevel(LOGLEVEL)
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
    print "\nConnected to TCRD database {} (schema ver {}; data ver {})".format(args['--dbname'], dbi['schema_ver'], dbi['data_ver'])
  
  if not args['--quiet']:
    print "\nLoading project info from pickle file {}".format(PROJECTS_P)
    projects = pickle.load( open(PROJECTS_P, 'rb') )

  if not args['--quiet']:
    print "\nCreating Tagger..."
  tgr = Tagger()
  tgr.load_names(ENTITIES_FILE, NAMES_FILE)
  tgr.load_global(GLOBAL_FILE)

  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  for year in [str(yr) for yr in range(2000, 2018)]: # 2000-2017
    pct = len(projects[year])
    print "\nTagging {} projects from {}".format(pct, year)
    logger.info("Tagging {} projects from {}".format(pct, year))
    pbar = ProgressBar(widgets=pbar_widgets, maxval=pct).start()
    start_time = time.time()
    ct = 0
    ttag_ct = 0
    abstag_ct = 0
    skip_ct = 0
    ttagsnotfnd = set()
    ttag2targetid = {}
    appid2targets = defaultdict(set)
    target2appids = defaultdict(set)
    for appid in projects[year].keys():
      ct += 1
      logger.debug("  Processing appid {}".format(appid))
      ginfo = projects[year][appid]
      # if there's no $$, we're not interested
      if ginfo['TOTAL_COST']:
        gcost = int(ginfo['TOTAL_COST'])
      elif ginfo['TOTAL_COST_SUB_PROJECT']:
        gcost = int(ginfo['TOTAL_COST_SUB_PROJECT'])
      else:
        continue
      # also, if there's less than $10k we're not interested
      if gcost < 10000:
        skip_ct += 1
        continue
      #
      # tag titles
      #
      matches = tgr.get_matches(projects[year][appid]['PROJECT_TITLE'], appid, [9606])
      if matches:
        ttag_ct += 1
        # the same tag can match multiple times, so get a set of ENSPs
        ensps = set()
        for m in matches:
          ensps.add(m[2][0][1])
        ensps = list(ensps)
        for ensp in ensps:
          if ensp in ttag2targetid:
            tid = ttag2targetid[ensp]
          elif ensp in ttagsnotfnd:
            continue
          else:
            targets = dba.find_targets({'stringid': ensp}, idg = False)
            if not targets:
              targets = dba.find_targets_by_xref({'xtype': 'Ensembl', 'value': ensp},
                                                 idg = False)
            if not targets:
              ttagsnotfnd.add(ensp)
              continue
            tid = targets[0]['id']
            ttag2targetid[ensp] = tid # save this so we don't look up the targets again
          appid2targets[appid].add(tid)
          target2appids[tid].add(appid)
      #
      # tag abstracts
      #
      if 'ABSTRACT' in projects[year][appid]:
        matches = tgr.get_matches(projects[year][appid]['ABSTRACT'], appid, [9606])
        if matches:
          abstag_ct += 1
          # the same tag can match multiple times, so get a set of ENSPs
          ensps = set()
          for m in matches:
            ensps.add(m[2][0][1])
          ensps = list(ensps)
          for ensp in ensps:
            if ensp in ttag2targetid:
              tid = ttag2targetid[ensp]
            elif ensp in ttagsnotfnd:
              continue
            else:
              targets = dba.find_targets({'stringid': ensp}, idg = False)
              if not targets:
                targets = dba.find_targets_by_xref({'xtype': 'Ensembl', 'value': ensp},
                                                   idg = False)
              if not targets:
                ttagsnotfnd.add(ensp)
                continue
              tid = targets[0]['id']
              ttag2targetid[ensp] = tid # save this so we don't look up the targets again
            appid2targets[appid].add(tid)
            target2appids[tid].add(appid)
      pbar.update(ct)
    pbar.finish()

    del_ct = 0
    for appid,tidset in appid2targets.items():
      if len(tidset) > 10:
        del_ct += 1
        del(appid2targets[appid])
    
    logger.info("{} projects processed.".format(ct))
    logger.info("  Removed {} projects with > 10 targets" % del_ct)
    logger.info("  Skipped {} projects with funds less than $10k:".format(skip_ct))
    logger.info("  {} titles have tagging result(s)".format(ttag_ct))
    logger.info("  {} abstracts have tagging result(s)".format(abstag_ct))
    logger.info("{} total tags map to {}/{} distinct targets".format(len(ttag2targetid.keys()), len(set(ttag2targetid.values())), len(target2appids.keys())))
    logger.info("{} project applications map to target(s)".format(len(appid2targets.keys())))
    if ttagsnotfnd:
      logger.info("  No target found for {} tags".format(len(ttagsnotfnd)))
    pfile = "%s/AppID2Targets%s.p"%(TAGGING_RESULTS_DIR, year)
    pickle.dump(appid2targets, open(pfile, 'wb'))
    logger.info("Tagging results saved to pickle {} for {}".format(pfile, year))
    pfile = "%s/Target2AppIDs%s.p"%(TAGGING_RESULTS_DIR, year)
    pickle.dump(target2appids, open(pfile, 'wb'))
    logger.info("Tagging results saved to pickle {} for {}".format(pfile, year))
    print "{} projects processed. See logfile {} for details.".format(ct, LOGFILE)


if __name__ == '__main__':
  print "\n{} (v{}) [{}]:".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  start_time = time.time()
  main(args)
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))
