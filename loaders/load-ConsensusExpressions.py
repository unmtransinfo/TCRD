#!/usr/bin/env python
# Time-stamp: <2018-04-09 12:35:41 smathias>
"""
Calculate and load consensus expression values into TCRD.
Usage:
    load-ConsensusExpressions.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
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
  -d --debug           : turn on debugging output
  -? --help            : print this message and exit 
"""
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2016-2018, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.1.0"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import logging
import csv
from collections import defaultdict
import operator
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = 'tcrd5logs/'
LOGFILE = LOGDIR + '%s.log'%PROGRAM
TISSUESTYPEDFILE = '../data/Tissues_Typed_v2.1.csv'

def calc_and_load(args):
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
  
  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'Consensus Expression Values', 'source': 'IDG-KMC generated data by Steve Mathias at UNM.', 'app': PROGRAM, 'app_version': __version__, 'comments': 'Consensus of GTEx, HPM and HPA expression values are calculated by the loader app.'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'expression', 'where_clause': "etype = 'Consensus'"})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

  tmap = {} # tissue name to Tissue Type as per TIO
  line_ct = slmf.wcl(TISSUESTYPEDFILE)
  line_ct -= 1
  if not args['--quiet']:
    print '\nProcessiong {} lines in tissue mapping file: {}'.format(line_ct, TISSUESTYPEDFILE)
  with open(TISSUESTYPEDFILE, 'rU') as csvfile:
    csvreader = csv.reader(csvfile)
    header = csvreader.next() # skip header line
    ct = 0
    for row in csvreader:
      ct += 1
      tissue = row[0].lower()
      tmap[tissue] = row[2]
  if not args['--quiet']:
    print '  Got {} tissue name mappings'.format(len(tmap))

  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  tct = dba.get_target_count()
  if not args['--quiet']:
    print "\nCalculating/Loading Consensus expressions for {} TCRD targets".format(tct)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=tct).start() 
  ct = 0
  exp_ct = 0
  dba_err_ct = 0
  for t in dba.get_targets(include_annotations=True):
    ct += 1
    p = t['components']['protein'][0]
    if not 'expressions' in p:
      continue
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
    print "Processed {} targets.".format(ct)
    print "  Inserted {} new Consensus expression rows.".format(exp_ct)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

def default_factory():
  return {0: 0, 1: 0, 2: 0, 3: 0}

def aggregate_exps(exps, tmap, want):
  exps = [e for e in exps if e['etype'] in want]
  aggexps = defaultdict(default_factory)
  fvalmap = {'Not Detected': 0, 'Low': 1, 'Medium': 2, 'High': 3}
  for e in exps:
    tissue = e['tissue'].lower()
    if e['tissue'] not in tmap:
      continue
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


if __name__ == '__main__':
  print "\n{} (v{}) [{}]:".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  start_time = time.time()
  calc_and_load(args)
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))

