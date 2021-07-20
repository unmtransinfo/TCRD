#!/usr/bin/env python
# Time-stamp: <2020-12-03 14:48:08 smathias>
"""
Load TIGA trait association data into TCRD from tab-delimited files.

Usage:
    load-TIGA.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-TIGA.py -h | --help

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
__copyright__ = "Copyright 2020, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "1.0.0"

import os,sys,time,re
from docopt import docopt
from TCRD7 import DBAdaptor
import urllib
import gzip
import csv
from collections import defaultdict
import logging
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = 'tcrd6logs/'
LOGFILE = LOGDIR + '%s.log'%PROGRAM
DOWNLOAD_DIR = '../data/TIGA/'
BASE_URL = 'https://unmtid-shinyapps.net/download/TIGA/'
TIGA_FILE = 'tiga_gene-trait_stats.tsv.gz'
TIGA_PROV_FILE = 'tiga_gene-trait_provenance.tsv.gz'

def download(args):
  for gzfn in [TIGA_FILE, TIGA_PROV_FILE]:
    gzfp = DOWNLOAD_DIR + gzfn
    fp = gzfp.replace('.gz', '')
    if os.path.exists(gzfp):
      os.remove(gzfp)
    if os.path.exists(fp):
      os.remove(fp)
    if not args['--quiet']:
      print "\nDownloading", BASE_URL + gzfn
      print "         to", gzfp
    urllib.urlretrieve(BASE_URL + gzfn, gzfp)
    if not args['--quiet']:
      print "Uncompressing", gzfp
    ifh = gzip.open(gzfp, 'rb')
    ofh = open(fp, 'wb')
    ofh.write( ifh.read() )
    ifh.close()
    ofh.close()

def load(args, dba, logger, logfile):
  infile = DOWNLOAD_DIR + TIGA_FILE.replace('.gz', '')
  line_ct = slmf.wcl(infile)
  if not args['--quiet']:
    print "\nProcessing {} lines in TIGA file {}".format(line_ct, infile)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  ct = 0
  k2pids = defaultdict(list) # map sym|ENSG to TCRD pids
  notfnd = set()
  dba_err_ct = 0
  pmark = {}
  tiga_ct = 0
  with open(infile, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    header = tsvreader.next() # skip header line
    ct += 1
    for row in tsvreader:
      # 0: ensemblId
      # 1: efoId
      # 2: trait
      # 3: n_study
      # 4: n_snp
      # 5: n_snpw
      # 6: geneNtrait
      # 7: geneNstudy
      # 8: traitNgene
      # 9: traitNstudy
      # 10: pvalue_mlog_median
      # 11: or_median
      # 12: n_beta
      # 13: study_N_mean
      # 14: rcras
      # 15: geneSymbol
      # 16: geneIdgTdl
      # 17: geneFamily
      # 18: geneIdgList
      # 19: geneName
      # 20: meanRank
      # 21: meanRankScore
      ct += 1
      pbar.update(ct)
      sym = row[15]
      ensg = row[0]
      #ensg = re.sub('\.\d+$', '', row[0]) # get rid of version if present
      k = sym + '|' + ensg
      if k in k2pids:
        # we've already found it
        pids = k2pids[k]
      elif k in notfnd:
        # we've already not found it
        continue
      else:
        # look it up
        targets = dba.find_targets({'sym': sym}, False)
        if not targets:
          targets = dba.find_targets_by_xref({'xtype': 'Ensembl', 'value': ensg}, False)
          notfnd.add(k)
          continue
        pids = []
        for t in targets:
          pids.append(t['components']['protein'][0]['id'])
        k2pids[ensg] = pids # save this mapping so we only lookup each target once
      ormed = None
      if row[11] != 'NA':
        ormed = row[11]
      init = {'ensg': row[0], 'efoid': row[1], 'trait': row[2], 'n_study': row[3], 'n_snp': row[4],
              'n_snpw': row[5], 'geneNtrait': row[6], 'geneNstudy': row[7], 'traitNgene': row[8],
              'traitNstudy': row[9], 'pvalue_mlog_median': row[10], 'or_median': ormed,
              'n_beta': row[12], 'study_N_mean': row[13], 'rcras': row[14], 'meanRank': row[20],
              'meanRankScore': row[21]}
      for pid in pids:
        init['protein_id'] = pid
        rv = dba.ins_tiga(init)
        if not rv:
          dba_err_ct += 1
          continue
        tiga_ct += 1
        pmark[pid] = True
  pbar.finish()
  for k in notfnd:
    logger.warn("No target found for {}".format(k))
  print "Processed {} lines".format(ct)
  print "  Inserted {} new tiga rows for {} proteins".format(tiga_ct, len(pmark))
  if notfnd:
    print "  No target found for {} ENSGs. See logfile {} for details.".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

  infile = DOWNLOAD_DIR + TIGA_PROV_FILE.replace('.gz', '')
  line_ct = slmf.wcl(infile)
  if not args['--quiet']:
    print "\nProcessing {} lines in TIGA provenance file {}".format(line_ct, infile)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  ct = 0
  tigaprov_ct = 0
  dba_err_ct = 0
  with open(infile, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    header = tsvreader.next() # skip header line
    ct += 1
    for row in tsvreader:
      # 0: ensemblId
      # 1: TRAIT_URI
      # 2: STUDY_ACCESSION
      # 3: PUBMEDID
      # 4: efoId
      ct += 1
      rv = dba.ins_tiga_provenance( {'ensg': row[0], 'efoid': row[4],
                                     'study_acc': row[2], 'pubmedid': row[3]} )
      if not rv:
        dba_err_ct += 1
        continue
      tigaprov_ct += 1
      pbar.update(ct)
  pbar.finish()
  print "Processed {} lines".format(ct)
  print "  Inserted {} new tiga rows".format(tigaprov_ct)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

        
if __name__ == '__main__':
  print "\n%s (v%s) [%s]:\n" % (PROGRAM, __version__, time.strftime("%c"))
  
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  if args['--logfile']:
    logfile =  args['--logfile']
  else:
    logfile = LOGFILE
  loglevel = int(args['--loglevel'])
  logger = logging.getLogger(__name__)
  logger.setLevel(loglevel)
  if not args['--debug']:
    logger.propagate = False # turns off console logging
  fh = logging.FileHandler(LOGFILE)
  fmtr = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
  fh.setFormatter(fmtr)
  logger.addHandler(fh)

  dba_params = {'dbhost': args['--dbhost'], 'dbname': args['--dbname'], 'logger_name': __name__}
  dba = DBAdaptor(dba_params)
  dbi = dba.get_dbinfo()
  logger.info("Connected to TCRD database {} (schema ver {}; data ver {})".format(args['--dbname'], dbi['schema_ver'], dbi['data_ver']))
  if not args['--quiet']:
    print "Connected to TCRD database {} (schema ver {}; data ver {})".format(args['--dbname'], dbi['schema_ver'], dbi['data_ver'])

  #download(args)
  start_time = time.time()
  load(args, dba, logger, logfile)
  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'TIGA', 'source': 'IDG-KMC generated data by Jeremy Yang at UNM .', 'app': PROGRAM, 'app_version': __version__, 'url': 'https://unmtid-shinyapps.net/shiny/tiga/'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'tiga'},
            {'dataset_id': dataset_id, 'table_name': 'tiga_provenance'} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))
