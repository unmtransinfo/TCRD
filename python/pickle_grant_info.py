#!/usr/bin/env python
# Time-stamp: <2016-12-14 15:40:19 smathias>
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
__copyright__ = "Copyright 2016, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "1.0.0"

import os,sys,time,re
from docopt import docopt
import csv
import cPickle as pickle
import logging

PROGRAM = os.path.basename(sys.argv[0])
LOGFILE = '../data/NIHExporter/%s.log' % PROGRAM
LOGLEVEL = 20
REPORTER_DATA_DIR = '../data/NIHExporter/'
PROJECTS_P = '../data/NIHExporter/ProjectInfo2000-2015.p'

def main():
  args = docopt(__doc__, version=__version__)
  quiet = args['--quiet']
  debug = int(args['--debug'])
  if debug:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)

  if not args['--quiet']:
    print "\n%s (v%s) [%s]:\n" % (PROGRAM, __version__, time.strftime("%c"))
    
  if os.path.exists(PROJECTS_P):
    print "\nPickle file %s exists. Exiting." % PROJECTS_P
    sys.exit(1)

  logger = logging.getLogger(__name__)
  logger.setLevel(LOGLEVEL)
  if not debug:
    logger.propagate = False # turns off console logging when debug is 0
  fh = logging.FileHandler(LOGFILE)
  fmtr = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
  fh.setFormatter(fmtr)
  logger.addHandler(fh)
  
  projects = {}
  for year in [str(yr) for yr in range(2000, 2016)]: # 2000-2015
    start_time = time.time()
    projs = {}
    print "Gathering project info for %s" % year
    logger.info("Gathering project info for %s" % year)
    # projects
    projects_file = REPORTER_DATA_DIR + "RePORTER_PRJ_C_FY%s.csv"%year
    assert os.path.exists(projects_file), "No projects file: %s!"%projects_file
    line_ct = wcl(projects_file)
    logger.info("Processing %d input lines in projects file %s" % (line_ct, projects_file))
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
    logger.info("Processing %d input lines in abstracts file %s" % (line_ct, abstracts_file))
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
    elapsed = time.time() - start_time
    logger.info("Info collected for %d projects. Elapsed time: %s\n" % (len(projs.keys()), elapsed))
  
  print "\nDumping info on projects to pickle %s" % PROJECTS_P
  pickle.dump(projects, open(PROJECTS_P, 'wb'))

  print "\n%s: Done.\n" % PROGRAM


def wcl(fname):
  with open(fname) as f:
    for i, l in enumerate(f):
      pass
  return i + 1

def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])

if __name__ == '__main__':
  main()
