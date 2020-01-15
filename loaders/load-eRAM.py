#!/usr/bin/env python
# Time-stamp: <2019-04-16 11:44:50 smathias>
"""Load disease associations into TCRD from eRAM shelf file.

Usage:
    load-eRAM.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-eRAM.py -? | --help

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
__copyright__ = "Copyright 2018-2019, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "1.1.0"

import os,sys,time
from docopt import docopt
from TCRDMP import DBAdaptor
import logging
import shelve
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd6logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
ERAM_SHELF_FILE = '../data/eRAM/eRAM.db'

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
  dataset_id = dba.ins_dataset( {'name': 'eRAM Disease Associations', 'source': 'Data scraped from eRAM web pages.', 'app': PROGRAM, 'app_version': __version__, 'url': 'http://www.unimd.org/eram/'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'disease', 'where_clause': "dtype = 'eRAM'"})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)
  
  s = shelve.open(ERAM_SHELF_FILE)
  dis_ct = len(s['disease_names'])
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  if not args['--quiet']:
    print "\nProcessing {} disease names in shelf file {}".format(dis_ct, ERAM_SHELF_FILE)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=dis_ct).start() 
  ct = 0
  pmark = {}
  skip_ct = 0
  dnerr1_ct = 0
  dnerr2_ct = 0
  notfnd = set()
  dis_ct = 0
  dba_err_ct = 0
  for dname in s['disease_names']:
    ct += 1
    try:
      dname = str(dname)
    except:
      dnerr2_ct += 1
      logger.warn("UnicodeEncodeError for disease name '{}'".format(dname.encode('ascii', 'ignore')))
      continue
    if dname not in s:
      dnerr_ct += 1
      logger.warn("Disease name '{}' not in shelf".format(dname))
      continue
    if 'currated_genes' not in s[dname]:
      skip_ct += 1
      continue
    for cg in s[dname]['currated_genes']:
      sym = cg['sym']
      geneid = cg['geneid']
      k = "%s|%s"%(sym,geneid)
      if k in notfnd:
        continue
      targets = dba.find_targets({'sym': sym})
      if not targets:
        targets = dba.find_targets({'geneid': geneid})
      if not targets:
        notfnd.add(k)
        logger.warn("No target found for {}".format(k))
        continue
      for t in targets:
        p = t['components']['protein'][0]
        pmark[t['id']] = True
        for doid in s[dname]['doids']:
          rv = dba.ins_disease( {'protein_id': p['id'], 'dtype': 'eRAM', 'name': dname,
                                 'did': doid, 'source': cg['sources']} )
          if not rv:
            dba_err_ct += 1
            continue
          dis_ct += 1
    pbar.update(ct)
  pbar.finish()
  print "{} lines processed.".format(ct)
  print "Inserted {} new disease rows for {} proteins".format(dis_ct, len(pmark))
  if skip_ct > 0:
    print "Skipped {} diseases with no currated genes. See logfile {} for details.".format(skip_ct, logfile)
  if dnerr1_ct > 0:
    print "{} disease names not found in shelf. See logfile {} for details.".format(dnerr1_ct, logfile)
  if dnerr2_ct > 0:
    print "{} disease names cannot be decoded to strs. See logfile {} for details.".format(dnerr2_ct, logfile)
  if notfnd:
    print "No target found for {} stringids/symbols. See logfile {} for details.".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)


if __name__ == '__main__':
  print "\n{} (v{}) [{}]:".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  start_time = time.time()
  load(args)
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))
