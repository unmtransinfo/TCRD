#!/usr/bin/env python
# Time-stamp: <2017-01-13 12:52:01 smathias>
"""
Calculate and load consensus expression values into TCRD.
Usage:
    load-ConsensusExpressions.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-ConsensusExpressions.py -? | --help

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
__copyright__ = "Copyright 2016-2017, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.0.0"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import logging
import csv
from collections import defaultdict
import operator
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
TISSUESTYPEDFILE = '../data/Tissues_Typed_v2.1.csv'

def calc_and_load():
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
  
  start_time = time.time()
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'Consensus Expression Values', 'source': 'IDG-KMC generated data by Steve Mathias at UNM.', 'app': PROGRAM, 'app_version': __version__, 'comments': 'Consensus of GTEx, HPM and HPA expression values are calculated by the loader app.'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'expression', 'where_clause': "etype = 'Consensus'"})
  if not rv:
    print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
    sys.exit(1)
  
  tmap = {} # tissue name to Tissue Type as per TIO
  line_ct = wcl(TISSUESTYPEDFILE)
  line_ct -= 1
  if not args['--quiet']:
    print '\nProcessiong %d tissue mapping lines from file: %s' % (line_ct, TISSUESTYPEDFILE)
  with open(TISSUESTYPEDFILE, 'rU') as csvfile:
    csvreader = csv.reader(csvfile)
    header = csvreader.next() # skip header line
    ct = 0
    for row in csvreader:
      ct += 1
      tissue = row[0].lower()
      tmap[tissue] = row[2]
  if not args['--quiet']:
    print '  Got %d tissue name mappings' % len(tmap.keys())

  tct = dba.get_target_count()
  if not args['--quiet']:
    print "\nCalculating/Loading Consensus expressions for %d TCRD targets" % tct
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=tct).start() 
  ct = 0
  exp_ct = 0
  dba_err_ct = 0
  for t in dba.get_targets(include_annotations=True):
    ct += 1
    p = t['components']['protein'][0]
    if 'expressions' in p:
      want = ['GTEx', 'HPA Protein', 'HPA RNA', 'HPM Gene', 'HPM Protein']
      aggexps = aggregate_exps(p['expressions'], tmap, want)
      for tissue, vals in aggexps.items():
        (cons, conf) = calculate_consensus(vals)
        rv = dba.ins_expression( {'protein_id': p['id'], 'etype': 'Consensus', 
                                  'tissue': tissue, 'qual_value': cons, 'confidence': conf} )
        if rv:
          exp_ct += 1
        else:
          dba_err_ct += 1
    pbar.update(ct)
  pbar.finish()
  if not args['--quiet']:
    print "Processed %d targets." % ct
    print "  Inserted %d new Consensus expression rows." % exp_ct
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)


def default_factory():
  return {0: 0, 1: 0, 2: 0, 3: 0}

def aggregate_exps(exps, tmap, want):
  exps = [e for e in exps if e['etype'] in want]
  aggexps = defaultdict(default_factory)
  fvalmap = {'Not Detected': 0, 'Low': 1, 'Medium': 2, 'High': 3}
  for e in exps:
    tissue = e['tissue'].lower()
    k1 = tmap[tissue]
    if e['qual_value'] in fvalmap:
      k2 = fvalmap[e['qual_value']]
    else:
      continue
    aggexps[k1][k2] += 1
  return aggexps

def calculate_consensus(vals):
  rvalmap = {0: 'Not Detected', 1: 'Low', 2: 'Medium', 3: 'High'}
  # sorted_vals will be a list of tuples sorted by the second element in each tuple (ie. the count)
  sorted_vals = sorted(vals.items(), key=operator.itemgetter(1), reverse=True)
  # consensus value is simply the mode:
  cons = rvalmap[sorted_vals[0][0]]
  # calculate confidence score
  if cons == 'High':
    if vals[3] > 4:
      if vals[2]+vals[1]+vals[0] == 0:
        conf = 5
      elif vals[2] == 1 and vals[1]+vals[0] == 0:
        conf = 4
      elif vals[2] == 2 and vals[1]+vals[0] == 0:
        conf = 3
      elif vals[2] == 3 and vals[1]+vals[0] == 0:
        conf = 2
      else:
        conf = 1
    elif vals[3] == 4:
      if vals[2]+vals[1]+vals[0] == 0:
        conf = 4
      elif vals[2] == 1 and vals[1]+vals[0] == 0:
        conf = 3
      elif vals[2] == 2 and vals[1]+vals[0] == 0:
        conf = 2
      else:
        conf = 1
    elif vals[3] == 3:
      if vals[2]+vals[1]+vals[0] == 0:
        conf = 3
      elif vals[2] == 1 and vals[1]+vals[0] == 0:
        conf = 2
      else:
        conf = 1
    elif vals[3] == 2:
      if vals[2]+vals[1]+vals[0] == 0:
        conf = 2
      else:
        conf = 1
    else:
      conf = 0
  elif cons == 'Medium':
    if vals[2]+vals[3] > 4:
      if vals[1]+vals[0] == 0:
        conf = 5
      elif vals[1] == 1 and vals[0] == 0:
        conf = 4
      elif vals[1] == 2 and vals[0] == 0:
        conf = 3
      elif vals[1] == 3 and vals[0] == 0:
        conf = 2
      else:
        conf = 1
    elif vals[2]+vals[3] == 4:
      if vals[1]+vals[0] == 0:
        conf = 4
      elif vals[1] == 1 and vals[0] == 0:
        conf = 3
      elif vals[1] == 2 and vals[0] == 0:
        conf = 2
      else:
        conf = 1
    elif vals[2]+vals[3] == 3:
      if vals[1]+vals[0] == 0:
        conf = 3
      elif vals[1] == 1 and vals[0] == 0:
        conf = 2
      else:
        conf = 1
    elif vals[2]+vals[3] == 2:
      if vals[1]+vals[0] == 0:
        conf = 2
      else:
        conf = 1
    else:
      conf = 0
  elif cons == 'Low':
    if vals[1]+vals[2]+vals[3] > 4:
      if vals[0] == 0:
        conf = 5
      elif vals[0] == 1 and vals[3] == 0:
        conf = 4
      elif vals[0] == 2 and vals[3] == 0:
        conf = 3
      elif vals[0] == 3 and vals[3] == 0:
        conf = 2
      else:
        conf = 1
    elif vals[1]+vals[2]+vals[3] == 4:
      if vals[0] == 0:
        conf = 4
      elif vals[0] == 1 and vals[3] == 0:
        conf = 3
      elif vals[0] == 2 and vals[3] == 0:
        conf = 2
      else:
        conf = 1
    elif vals[1]+vals[2]+vals[3] == 3:
      if vals[0] == 0:
        conf = 3
      elif vals[0] == 1 and vals[3] == 0:
        conf = 2
      else:
        conf = 1
    else:
      conf = 0
  elif cons == 'Not Detected':
    if vals[0] > 4:
      if vals[1]+vals[2]+vals[3] == 0:
        conf = 5
      elif vals[1] == 1 and vals[2]+vals[3] == 0:
        conf = 4
      elif vals[1] == 2 and vals[2]+vals[3] == 0:
        conf = 3
      elif vals[1] == 3 and vals[2]+vals[3] == 0:
        conf = 2
      else:
        conf = 1
    elif vals[0] == 4:
      if vals[1]+vals[2]+vals[3] == 0:
        conf = 4
      elif vals[1] == 1 and vals[2]+vals[3] == 0:
        conf = 3
      elif vals[1] == 2 and vals[2]+vals[3] == 0:
        conf = 2
      else:
        conf = 1
    elif vals[0] == 3:
      if vals[1]+vals[2]+vals[3] == 0:
        conf = 3
      elif vals[1] == 1 and vals[2]+vals[3] == 0:
        conf = 2
      else:
        conf = 1
    elif vals[0] == 2:
      if vals[1]+vals[2]+vals[3] == 0:
        conf = 2
      else:
        conf = 1
    else:
      conf = 0
  return(cons, conf)


def wcl(fname):
  with open(fname) as f:
    for i, l in enumerate(f):
      pass
  return i + 1

def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])

if __name__ == '__main__':
  print "\n%s (v%s) [%s]:" % (PROGRAM, __version__, time.strftime("%c"))
  start_time = time.time()
  calc_and_load()
  elapsed = time.time() - start_time
  print "\n%s: Done. Elapsed time: %s\n" % (PROGRAM, secs2str(elapsed))
