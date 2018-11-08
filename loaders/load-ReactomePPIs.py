#!/usr/bin/env python
# Time-stamp: <2018-03-29 12:57:54 smathias>
""" Load Reactome ppis into TCRD from TSV file.

Usage:
    load-ReactomePPIs.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
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
  -d --debug           : turn on debugging output
  -? --help            : print this message and exit 
"""
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2015-2018, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.1.0"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import logging
import csv
import urllib
import gzip
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd5logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
DOWNLOAD_DIR = '../data/Reactome/'
BASE_URL = 'https://reactome.org/download/current/interactors/'
FILENAME = 'reactome.homo_sapiens.interactions.tab-delimited.txt'

def download(args):
  fn = DOWNLOAD_DIR + FILENAME
  if os.path.exists(fn):
    os.remove(fn)
  if not args['--quiet']:
    print "\nDownloading ", BASE_URL + FILENAME
    print "         to ", fn
  urllib.urlretrieve(BASE_URL + FILENAME, fn)
  if not args['--quiet']:
    print "Done."

def load(args):
  loglevel = int(args['--loglevel'])
  if args['--logfile']:
    logfile = args['--logfile']
  else:
    logfile = LOGFILE
  logger = logging.getLogger(__name__)
  logger.setLevel(loglevel)
  if not args['--debug']:
    logger.propagate = False # turns off console logging when debug is 0
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
  dataset_id = dba.ins_dataset( {'name': 'Reactome Protein-Protein Interactions', 'source': "File %s"%BASE_URL+FILENAME, 'app': PROGRAM, 'app_version': __version__, 'url': 'http://www.reactome.org/'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'ppi', 'where_clause': "ppitype = 'Reactome'"})
  if not rv:
    print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
    sys.exit(1)

  infile = DOWNLOAD_DIR + FILENAME
  line_ct = slmf.wcl(infile)
  line_ct -= 1
  if not args['--quiet']:
    print "\nProcessing {} lines from Reactome PPI file {}".format(line_ct, infile)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
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
    notfnd = set()
    dba_err_ct = 0
    for row in tsvreader:
      # 0: Interactor 1 uniprot id
      # 1: Interactor 1 Ensembl gene id
      # 2: Interactor 1 Entrez Gene id
      # 3: Interactor 2 uniprot id
      # 4: Interactor 2 Ensembl gene id
      # 5: Interactor 2 Entrez Gene id
      # 6: Interaction type
      # 7: Interaction context Pubmed references
      ct += 1
      pbar.update(ct)
      if row[6] != 'complex':
        skip_ct += 1
        continue
      if not row[0].startswith('uniprotkb:'):
        continue
      if not row[3].startswith('uniprotkb:'):
        continue
      up1 = row[0].replace('uniprotkb:', '')
      up2 = row[3].replace('uniprotkb:', '')      
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
          notfnd.add(up1)
          logger.warn("No target found for UniProt: {}".format(up1))
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
          notfnd.add(up2)
          logger.warn("No target found for UniProt: {}".format(up2))
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
  print "{} Reactome PPI rows processed.".format(ct)
  print "  Skipped {} non-complex rows or rows without two UniProt interactors".format(skip_ct)
  print "  Skipped {} duplicate PPIs".format(dup_ct)
  print "  Inserted {} ({}) new ppi rows".format(ppi_ct, len(ppis))
  if notfnd:
    print "WARNNING: {} UniProt accessions did not find a TCRD target.".format(len(notfnd))
  if dba_err_ct > 0:
    print "WARNNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

def find_target(dba, up):
  targets = dba.find_targets({'uniprot': up})
  if targets:
    return targets[0]
  else:
    return None

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
