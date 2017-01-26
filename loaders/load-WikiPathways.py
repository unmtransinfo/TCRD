#!/usr/bin/env python
# Time-stamp: <2017-01-12 10:23:10 smathias>
"""Load WikiPathways links into TCRD from TSV file.

Usage:
    load-WikiPathways.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
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
  -d --debug DEBUGL    : set debugging output level (0-3) [default: 0]
  -? --help            : print this message and exit 
"""
__author__ = "Steve Mathias"
__email__ = "smathias@salud.unm.edu"
__org__ = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2015-2017, Steve Mathias"
__license__ = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__ = "2.0.0"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import csv
import urllib
import logging
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
DOWNLOAD_DIR = '../data/WikiPathways/'
BASE_URL = 'http://www.pathvisio.org/data/bots/gmt/current/'
PATHWAYS_FILE = 'gmt_wp_Homo_sapiens.gmt'

def download():
  if os.path.exists(DOWNLOAD_DIR + PATHWAYS_FILE):
    os.remove(DOWNLOAD_DIR + PATHWAYS_FILE)
  print "Downloading ", BASE_URL + PATHWAYS_FILE
  print "         to ", DOWNLOAD_DIR + PATHWAYS_FILE
  urllib.urlretrieve(BASE_URL + PATHWAYS_FILE, DOWNLOAD_DIR + PATHWAYS_FILE)

def load():
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

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'WikiPathways', 'source': 'File %s'%BASE_URL+PATHWAYS_FILE, 'app': PROGRAM, 'app_version': __version__, 'url': 'http://www.wikipathways.org/'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'pathway', 'where_clause': "pwtype = 'WikiPathways'"})
  if not rv:
    print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
    sys.exit(1)
    
  start_time = time.time()
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  fn = DOWNLOAD_DIR + PATHWAYS_FILE
  line_ct = wcl(fn)
  if not args['--quiet']:
    print "\nProcessing %d input line from WikiPathways file %s" % (line_ct, fn)
  with open(fn, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    # Example line:
    # Apoptosis Modulation and Signaling%WikiPathways_20160516%WP1772%Homo sapiens    http://www.wikipathways.org/instance/WP1772_r85184       843     3725    842 ...
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start()
    ct = 0
    gid_mark = {}
    notfnd = {}
    pw_ct = 0
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
      name = row[0].split('%')[0]
      wpid = row[1].split('/')[-1]
      geneids = row[2:]
      for geneid in geneids:
        gid_mark[geneid] = True
        targets = dba.find_targets({'geneid': geneid})
        if not targets:
          notfnd[geneid] = True
          continue
        for t in targets:
          pid = t['components']['protein'][0]['id']
          rv = dba.ins_pathway({'protein_id': pid, 'pwtype': 'WikiPathways', 'name': name,
                                'id_in_source': wpid, 'url': row[1]})
          if rv:
            pw_ct += 1
          else:
            dba_err_ct += 1
      pbar.update(ct)
  pbar.finish()
  elapsed = time.time() - start_time
  print "Processed %d WikiPathways. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "  Inserted %d pathway rows" % pw_ct
  if notfnd:
    print "WARNNING: %d (of %d) Gene IDs did not find a TCRD target." % (len(notfnd), len(gid_mark))
  if dba_err_ct > 0:
    print "WARNNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)
  

def wcl(fname):
  with open(fname) as f:
    for i, l in enumerate(f):
      pass
  return i + 1

def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])

if __name__ == '__main__':
  print "\n%s (v%s) [%s]:" % (PROGRAM, __version__, time.strftime("%c"))
  download()
  load()
  print "\n%s: Done.\n" % PROGRAM
