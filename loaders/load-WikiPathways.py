#!/usr/bin/env python
# Time-stamp: <2019-08-21 14:28:17 smathias>
"""Load WikiPathways links into TCRD from TSV file.

Usage:
    load-WikiPathways.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-WikiPathways.py -? | --help

Options:
  -h --dbhost DBHOST   : MySQL database host name [default: localhost]
  -n --dbname DBNAME   : MySQL database name [default: tcrevd]
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
__copyright__ = "Copyright 2015-2019, Steve Mathias"
__license__ = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__ = "3.0.0"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import csv
import urllib
import logging
from collections import defaultdict
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd6logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
DOWNLOAD_DIR = '../data/WikiPathways/'
BASE_URL = 'http://www.pathvisio.org/data/bots/gmt/current/'
PATHWAYS_FILE = 'gmt_wp_Homo_sapiens.gmt'

def download(args):
  if os.path.exists(DOWNLOAD_DIR + PATHWAYS_FILE):
    os.remove(DOWNLOAD_DIR + PATHWAYS_FILE)
  if not args['--quiet']:
    print "Downloading ", BASE_URL + PATHWAYS_FILE
    print "         to ", DOWNLOAD_DIR + PATHWAYS_FILE
  urllib.urlretrieve(BASE_URL + PATHWAYS_FILE, DOWNLOAD_DIR + PATHWAYS_FILE)

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
  dataset_id = dba.ins_dataset( {'name': 'WikiPathways', 'source': 'File %s'%BASE_URL+PATHWAYS_FILE, 'app': PROGRAM, 'app_version': __version__, 'url': 'http://www.wikipathways.org/'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'pathway', 'where_clause': "pwtype = 'WikiPathways'"})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)
    
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  fn = DOWNLOAD_DIR + PATHWAYS_FILE
  line_ct = slmf.wcl(fn)
  if not args['--quiet']:
    print "\nProcessing {} input lines from WikiPathways file {}".format(line_ct, fn)
  with open(fn, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    # Example line:
    # Apoptosis Modulation and Signaling%WikiPathways_20160516%WP1772%Homo sapiens    http://www.wikipathways.org/instance/WP1772_r85184       843     3725    842 ...
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start()
    ct = 0
    gid2pids = defaultdict(list)
    pmark = set()
    notfnd = set()
    pw_ct = 0
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
      name = row[0].split('%')[0]
      wpid = row[1].split('/')[-1]
      geneids = row[2:]
      for gid in geneids:
        if gid in gid2pids:
          pids = gid2pids[gid]
        elif gid in notfnd:
          continue
        else:
          targets = dba.find_targets({'geneid': gid})
          if not targets:
            notfnd.add(gid)
            continue
          pids = []
        for t in targets:
          pids.append(t['components']['protein'][0]['id'])
        gid2pids[gid] = pids # save this mapping so we only lookup each target once
        for pid in pids:
          rv = dba.ins_pathway({'protein_id': pid, 'pwtype': 'WikiPathways', 'name': name,
                                'id_in_source': wpid, 'url': row[1]})
          if rv:
            pw_ct += 1
            pmark.add(pid)
          else:
            dba_err_ct += 1
      pbar.update(ct)
  pbar.finish()
  for gid in gid2pids:
    logger.warn("No target found for {}".format(gid))
  print "Processed {} WikiPathways.".format(ct)
  print "  Inserted {} pathway rows for {} proteins.".format(pw_ct, len(pmark))
  if notfnd:
    print "  No target found for {} Gene IDs. See logfile {} for details.".format(len(notfnd), logfile)
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
