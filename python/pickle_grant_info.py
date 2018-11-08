#!/usr/bin/env python
# Time-stamp: <2018-05-10 10:11:26 smathias>
"""Collect grant info from NIHExporter files and save in pickle file.

Usage:
    pickle_grant_info.py [--debug=<int> | --quiet]
    pickle_grant_info.py -h | --help

Options:
  -q --quiet           : set output verbosity to minimal level
  -d --debug DEBUGL    : set debugging output level (0-3) [default: 0]
  -? --help            : print this message and exit 
"""
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2016-2018, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "1.1.0"

import os,sys,time,re
from docopt import docopt
import csv
import cPickle as pickle
import logging
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = 'tcrd5logs/'
LOGFILE = LOGDIR + '%s.log'%PROGRAM
LOGLEVEL = 20
REPORTER_DATA_DIR = '../data/NIHExporter/'
PROJECTS_P = '../data/NIHExporter/ProjectInfo2000-2017.p'

def main(args):
  loglevel = int(args['--loglevel'])
  if args['--logfile']:
    logfile = args['--logfile']
  else:
    logfile = LOGFILE
  logger = logging.getLogger(__name__)
  logger.setLevel(LOGLEVEL)
  if notargs['--debug']:
    logger.propagate = False # turns off console logging
  fh = logging.FileHandler(LOGFILE)
  fmtr = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
  fh.setFormatter(fmtr)
  logger.addHandler(fh)
  
  projects = {}
  for year in [str(yr) for yr in range(2000, 2018)]: # 2000-2017
    projs = {}
    print "Gathering project info for {}".format(year)
    logger.info("Gathering project info for {}".format(year))
    # projects
    projects_file = REPORTER_DATA_DIR + "RePORTER_PRJ_C_FY%s.csv"%year
    assert os.path.exists(projects_file), "No projects file: {}!".format(projects_file)
    line_ct = wcl(projects_file)
    logger.info("Processing {} input lines in projects file {}".format(line_ct, projects_file))
    with open(projects_file, 'rU') as csvfile:
      csvreader = csv.reader(csvfile)
      ct = 0
      header = csvreader.next() # skip header line
      ks = header[1:]
      for row in csvreader:
        ct += 1
        appid = int(row[0])
        d = {}
        for (i,k) in enumerate(ks):
          idx = i + 1 # add one because we are skipping first column (the appid)
          d[k] = row[idx]
        projs[appid] = d
    # abstracts
    abstracts_file = REPORTER_DATA_DIR + "RePORTER_PRJABS_C_FY%s.csv"%year
    assert os.path.exists(abstracts_file), "No abstracts file: %s!"%abstracts_file
    line_ct = wcl(abstracts_file)
    logger.info("Processing {} input lines in abstracts file {}".format(line_ct, abstracts_file))
    with open(abstracts_file, 'rU') as csvfile:
      csvreader = csv.reader(csvfile)
      ct = 0
      header = csvreader.next() # skip header line
      for row in csvreader:
        ct += 1
        appid = int(row[0])
        if appid in projs:
          abstract_txt = re.sub(r'^\s*DESCRIPTION \(provided by applicant\):\s*', '', row[1])
          absstract_txt = re.sub(r'^\s*ABSTRACT\s*', '', abstract_txt)
          absstract_txt = re.sub(r'^\s*PROJECT SUMMARY\/ABSTRACT:(\s*RATIONALE:\s*)?', '', abstract_txt)
          projs[appid]['ABSTRACT'] = abstract_txt
    projects[year] = projs
    logger.info("Info collected for {} projects.\n".format(len(projs.keys())))
  
  print "\nDumping info on projects to pickle {}".format(PROJECTS_P)
  pickle.dump(projects, open(PROJECTS_P, 'wb'))


if __name__ == '__main__':
  print "\n{} (v{}) [{}]:".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  start_time = time.time()
  main(args)
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))
