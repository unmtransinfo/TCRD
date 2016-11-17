#!/usr/bin/env python
# Time-stamp: <2016-11-16 16:44:12 smathias>
"""Load GWAS Catalog phenotype data into TCRD from TSV file.

Usage:
    load-GWASCatalog.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-GWASCatalog.py -? | --help

Options:
  -h --dbhost DBHOST   : MySQL database host name [default: localhost]
  -n --dbname DBNAME   : MySQL database name [default: tcrd]
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
__copyright__ = "Copyright 2015-2016, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.0.0"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import logging
import csv
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
DBHOST = 'localhost'
DBPORT = 3306
DBNAME = 'tcrdev'
# File description is here:
# http://www.ebi.ac.uk/gwas/docs/fileheaders
# Get file here:
# https://www.ebi.ac.uk/gwas/docs/downloads
INFILE = '/home/smathias/TCRD/data/EBI/gwas_catalog_v1.0.1-studies_r2016-11-13.tsv'
OUTFILE = 'tcrd4logs/TCRDv4-GWAS_Mapping.csv'

def main():
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

  # DBAdaptor uses same logger as main()
  dba_params = {'dbhost': args['--dbhost'], 'dbname': args['--dbname'], 'logger_name': __name__}
  dba = DBAdaptor(dba_params)
  dbi = dba.get_dbinfo()
  logger.info("Connected to TCRD database %s (schema ver %s; data ver %s)", args['--dbname'], dbi['schema_ver'], dbi['data_ver'])
  if not args['--quiet']:
    print "\n%s (v%s) [%s]:" % (PROGRAM, __version__, time.strftime("%c"))
    print "\nConnected to TCRD database %s (schema ver %s; data ver %s)" % (args['--dbname'], dbi['schema_ver'], dbi['data_ver'])

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'GWAS Catalog', 'source': 'File %s from http://www.ebi.ac.uk/gwas/docs/downloads'%os.path.basename(INFILE), 'app': PROGRAM, 'app_version': __version__, 'columns_touched': "phenotype.* where ptype is 'GWAS Catalog'"} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % dba_logfile
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'phenotype', 'where_clause': "ptype = 'GWAS Catalog'"})
  if not rv:
    print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
    sys.exit(1)
  
  line_ct = wcl(INFILE)
  line_ct -= 1 
  if not args['--quiet']:
    print '\nProcessing %d lines from input file %s' % (line_ct, INFILE)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start()
  outlist = []
  with open(INFILE, 'rU') as tsvfile:
    tsvreader = csv.reader(tsvfile, delimiter='\t')
    header = tsvreader.next() # skip header line
    ct = 0
    notfnd = []
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
    for row in tsvreader:
      ct += 1
      if len(row) < 14: continue
      syms = row[14]
      if syms == 'NR': continue
      for sym in syms.split(','):
        targets = dba.find_targets({'sym': sym})
        if not targets:
          notfnd.append(sym)
          continue
        for t in targets:
          p = t['components']['protein'][0]
          tmark[t['id']] = True
          try:
            pval = float(row[27])
          except:
            pval = None
          outlist.append( [t['id'], p['sym'], p['name'], p['description'], t['idgfam'], t['tdl'], p['geneid'], p['uniprot'], row[6], row[1], row[7], row[21], row[26] ] )
          rv = dba.ins_phenotype({'protein_id': p['id'], 'ptype': 'GWAS Catalog', 'trait': row[7], 'pmid': row[1], 'snps': row[21], 'p_value': pval})
          if not rv:
            dba_err_ct += 1
            continue
          pt_ct += 1
      pbar.update(ct)
  pbar.finish()

  print "%d lines processed." % ct
  print "  Found %d GWAS phenotypes for %d targets" % (pt_ct, len(tmark.keys()))
  if notfnd:
    print "No target found for %d symbols" % len(notfnd)
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)

  header = ['TCRD ID', 'HGNC Sym', 'Name', 'Description', 'IDG Family', 'TDL', 'NCBI Gene ID', 'UniProt', 'GWAS Study', 'PubMed ID', 'Disease/Trait', 'SNP(s)', 'p-value']
  with open(OUTFILE, 'wb') as csvout:
    csvwriter = csv.writer(csvout, quotechar='"', quoting=csv.QUOTE_MINIMAL)
    csvwriter.writerow(header)
    for outrow in outlist:
      csvwriter.writerow(outrow)
  
  print "\n%s: Done." % PROGRAM
  print

def wcl(fname):
  with open(fname) as f:
    for i, l in enumerate(f):
      pass
  return i + 1

if __name__ == '__main__':
    main()








