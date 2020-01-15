#!/usr/bin/env python
# Time-stamp: <2018-05-18 12:02:05 smathias>
"""Load GWAS Catalog phenotype data into TCRD from TSV file.

Usage:
    load-GWASCatalogPhenotypes.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-GWASCatalogPhenotypes.py -? | --help

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

import os,sys,time, re
from docopt import docopt
from TCRD import DBAdaptor
import logging
import csv
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd5logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
# File description is here:
# http://www.ebi.ac.uk/gwas/docs/fileheaders
# Get file here:
# https://www.ebi.ac.uk/gwas/docs/file-downloads
INFILE = '../data/EBI/gwas_catalog_v1.0.1-associations_e91_r2018-03-13.tsv'
OUTFILE = '../data/EBI/TCRDv5-GWAS_Mapping.csv'

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
  dataset_id = dba.ins_dataset( {'name': 'GWAS Catalog', 'source': 'File %s from http://www.ebi.ac.uk/gwas/docs/file-downloads'%os.path.basename(INFILE), 'app': PROGRAM, 'app_version': __version__, 'url': 'https://www.ebi.ac.uk/gwas/docs/file-downloads'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'phenotype', 'where_clause': "ptype = 'GWAS Catalog'"})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)
  
  line_ct = slmf.wcl(INFILE)
  line_ct -= 1 
  if not args['--quiet']:
    print '\nProcessing {} lines from input file {}'.format(line_ct, INFILE)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start()
  outlist = []
  with open(INFILE, 'rU') as tsvfile:
    tsvreader = csv.reader(tsvfile, delimiter='\t')
    header = tsvreader.next() # skip header line
    ct = 0
    notfnd = set()
    tmark = {}
    pt_ct = 0
    dba_err_ct = 0
    # 0: DATE ADDED TO CATALOG
    # 1: PUBMEDID
    # 2: FIRST AUTHOR
    # 3: DATE
    # 4: JOURNAL
    # 5: LINK
    # 6: STUDY
    # 7: DISEASE/TRAIT
    # 8: INITIAL SAMPLE SIZE
    # 9: REPLICATION SAMPLE SIZE
    # 10: REGION
    # 11: CHR_ID
    # 12: CHR_POS
    # 13: REPORTED GENE(S)
    # 14: MAPPED_GENE
    # 15: UPSTREAM_GENE_ID
    # 16: DOWNSTREAM_GENE_ID
    # 17: SNP_GENE_IDS
    # 18: UPSTREAM_GENE_DISTANCE
    # 19: DOWNSTREAM_GENE_DISTANCE
    # 20: STRONGEST SNP-RISK ALLELE
    # 21: SNPS
    # 22: MERGED
    # 23: SNP_ID_CURRENT
    # 24: CONTEXT
    # 25: INTERGENIC
    # 26: RISK ALLELE FREQUENCY
    # 27: P-VALUE
    # 28: PVALUE_MLOG
    # 29: P-VALUE (TEXT)
    # 30: OR or BETA
    # 31: 95% CI (TEXT)
    # 32: PLATFORM [SNPS PASSING QC]
    # 33: CNV
    # 34: MAPPED_TRAIT
    # 35: MAPPED_TRAIT_URI
    # 36: STUDY ACCESSION
    symregex = re.compile(r' ?[-,;] ?')
    for row in tsvreader:
      ct += 1
      if len(row) < 14: continue
      symstr = row[14]
      if symstr == 'NR': continue
      symlist = symregex.split(symstr)
      for sym in symlist:
        if sym in notfnd:
          continue
        targets = dba.find_targets({'sym': sym})
        if not targets:
          notfnd.add(sym)
          logger.warn("Symbol {} not found".format(sym))
          continue
        for t in targets:
          p = t['components']['protein'][0]
          tmark[t['id']] = True
          try:
            pval = float(row[27])
          except:
            pval = None
          #outlist.append( [t['id'], p['sym'], p['name'], p['description'], t['fam'], t['tdl'], p['geneid'], p['uniprot'], row[6], row[1], row[7], row[21], row[26] ] )
          rv = dba.ins_phenotype({'protein_id': p['id'], 'ptype': 'GWAS Catalog', 'trait': row[7], 'pmid': row[1], 'snps': row[21], 'p_value': pval})
          if not rv:
            dba_err_ct += 1
            continue
          pt_ct += 1
      pbar.update(ct)
  pbar.finish()
  print "{} lines processed.".format(ct)
  print "Loaded {} GWAS phenotypes for {} targets".format(pt_ct, len(tmark.keys()))
  if notfnd:
    print "No target found for {} symbols. See logfile {} for details.".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

  # header = ['TCRD ID', 'HGNC Sym', 'Name', 'Description', 'IDG Family', 'TDL', 'NCBI Gene ID', 'UniProt', 'GWAS Study', 'PubMed ID', 'Disease/Trait', 'SNP(s)', 'p-value']
  # with open(OUTFILE, 'wb') as csvout:
  #   csvwriter = csv.writer(csvout, quotechar='"', quoting=csv.QUOTE_MINIMAL)
  #   csvwriter.writerow(header)
  #   for outrow in outlist:
  #     csvwriter.writerow(outrow)


if __name__ == '__main__':
  print "\n{} (v{}) [{}]:".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  start_time = time.time()
  load(args)
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))
