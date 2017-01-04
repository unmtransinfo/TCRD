#!/usr/bin/env python
# Time-stamp: <2017-01-04 12:32:59 smathias>
"""Calculate CDFs for Harmonizome data and load into TCRD.

Usage:
    load-HGramCDFs.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
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
  -d --debug DEBUGL    : set debugging output level (0-3) [default: 0]
  -? --help            : print this message and exit 
"""
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2016, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.0.0"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import math
import numpy
import logging
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
DBHOST = 'localhost'
DBPORT = 3306
DBNAME = 'tcrd'
LOGFILE = 'tcrd4logs/%s.log'%PROGRAM

def main():
  args = docopt(__doc__, version=__version__)
  debug = int(args['--debug'])
  if debug:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  loglevel = int(args['--loglevel'])
  if args['--logfile']:
    logfile = args['--logfile']
  else:
    logfile = LOGFILE
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

  # Provenance
  rv = dba.ins_provenance({'dataset_id': 1, 'table_name': 'hgram_cdf'})
  if not rv:
    print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
    sys.exit(1)

  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]

  # Create a dictionary of gene_attribute_type.name => [] pairs
  counts = {}
  # Create a dictionary of gene_attribute_type.name => {} pairs
  stats = {}
  gatypes = dba.get_gene_attribute_types()
  for ga in gatypes:
    counts[ga] = []
    stats[ga] = {}
  start_time = time.time()
  tct = dba.get_target_count(idg=False)
  print "\nCollecting counts for %d gene attribute types on %d TCRD targets" % (len(gatypes), tct)
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
      #p2cts[pid] = attr_count
  pbar.finish()

  print "Calculatig Gene Attribute stats. See logfile %s." % logfile
  logger.info("Calculatig Gene Attribute stats:")
  for type,l in counts.items():
    if len(l) == 0:
      del(counts[type])
      continue
    npa = numpy.array(l)
    logger.info("  %s: %d counts; mean: %.2f; std: %.2f" % (type, len(l), npa.mean(), npa.std()))
    stats[type]['mean'] = npa.mean()
    stats[type]['std'] = npa.std()

  start_time = time.time()
  print "\nLoading HGram CDFs for %d TCRD targets" % tct
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
  print "Processed %d targets." % ct
  print "  Loaded %d new hgram_cdf rows" % cdf_ct
  print "  Skipped %d NaN CDFs" % nan_ct
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)

  elapsed = time.time() - start_time
  print "\n%d targets processed." % ct
  print "\n%s: Done. Elapsed time: %s" % (PROGRAM, secs2str(elapsed))
  print

def gaussian_cdf(ct, mu, sigma):
  err = math.erf((ct - mu) / (sigma * math.sqrt(2.0)))
  cdf = 0.5 * ( 1.0 + err )
  return cdf

def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])

if __name__ == '__main__':
    main()








