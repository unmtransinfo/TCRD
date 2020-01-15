#!/usr/bin/env python
# Time-stamp: <2019-09-04 09:36:44 smathias>
"""Calculate CDFs for Harmonizome data and load into TCRD.

Usage:
    load-HGramCDFs.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-HGramCDFs.py -? | --help

Options:
  -h --dbhost DBHOST   : MySQL database host name [default: localhost]
  -n --dbname DBNAME   : MySQL database name [default: tcrdev]
  -l --logfile LOGF    : set log file name
  -v --loglevel LOGL   : set logging level [default: 20]
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
__copyright__ = "Copyright 2016-2019, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "3.0.0"

import os,sys,time
from docopt import docopt
from TCRDMP import DBAdaptor
import math
import numpy
import logging
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = 'tcrd6logs/'
LOGFILE = LOGDIR + '%s.log'%PROGRAM

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

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'Harmonogram CDFs', 'source': 'IDG-KMC generated data by Steve Mathias at UNM.', 'app': PROGRAM, 'app_version': __version__, 'comments': 'CDFs are calculated by the loader app based on gene_attribute data in TCRD.'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': 1, 'table_name': 'hgram_cdf'})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]

  # Create a dictionary of gene_attribute_type.name => [] pairs
  counts = {}
  # Create a dictionary of gene_attribute_type.name => {} pairs
  stats = {}
  gatypes = dba.get_gene_attribute_types()
  for ga in gatypes:
    counts[ga] = []
    stats[ga] = {}

  tct = dba.get_target_count(idg=False)
  if not args['--quiet']:
    print "\nCollecting counts for {} gene attribute types on {} TCRD targets".format(len(gatypes), tct)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=tct).start()
  ct = 0
  for t in dba.get_targets(idg=False, include_annotations=True, get_ga_counts=True):
    ct += 1
    pbar.update(ct)
    p = t['components']['protein'][0]
    pid = p['id']
    if not 'gene_attribute_counts' in p: continue
    for type,attr_count in p['gene_attribute_counts'].items():
      counts[type].append(attr_count)
  pbar.finish()

  print "\nCalculatig Gene Attribute stats. See logfile {}.".format(logfile)
  logger.info("Calculatig Gene Attribute stats:")
  for type,l in counts.items():
    if len(l) == 0:
      del(counts[type])
      continue
    npa = numpy.array(l)
    logger.info("  %s: %d counts; mean: %.2f; std: %.2f" % (type, len(l), npa.mean(), npa.std()))
    stats[type]['mean'] = npa.mean()
    stats[type]['std'] = npa.std()

  print "\nLoading HGram CDFs for {} TCRD targets".format(tct)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=tct).start()
  ct = 0
  nan_ct = 0
  cdf_ct = 0
  dba_err_ct = 0
  for t in dba.get_targets(idg=False, include_annotations=True, get_ga_counts=True):
    ct += 1
    p = t['components']['protein'][0]
    pid = p['id']
    if not 'gene_attribute_counts' in p: continue
    for type,attr_count in p['gene_attribute_counts'].items():
      attr_cdf = gaussian_cdf(attr_count, stats[type]['mean'], stats[type]['std'])
      if math.isnan(attr_cdf):
        attr_cdf = 1.0 / (1.0 + math.exp(-1.702*((attr_count-stats[type]['mean']) / stats[type]['std'] )))
      if math.isnan(attr_cdf):
        nan_ct += 1
        continue
      rv = dba.ins_hgram_cdf({'protein_id': p['id'], 'type': type,
                              'attr_count': attr_count, 'attr_cdf': attr_cdf})
      if not rv:
        dba_err_ct += 1
        continue
      cdf_ct += 1
    pbar.update(ct)
  pbar.finish()
  print "Processed {} targets.".format(ct)
  print "  Loaded {} new hgram_cdf rows".format(cdf_ct)
  print "  Skipped {} NaN CDFs".format(nan_ct)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

def gaussian_cdf(ct, mu, sigma):
  err = math.erf((ct - mu) / (sigma * math.sqrt(2.0)))
  cdf = 0.5 * ( 1.0 + err )
  return cdf


if __name__ == '__main__':
  print "\n{} (v{}) [{}]:".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  start_time = time.time()
  load(args)
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))









