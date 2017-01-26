#!/usr/bin/env python
# Time-stamp: <2017-01-11 12:37:12 smathias>
""" Load Reactome ppis into TCRD from TSV file.

Usage:
    load-ReactomePPIs.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-ReactomePPIs.py -h | --help

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
__copyright__ = "Copyright 2015-2017, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.0.0"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import logging
import csv
import urllib
import gzip
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
DOWNLOAD_DIR = '../data/Reactome/'
BASE_URL = 'http://www.reactome.org/download/current/'
FILENAME = 'homo_sapiens.interactions.txt.gz'

def download():
  gzfn = DOWNLOAD_DIR + FILENAME
  if os.path.exists(gzfn):
    os.remove(gzfn)
  fn = gzfn.replace('.gz', '')
  if os.path.exists(fn):
    os.remove(fn)
  print "\nDownloading ", BASE_URL + FILENAME
  print "         to ", gzfn
  urllib.urlretrieve(BASE_URL + FILENAME, gzfn)
  print "Uncompressing", gzfn
  ifh = gzip.open(gzfn, 'rb')
  ofh = open(fn, 'wb')
  ofh.write( ifh.read() )
  ifh.close()
  ofh.close()
  print "Done."

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
  dataset_id = dba.ins_dataset( {'name': 'Reactome Protein-Protein Interactions', 'source': "File %s"%BASE_URL+FILENAME, 'app': PROGRAM, 'app_version': __version__, 'url': 'http://www.reactome.org/'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'ppi', 'where_clause': "ppitype = 'Reactome'"})
  if not rv:
    print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
    sys.exit(1)

  start_time = time.time()
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  infile = (DOWNLOAD_DIR + FILENAME).replace('.gz', '')
  line_ct = wcl(infile)
  line_ct -= 1
  if not args['--quiet']:
    print "\nProcessing %d lines from Reactome PPI file %s" % (line_ct, infile)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  with open(infile, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    header = tsvreader.next() # skip header line
    ct = 0
    skip_ct = 0
    dup_ct = 0
    ppis = {}
    ppi_ct = 0
    up2pid = {}
    notfnd = {}
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
      pbar.update(ct)
      up1 = row[0].replace('UniProt:', '')
      up2 = row[3].replace('UniProt:', '')      
      if not up1 or not up2:
        skip_ct += 1
        continue
      # protein1
      if up1 in up2pid:
        pid1 = up2pid[up1]
      elif up1 in notfnd:
        continue
      else:
        t1 = find_target(dba, up1)
        if not t1:
          notfnd[up1] = True
          continue
        pid1 = t1['components']['protein'][0]['id']
        up2pid[up1] = pid1
      # protein2
      if up2 in up2pid:
        pid2 = up2pid[up2]
      elif up2 in notfnd:
        continue
      else:
        t2 = find_target(dba, up2)
        if not t2:
          notfnd[up2] = True
          continue
        pid2 = t2['components']['protein'][0]['id']
        up2pid[up2] = pid2
      ppik = up1 + "|" + up2
      if ppik in ppis:
        dup_ct += 1
        continue
      # Insert PPI
      rv = dba.ins_ppi( {'ppitype': 'Reactome', 
                         'protein1_id': pid1, 'protein1_str': up1,
                         'protein2_id': pid2, 'protein2_str': up2} )
      if rv:
        ppi_ct += 1
        ppis[ppik] = True
      else:
        dba_err_ct += 1
  pbar.finish()
  elapsed = time.time() - start_time
  print "%d Reactome PPI rows processed." % ct
  print "  Skipped %d rows without two interactors" % skip_ct
  print "  Skipped %d duplicate PPIs" % dup_ct
  print "  Inserted %d (%d) new ppi rows" % (ppi_ct, len(ppis))
  if len(notfnd) > 0:
    print "WARNNING: %d proteins NOT FOUND in TCRD:" % len(notfnd)
    #for d in notfnd:
    #  print d
  if dba_err_ct > 0:
    print "WARNNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)


def find_target(dba, up):
  targets = dba.find_targets({'uniprot': up})
  if targets:
    return targets[0]
  else:
    return None

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
