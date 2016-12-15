#!/usr/bin/env python
# Time-stamp: <2016-12-12 11:34:24 smathias>
"""Load CMap Landmark Gene ID xrefs into TCRD from CSV file.

Usage:
    load-L1000XRefs.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-L1000XRefs.py -? | --help

Options:
  -h --dbhost DBHOST   : MySQL database host name [default: localhost]
  -n --dbname DBNAME   : MySQL database name [default: tcrd]
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
'''
load-L1000XRefs.py - 
'''
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2015-2016, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.0.0"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import logging
import csv
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
DBHOST = 'localhost'
DBPORT = 3306
DBNAME = 'tcrdev'
LOGFILE = './%s.log'%PROGRAM
L1000_FILE = '../data/CMap_LandmarkGenes_n978.csv'

def main():
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

  # DBAdaptor uses same logger as main()
  dba_params = {'dbhost': args['--dbhost'], 'dbname': args['--dbname'], 'logger_name': __name__}
  dba = DBAdaptor(dba_params)
  dbi = dba.get_dbinfo()
  logger.info("Connected to TCRD database %s (schema ver %s; data ver %s)", args['--dbname'], dbi['schema_ver'], dbi['data_ver'])
  if not args['--quiet']:
    print "\n%s (v%s) [%s]:" % (PROGRAM, __version__, time.strftime("%c"))
    print "\nConnected to TCRD database %s (schema ver %s; data ver %s)" % (args['--dbname'], dbi['schema_ver'], dbi['data_ver'])

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'LINCS L1000 XRefs', 'source': 'File %s'%os.path.basename(L1000_FILE), 'app': PROGRAM, 'app_version': __version__, 'url': 'http://support.lincscloud.org/hc/en-us/articles/202092616-The-Landmark-Genes'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  
  start_time = time.time()
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  line_ct = wcl(L1000_FILE)
  if not args['--quiet']:
    print "\nProcessing %d rows in file %s" % (line_ct, L1000_FILE)
  with open(L1000_FILE, 'rU') as csvfile:
    csvreader = csv.reader(csvfile)
    ct = 0
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start()
    ct = 0
    tmark = {}
    xref_ct = 0
    notfnd = []
    dba_err_ct = 0
    for row in csvreader:
      ct += 1
      pbar.update(ct)
      l1000 = row[0]
      sym = row[1]
      geneid = row[2]
      targets = dba.find_targets({'sym': sym})
      if not targets:
        targets = dba.find_targets({'geneid': geneid})
        if not targets:
          notfnd.append("%s|%s"%(sym,geneid))
          continue
      target = targets[0]
      tmark[target['id']] = True
      pid = target['components']['protein'][0]['id']
      rv = dba.ins_xref({'protein_id': pid, 'xtype': 'L1000 ID', 'dataset_id': dataset_id, 'value': l1000})
      if rv:
        xref_ct += 1
      else:
        dba_err_ct += 1
  pbar.finish()

  elapsed = time.time() - start_time
  if not args['--quiet']:
    print "\n%d rows processed. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "%d targets annotated with L1000 xref(s)" % len(tmark.keys())
  print "  Inserted %d new L1000 ID xref rows" % xref_ct
  if len(notfnd) > 0:
    print "WARNNING: %d symbols NOT FOUND in TCRD:" % len(notfnd)
    for sg in notfnd:
      print sg
  if dba_err_ct > 0:
    print "WARNNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)
  if not args['--quiet']:
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
