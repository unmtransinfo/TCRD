#!/usr/bin/env python
# Time-stamp: <2018-05-18 12:05:52 smathias>
"""Load Reactome Pathway links into TCRD from download files.

Usage:
    load-PathwaysReactome.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-PathwaysReactome.py -? | --help

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
__author__ = "Steve Mathias"
__email__ = "smathias@salud.unm.edu"
__org__ = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2015-2018, Steve Mathias"
__license__ = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__ = "2.1.0"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import csv
import urllib
import zipfile
import logging
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd5logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
DOWNLOAD_DIR = '../data/Reactome/'
BASE_URL = 'http://www.reactome.org/download/current/'
PATHWAYS_FILE = 'ReactomePathways.gmt.zip'

def download(args):
  zfn = DOWNLOAD_DIR + PATHWAYS_FILE
  if os.path.exists(zfn):
    os.remove(zfn)
  fn = zfn.replace('.zip', '')
  if os.path.exists(fn):
    os.remove(fn)
  if not args['--quiet']:
    print "Downloading ", BASE_URL + PATHWAYS_FILE
    print "         to ", DOWNLOAD_DIR + PATHWAYS_FILE
  urllib.urlretrieve(BASE_URL + PATHWAYS_FILE, DOWNLOAD_DIR + PATHWAYS_FILE)
  if not args['--quiet']:
    print "Unzipping", zfn
  zip_ref = zipfile.ZipFile(DOWNLOAD_DIR + PATHWAYS_FILE, 'r')
  zip_ref.extractall(DOWNLOAD_DIR)
  zip_ref.close()

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
  dataset_id = dba.ins_dataset( {'name': 'Reactome Pathways', 'source': 'File %s'%BASE_URL+PATHWAYS_FILE, 'app': PROGRAM, 'app_version': __version__, 'url': 'http://www.reactome.org/'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'pathway', 'where_clause': "pwtype = 'Reactome'"})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)
    
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  infile = (DOWNLOAD_DIR + PATHWAYS_FILE).replace('.zip', '')
  line_ct = slmf.wcl(infile)
  if not args['--quiet']:
    print "\nProcessing {} input line from Reactome Pathways file {}".format(line_ct, infile)
  with open(infile, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    # Example line:
    # Apoptosis       R-HSA-109581    Reactome Pathway        ACIN1   ADD1    AKT1    AKT2   ...
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start()
    ct = 0
    sym_mark = {}
    notfnd = set()
    pw_ct = 0
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
      pwname = row[0]
      pwid = row[1]
      url = 'http://www.reactome.org/content/detail/' + pwid
      syms = row[3:]
      for sym in syms:
        sym_mark[sym] = True
        if sym in notfnd:
          continue
        targets = dba.find_targets({'sym': sym})
        if not targets:
          notfnd.add(sym)
          logger.warn("No target found for Gene symbol: {}".format(sym))
          continue
        for t in targets:
          pid = t['components']['protein'][0]['id']
          rv = dba.ins_pathway({'protein_id': pid, 'pwtype': 'Reactome', 'name': pwname,
                                'id_in_source': pwid, 'url': url})
          if rv:
            pw_ct += 1
          else:
            dba_err_ct += 1
      pbar.update(ct)
  pbar.finish()
  print "Processed {} Reactome Pathways.".format(ct)
  print "  Inserted {} pathway rows".format(pw_ct)
  if notfnd:
    print "WARNNING: {} (of {}) Gene symbols did not find a TCRD target.".format(len(notfnd), len(sym_mark))
  if dba_err_ct > 0:
    print "WARNNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)


if __name__ == '__main__':
  print "\n{} (v{}) [{}]:".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  start_time = time.time()
  download(args)
  load(args)
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))
