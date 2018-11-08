#!/usr/bin/env python
"""Load Years for GeneRIF PubMed IDs into TCRD.

Usage:
    load-GeneRIF_Years.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>] [--pastid=<int>]
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
  -d --debug           : turn on debugging output
  -? --help            : print this message and exit 
"""
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2017-2018, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "1.1.0"

import os,sys,time,urllib,re
from docopt import docopt
from TCRD import DBAdaptor
import logging
import cPickle as pickle
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd5logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
PICKLE_FILE = '../data/TCRDv5_PubMed2Date.p'

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
  dataset_id = dba.ins_dataset( {'name': 'GeneRIF Years', 'source': 'PubMed records via NCBI E-Utils', 'app': PROGRAM, 'app_version': __version__, 'url': 'https://www.ncbi.nlm.nih.gov/pubmed'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'generif', 'column_name': 'years'})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

  pubmed2date = pickle.load(open(PICKLE_FILE, 'rb'))
  if not args['--quiet']:
    print "\nGot %d PubMed date mappings from file %s" % (len(pubmed2date), PICKLE_FILE)
  
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  generifs = dba.get_generifs()
  if not args['--quiet']:
    print "\nProcessing {} GeneRIFs".format(len(generifs))
  logger.info("Processing {} GeneRIFs".format(len(generifs)))
  pbar = ProgressBar(widgets=pbar_widgets, maxval=len(generifs)).start()
  yrre = re.compile(r'^(\d{4})')
  ct = 0
  yr_ct = 0
  skip_ct = 0
  net_err_ct = 0
  dba_err_ct = 0
  for generif in generifs:
    ct += 1
    logger.debug("Processing GeneRIF: {}".format(generif))
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
  if not args['--quiet']:
    print "{} GeneRIFs processed.".format(ct)
  print "  Updated {} genefifs with years".format(yr_ct)
  print "  Skipped {} generifs with no years.".format(skip_ct)
  if dba_err_ct > 0:
    print "WARNNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)
  if net_err_ct > 0:
    print "WARNING: {} Network/E-Utils errors occurred. See logfile {} for details.".format(net_err_ct, logfile)


if __name__ == '__main__':
  print "\n{} (v{}) [{}]:".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  start_time = time.time()
  load(args)
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))
