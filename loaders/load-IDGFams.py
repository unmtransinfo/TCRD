#!/usr/bin/env python
# Time-stamp: <2017-01-13 12:18:17 smathias>
"""Load IDG Family designations into TCRD from pickle file.

Usage:
    load-IDGFams.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] --infile=<file>
    load-IDGFams.py -h | --help

Options:
  -i --infile INFILE   : Input pickle file containing IDG Family data
  -h --dbhost DBHOST   : MySQL database host name [default: localhost]
  -n --dbname DBNAME   : MySQL database name [default: tcrdev]
  -q --quiet           : set output verbosity to minimal level
  -d --debug DEBUGL    : set debugging output level (0-3) [default: 0]
  -? --help            : print this message and exit 
"""
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2014-2016, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.0.0"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import cPickle as pickle
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
DBNAME = 'tcrdev'

def main():
  args = docopt(__doc__, version=__version__)
  debug = int(args['--debug'])
  if debug > 1:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  
  dba_params = {'dbhost': args['--dbhost'], 'dbname': args['--dbname'], 'logger_name': __name__}
  dba = DBAdaptor(dba_params)
  dbi = dba.get_dbinfo()
  if not args['--quiet']:
    print "\n%s (v%s) [%s]:" % (PROGRAM, __version__, time.strftime("%c"))
    print "\nConnected to TCRD database %s (schema ver %s; data ver %s)" % (args['--dbname'], dbi['schema_ver'], dbi['data_ver'])

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'IDG Families', 'source': 'IDG-KMC generated data by Steve Mathias at UNM and the Schurer group at UMiami.', 'app': PROGRAM, 'app_version': __version__, 'comments': 'IDG family designations are based on manually curated lists.'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'target', 'column_name': 'idgfam'})
  if not rv:
    print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
    sys.exit(1)
  
  start_time = time.time()
  idgs = pickle.load( open(args['--infile'], 'rb') )
  uct = sum([len(idgs[k]) for k in idgs.keys()])
  if not args['--quiet']:
    print "\nLoading %d IDF Family designations from pickle file %s" % (uct, args['--infile'])
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=uct).start()
  ct = 0
  idg_ct = 0
  notfnd = []
  mulfnd = []
  for idgfam,l in idgs.items():
    for d in l:
      ct += 1
      targets = []
      if 'sym' in d and d['sym'] != None:
        if debug:
          print "[DEBUG] Searching for target by sym %s" % d['sym']
        targets = dba.find_targets({'sym': d['sym']})
      if not targets or len(targets) > 1:
        if debug:
          print "[DEBUG] Searching for target by uniprot %s" % d['uniprot']
        targets = dba.find_targets({'uniprot': d['uniprot']})
      if not targets:
        if 'geneid' in d and d['geneid'] != None:
          if debug:
            print "[DEBUG] Searching for target by geneid %d" % d['geneid']
          targets = dba.find_targets({'geneid': d['geneid']})
      if targets:
        if debug:
          print "[DEBUG] Found %d targets" % len(targets)
        if len(targets) > 1:
          if debug:
            print "[DEBUG] WARNING: Multiple targets found for", d
          mulfnd.append(d)
        t = targets[0]
        rv = dba.upd_target(t['id'], 'idgfam', idgfam)
        if not rv:
          print "ERROR updating target %d to %s" % (t['id'], idgfam)
        else:
          idg_ct += 1
      else:
        print "ERROR: %s family target not found with sym %s" % (idgfam, d['sym'])
        notfnd.append(d)
      pbar.update(ct)
  pbar.finish()

  elapsed = time.time() - start_time
  print "%d IDG family designations loaded into TCRD. Elapsed time: %s" % (idg_ct, secs2str(elapsed))
  if notfnd:
    print "[WARNING] No target found for %d IDG records:" % len(notfnd)
    for d in notfnd:
      print d
  if mulfnd:
    print "[WARNING] Multiple targets found for IDG %d records:" % len(mulfnd)
    for d in mulfnd:
      print d
  print "\n%s: Done.\n" % PROGRAM
  

def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])

if __name__ == '__main__':
    main()
