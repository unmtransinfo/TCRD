#!/usr/bin/env python
# Time-stamp: <2017-01-12 11:19:10 smathias>
"""Load Is Transcription Factor tdl_infos into TCRD from AnimalTFDB TSV file.

Usage:
    load-AnimalTFDB.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>] [--pastid=<int>]
    load-AnimalTFDB.py -h | --help

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
  -p --pastid PASTID   : TCRD target id to start at (for restarting frozen run)
  -q --quiet           : set output verbosity to minimal level
  -d --debug DEBUGL    : set debugging output level (0-3) [default: 0]
  -? --help            : print this message and exit 
"""
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2014-2017, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.0.0"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import csv
import logging
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
# http://www.bioguo.org/AnimalTFDB/BrowseAllTF.php?spe=Homo_sapiens
INFILE = '../data/AnimalTFDB/HsTFList.txt'

def load():
  args = docopt(__doc__, version=__version__)
  debug = int(args['--debug'])
  if debug:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  
  loglevel = int(args['--loglevel'])
  if args['--logfile']:
    logfile = args['--logfile']
  else:
    logfile = "%s.log" % PROGRAM
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
  if not args['--quiet']:
    print "\nConnected to TCRD database %s (schema ver %s; data ver %s)" % (args['--dbname'], dbi['schema_ver'], dbi['data_ver'])
  
  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'AnimalTFDB', 'source': 'http://www.bioguo.org/AnimalTFDB/BrowseAllTF.php?spe=Homo_sapiens', 'app': PROGRAM, 'app_version': __version__, 'url': 'http://www.bioguo.org/AnimalTFDB/'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'tdl_infp', 'where_clause': "itype = 'Is Transcription Factor'"})
  if not rv:
    print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
    sys.exit(1)

  start_time = time.time()
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  TDLs = {'Tdark': 0, 'Tbio': 0, 'Tchem': 0, 'Tclin': 0}
  
  line_ct = wcl(INFILE)
  if not args['--quiet']:
    print "\nProcessing %d lines in input file %s\n" % (line_ct, INFILE)
  with open(INFILE, 'rU') as tsv:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    ti_ct = 0
    notfnd = []
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
      sym = row[3]
      targets = dba.find_targets({'sym': sym})
      if not targets:
        gid = row[2]
        targets = dba.find_targets({'geneid': gid})
      if not targets:
        ensg = row[1]
        targets = dba.find_targets_by_xref({'xtype': 'Ensembl', 'value': ensg})
      if not targets:
        notfnd.append(row)
        continue
      t = targets[0]
      TDLs[t['tdl']] += 1
      pid = t['components']['protein'][0]['id']
      rv = dba.ins_tdl_info({'protein_id': pid, 'itype': 'Is Transcription Factor', 
                             'boolean_value': 1} )
      if rv:
        ti_ct += 1
      else:
        dba_err_ct += 1
      pbar.update(ct)
  pbar.finish()

  elapsed = time.time() - start_time
  print "\n%d input lines processed. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "  Inserted %d new Is Transcription Factor tdl_infos" % ti_ct
  if notfnd:
    print "No target found for %d rows:" % len(notfnd)
    #for row in notfnd:
    #  print row
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)
  for tdl in ['Tclin', 'Tchem', 'Tbio', 'Tdark']:
    print "%s: %d" % (tdl, TDLs[tdl])


def wcl(fname):
  with open(fname) as f:
    for i, l in enumerate(f):
      pass
  return i + 1

def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])

if __name__ == '__main__':
  print "\n%s (v%s) [%s]:\n" % (PROGRAM, __version__, time.strftime("%c"))
  load()
  print "\n%s: Done.\n" % PROGRAM
