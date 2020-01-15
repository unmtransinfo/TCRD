#!/usr/bin/env python
# Time-stamp: <2019-04-10 15:28:56 smathias>
"""Load HomoloGene data into TCRD via TSV file.

Usage:
    load-HomoloGene.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-HomoloGene.py -h | --help

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
__copyright__ = "Copyright 2019, Steve Mathias"
__license__ = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__ = "1.0.0"

import os,sys,time
from docopt import docopt
from TCRDMP import DBAdaptor
import logging
import urllib
import csv
import pandas as pd
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = 'tcrd6logs/'
LOGFILE = LOGDIR + '%s.log'%PROGRAM
DOWNLOAD_DIR = '../data/NCBI/'
BASE_URL = 'ftp://ftp.ncbi.nih.gov/pub/HomoloGene/current/'
FILENAME = 'homologene.data'
TAXIDS = [9606, 10090, 10116] # Human, Mouse, Rat

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
  dataset_id = dba.ins_dataset( {'name': 'HomoloGene', 'source': 'File %s'%BASE_URL+FILENAME, 'app': PROGRAM, 'app_version': __version__, 'url': 'https://www.ncbi.nlm.nih.gov/homologene', 'comments': 'Only Human, Mouse and Rat members of HomoloGene groups are loaded. These relate protein to nhprotein.'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'homology'} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]

  infile = DOWNLOAD_DIR + FILENAME
  line_ct = slmf.wcl(infile)
  if not args['--quiet']:
    print "\nProcessing {} input lines in file {}".format(line_ct, infile)
  with open(infile, 'rU') as tsv:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    skip_ct = 0
    hom_ct = 0
    nf_ct = 0
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
      pbar.update(ct)
      # homologene_group_id    tax_id    ncbi_gene_id    symbol    protein_gi    ref_seq
      taxid = int(row[1])
      if taxid not in TAXIDS:
        skip_ct += 1
        continue
      if taxid == 9606:
        targets = dba.find_targets({'geneid': row[2]})
        if not targets:
          nf_ct += 1
          logger.warn("No target found for {}".format(row))
          continue
        for t in targets:
          p = t['components']['protein'][0]
          rv = dba.ins_homologene({'protein_id': p['id'], 'groupid': row[0], 'taxid': taxid})
          if rv:
            hom_ct += 1
          else:
            dba_err_ct += 1
      else:
        nhproteins = dba.find_nhproteins({'geneid': row[2]})
        if not nhproteins:
          nf_ct += 1
          logger.warn("No nhprotein found for {}".format(row))
          continue
        for nhp in nhproteins:
          rv = dba.ins_homologene({'nhprotein_id': nhp['id'], 'groupid': row[0], 'taxid': taxid})
          if rv:
            hom_ct += 1
          else:
            dba_err_ct += 1
  pbar.finish()
  print "Processed {} lines.".format(ct)
  print "Loaded {} new homologene rows".format(hom_ct)
  print "  Skipped {} non-Human/Mouse/Rat lines".format(skip_ct)
  if nf_ct > 0:
    print "WARNNING: No target/nhprotein found for {} lines. See logfile {} for details.".format(nf_ct, logfile)
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
