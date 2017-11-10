#!/usr/bin/env python
# Time-stamp: <2017-11-10 11:41:06 smathias>
"""Load ortholog data into TCRD via HGNC web API.

Usage:
    load-Orthologs.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
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
  -d --debug DEBUGL    : set debugging output level (0-3) [default: 0]
  -? --help            : print this message and exit 
"""
__author__ = "Steve Mathias"
__email__ = "smathias@salud.unm.edu"
__org__ = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2017, Steve Mathias"
__license__ = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__ = "1.2.0"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import logging
import urllib
import gzip
import csv
import pandas as pd
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
LOGFILE = "%s.log" % PROGRAM
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
  start_time = time.time()
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
  elapsed = time.time() - start_time
  if not args['--quiet']:
    print "Done. Elapsed time: %s" % secs2str(elapsed)

def parse_hcop16(filepath, args):
  orthos = list()
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  line_ct = wcl(fn)
  if not args['--quiet']:
    print "\nProcessing %d input lines from file %s" % (line_ct, fn)
  with open(fn, 'rU') as tsv:
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
  ortho_df = pd.DataFrame(orthos)
  if not args['--quiet']:
    print "  Generated ortholog dataframe with %d entries" % len(orthos)
  return ortho_df

def load(ortho_df, args, logger):
  # DBAdaptor uses same logger as main()
  dba_params = {'dbhost': args['--dbhost'], 'dbname': args['--dbname'], 'logger_name': __name__}
  dba = DBAdaptor(dba_params)
  dbi = dba.get_dbinfo()
  logger.info("Connected to TCRD database %s (schema ver %s; data ver %s)", args['--dbname'], dbi['schema_ver'], dbi['data_ver'])
  if not args['--quiet']:
    print "\nConnected to TCRD database %s (schema ver %s; data ver %s)" % (args['--dbname'], dbi['schema_ver'], dbi['data_ver'])

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'Orthologs', 'source': 'File %s'%BASE_URL+FILENAME, 'app': PROGRAM, 'app_version': __version__, 'url': 'https://www.genenames.org/cgi-bin/hcop'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'ortholog', 'comment': "Orthologs are majority vote from the OMA, EggNOG and InParanoid resources as per HGNC."} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    if not rv:
      print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
      sys.exit(1)

  start_time = time.time()
  
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  tct = dba.get_target_count()
  if not args['--quiet']:
    print "\nLoading ortholog data for %d TCRD targets" % tct
  logger.info("Loading ortholog data for %d TCRD targets" % tct)
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
  elapsed = time.time() - start_time
  print "Processed %d targets. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "Loaded %d new ortholog rows" % ortho_ct
  print "  Skipped %d empty ortholog entries" % skip_ct
  print "  Skipped %d targets with no sym/geneid" % tskip_ct
  if len(notfnd) > 0:
    print "  No orthologs found for %d targets." % len(notfnd)
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
  args = docopt(__doc__, version=__version__)
  if not args['--quiet']:
    print "\n%s (v%s) [%s]:" % (PROGRAM, __version__, time.strftime("%c"))
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
  
  #download(args)
  fn = DOWNLOAD_DIR + FILENAME
  fn = fn.replace('.gz', '')
  ortho_df = parse_hcop16(fn, args)
  load(ortho_df, args, logger)
  
  print "\n%s: Done.\n" % PROGRAM
