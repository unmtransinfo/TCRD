#!/usr/bin/env python
# Time-stamp: <2019-04-11 11:51:15 smathias>
"""Load ortholog data into TCRD via HGNC web API.

Usage:
    load-Orthologs.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-Orthologs.py -h | --help

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
__copyright__ = "Copyright 2017-2019, Steve Mathias"
__license__ = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__ = "1.4.0"

import os,sys,time
from docopt import docopt
from TCRDMP import DBAdaptor
import logging
import urllib
import gzip
import csv
import pandas as pd
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = 'tcrd6logs/'
LOGFILE = LOGDIR + '%s.log'%PROGRAM
DOWNLOAD_DIR = '../data/HGNC/'
BASE_URL = 'ftp://ftp.ebi.ac.uk/pub/databases/genenames/hcop/'
FILENAME = 'human_all_hcop_sixteen_column.txt.gz'
TAXID2SP = {'9598': 'Chimp', 
            '9544': 'Macaque',
            '10090': 'Mouse',
            '10116': 'Rat',
            '9615': 'Dog',
            '9796': 'Horse',
            '9913': 'Cow',
            '9823': 'Pig',
            '13616': 'Opossum',
            '9258': 'Platypus',
            '9031': 'Chicken',
            '28377': 'Anole lizard',
            '8364': 'Xenopus',
            '7955': 'Zebrafish',
            '6239': 'C. elegans',
            '7227': 'Fruitfly',
            '4932': 'S.cerevisiae'}


def download(args):
  gzfn = DOWNLOAD_DIR + FILENAME
  if os.path.exists(gzfn):
    os.remove(gzfn)
  fn = gzfn.replace('.gz', '')
  if os.path.exists(fn):
    os.remove(fn)
  if not args['--quiet']:
    print "\nDownloading ", BASE_URL + FILENAME
    print "         to ", gzfn
  urllib.urlretrieve(BASE_URL + FILENAME, gzfn)
  if not args['--quiet']:
    print "Uncompressing", gzfn
  ifh = gzip.open(gzfn, 'rb')
  ofh = open(fn, 'wb')
  ofh.write( ifh.read() )
  ifh.close()
  ofh.close()
  if not args['--quiet']:
    print "Done."

def parse_hcop16(filepath, args):
  orthos = list()
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  line_ct = slmf.wcl(filepath)
  if not args['--quiet']:
    print "\nProcessing {} lines in input file {}".format(line_ct, filepath)
  with open(filepath, 'rU') as tsv:
    tsvreader = csv.DictReader(tsv, delimiter='\t')
    for d in tsvreader:
      # ortholog_species
      # human_entrez_gene
      # human_ensembl_gene
      # hgnc_id
      # human_name
      # human_symbol
      # human_chr
      # human_assert_ids
      # ortholog_species_entrez_gene
      # ortholog_species_ensembl_gene
      # ortholog_species_db_id
      # ortholog_species_name
      # ortholog_species_symbol
      # ortholog_species_chr
      # ortholog_species_assert_ids
      # support
      src_ct = 0
      srcs = []
      if 'Inparanoid' in d['support']:
        src_ct += 1
        srcs.append('Inparanoid')
      if 'OMA' in d['support']:
        src_ct += 1
        srcs.append('OMA')
      if 'EggNOG' in d['support']:
        src_ct += 1
        srcs.append('EggNOG')
      if src_ct >= 2: # Only take rows with at least 2 out of three
        d['sources'] = ', '.join(srcs)
        orthos.append(d)
  if not args['--quiet']:
    print "  Generated ortholog dataframe with {} entries".format(len(orthos))
  ortho_df = pd.DataFrame(orthos)
  return ortho_df

def load(ortho_df, args):
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
  dataset_id = dba.ins_dataset( {'name': 'Orthologs', 'source': 'File %s'%BASE_URL+FILENAME, 'app': PROGRAM, 'app_version': __version__, 'url': 'https://www.genenames.org/cgi-bin/hcop'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'ortholog', 'comment': "Orthologs are majority vote from the OMA, EggNOG and InParanoid resources as per HGNC."} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]

  tct = dba.get_target_count()
  if not args['--quiet']:
    print "\nLoading ortholog data for {} TCRD targets".format(tct)
  logger.info("Loading ortholog data for {} TCRD targets".format(tct))
  pbar = ProgressBar(widgets=pbar_widgets, maxval=tct).start()  
  ct = 0
  ortho_ct = 0
  tskip_ct = 0
  skip_ct = 0
  notfnd = set()
  dba_err_ct = 0
  for target in dba.get_targets():
    ct += 1
    pbar.update(ct)
    logger.info("Processing target %d" % target['id'])
    p = target['components']['protein'][0]
    if p['sym']: # try first by symbol
      to_df = ortho_df.loc[ortho_df['human_symbol'] == p['sym']]
    elif p['geneid']: # then try by GeneID
      to_df = ortho_df.loc[ortho_df['human_entrez_gene'] == p['geneid']]
    else:      
      tskip_ct += 1
      continue
    if len(to_df) == 0:
      continue
    for idx, row in to_df.iterrows():
      if row['ortholog_species_symbol'] == '-' and row['ortholog_species_name'] == '-':
        skip_ct += 1
        continue
      sp = TAXID2SP[row['ortholog_species']]
      init = {'protein_id': p['id'], 'taxid': row['ortholog_species'],
              'species': sp, 'sources': row['sources'],
              'symbol': row['ortholog_species_symbol'], 'name': row['ortholog_species_name']}
      # Add MOD DB ID if it's there
      if row['ortholog_species_db_id'] != '-':
        init['db_id'] = row['ortholog_species_db_id']
      # Add NCBI Gene ID if it's there
      if row['ortholog_species_entrez_gene'] != '-':
        init['geneid'] = row['ortholog_species_entrez_gene']
      # Construct MOD URLs for mouse, rat, zebrafish, fly, worm and yeast
      if sp == 'Mouse':
        init['mod_url'] = 'http://www.informatics.jax.org/marker/' + row['ortholog_species_db_id']
      elif sp == 'Rat':
        rgdid = row['ortholog_species_db_id'].replace('RGD:', '')
        init['mod_url'] = 'http://rgd.mcw.edu/rgdweb/report/gene/main.html?id=' + rgdid
      elif sp == 'Zebrafish':
        init['mod_url'] = 'http://zfin.org/' + row['ortholog_species_db_id']
      elif sp == 'Fruitfly':
        init['mod_url'] = "http://flybase.org/reports/%s.html" % row['ortholog_species_db_id']
      elif sp == 'C. elegans':
        init['mod_url'] = 'http://www.wormbase.org/search/gene/' + row['ortholog_species_symbol']
      elif sp == 'S.cerevisiae':
        init['mod_url'] = 'https://www.yeastgenome.org/locus/' + row['ortholog_species_db_id']
      rv = dba.ins_ortholog(init)
      if rv:
        ortho_ct += 1
      else:
        dba_err_ct += 1
    pbar.update(ct)
  pbar.finish()
  print "Processed {} targets.".format(ct)
  print "Loaded {} new ortholog rows".format(ortho_ct)
  print "  Skipped {} empty ortholog entries".format(skip_ct)
  print "  Skipped {} targets with no sym/geneid".format(tskip_ct)
  if len(notfnd) > 0:
    print "  No orthologs found for {} targets.".format(len(notfnd))
  if dba_err_ct > 0:
    print "WARNNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)


if __name__ == '__main__':
  print "\n{} (v{}) [{}]:".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  start_time = time.time()
  download(args)
  fn = DOWNLOAD_DIR + FILENAME
  fn = fn.replace('.gz', '')
  ortho_df = parse_hcop16(fn, args)
  load(ortho_df, args)
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))
