#!/usr/bin/env python
"""Load Years for GeneRIF PubMed IDs into TCRD.

Usage:
    load-GeneRIF_Years.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>] [--pastid=<int>]
    load-GeneRIF_Years.py -h | --help

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
__copyright__ = "Copyright 2017, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "1.0.0"

import os,sys,time,urllib,re
from docopt import docopt
from TCRD import DBAdaptor
import logging
import cPickle as pickle
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
PICKLE_FILE = '../data/TCRDv4.6.7_PubMed2Date.p'

def load(args, logger):
  # DBAdaptor
  dba_params = {'dbhost': args['--dbhost'], 'dbname': args['--dbname'],
                'logger_name': __name__, 'loglevel': args['--loglevel']}
  dba = DBAdaptor(dba_params)
  dbi = dba.get_dbinfo()
  logger.info("Connected to TCRD database %s (schema ver %s; data ver %s)", args['--dbname'], dbi['schema_ver'], dbi['data_ver'])
  if not args['--quiet']:
    print "\nConnected to TCRD database %s (schema ver %s; data ver %s)" % (args['--dbname'], dbi['schema_ver'], dbi['data_ver'])
  
  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'GeneRIF Years', 'source': 'PubMed records via NCBI E-Utils', 'app': PROGRAM, 'app_version': __version__, 'url': 'https://www.ncbi.nlm.nih.gov/pubmed'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'generif', 'column_name': 'years'})
  if not rv:
    print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
    sys.exit(1)

  start_time = time.time()

  pubmed2date = pickle.load(open(PICKLE_FILE, 'rb'))
  if not args['--quiet']:
    print "\nGot %d PubMed date mappings from file %s" % (len(pubmed2date), PICKLE_FILE)
  
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  generifs = dba.get_generifs()
  if not args['--quiet']:
    print "\nProcessing %d GeneRIFs" % len(generifs)
  logger.info("Processing %d GeneRIFs" % len(generifs))
  pbar = ProgressBar(widgets=pbar_widgets, maxval=len(generifs)).start()
  yrre = re.compile(r'^(\d{4})')
  ct = 0
  yr_ct = 0
  skip_ct = 0
  net_err_ct = 0
  dba_err_ct = 0
  for generif in generifs:
    ct += 1
    logger.debug("Processing GeneRIF: %s" % generif)
    # GeneRIFs with multiple refs often have duplicates, so fix that
    if "|" in generif['pubmed_ids']:
      pmids = set(generif['pubmed_ids'].split("|"))
      pmids = list(pmids)
      rv = dba.do_update({'table': 'generif', 'id': generif['id'],
                          'col': 'pubmed_ids', 'val':"|".join(pmids)})
      if not rv:
        dba_err_ct += 1
    else:
      pmids = [generif['pubmed_ids']]
    
    years = list()
    for pmid in pmids:
      if pmid in pubmed2date:
        m = yrre.match(pubmed2date[pmid])
        if m:
          years.append(m.groups(1)[0])
        else:
          years.append('')
      else:
        years.append('')
    # See if we got any years...
    if any(years): # if so, so do the updates
      rv = dba.do_update({'table': 'generif', 'id': generif['id'],
                          'col': 'years', 'val':"|".join(years)})
      if rv:
        yr_ct += 1
      else:
        dba_err_ct += 1
    else: # if not, skip
      skip_ct += 1
    pbar.update(ct)
  pbar.finish()
  elapsed = time.time() - start_time
  if not args['--quiet']:
    print "%d GeneRIFs processed. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "  Updated %d genefifs with years" % yr_ct
  print "  Skipped %d generifs with no years." % skip_ct
  if dba_err_ct > 0:
    print "WARNNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)
  if net_err_ct > 0:
    print "WARNING: %d Network/E-Utils errors occurred. See logfile %s for details." % (net_err_ct, logfile)

def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])

if __name__ == '__main__':
  args = docopt(__doc__, version=__version__)
  if not args['--quiet']:
    print "\n%s (v%s) [%s]:" % (PROGRAM, __version__, time.strftime("%c"))
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

  load(args, logger)

  print "\n%s: Done.\n" % PROGRAM

