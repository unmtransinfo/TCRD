#!/usr/bin/env python
# Time-stamp: <2018-05-31 10:47:07 smathias>
"""Load IMPC phenotype data into TCRD from CSV file.

Usage:
    load-IMPCPhenotypes.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-IMPCPhenotypes.py -? | --help

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
__version__   = "2.3.0"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import logging
import urllib
import gzip
import csv
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd5logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
# Get from ftp://ftp.ebi.ac.uk/pub/databases/impc/release-*.*/csv/
# ftp://ftp.ebi.ac.uk/pub/databases/impc/release-6.1/csv/ALL_genotype_phenotype.csv.gz
IMPC_VER = '6.1'
DOWNLOAD_DIR = '../data/IMPC/'
BASE_URL = 'ftp://ftp.ebi.ac.uk/pub/databases/impc/release-%s/csv/'%IMPC_VER
IMPC_FILE = 'ALL_genotype_phenotype.csv.gz'

def download(args):
  gzfn = DOWNLOAD_DIR + IMPC_FILE
  if os.path.exists(gzfn):
    os.remove(gzfn)
  fn = gzfn.replace('.gz', '')
  if os.path.exists(fn):
    os.remove(fn)
  if not args['--quiet']:
    print "\nDownloading", BASE_URL + IMPC_FILE
    print "         to", DOWNLOAD_DIR + IMPC_FILE
  urllib.urlretrieve(BASE_URL + IMPC_FILE, DOWNLOAD_DIR + IMPC_FILE)
  if not args['--quiet']:
    print "Uncompressing", gzfn
  ifh = gzip.open(gzfn, 'rb')
  ofh = open(fn, 'wb')
  ofh.write( ifh.read() )
  ifh.close()
  ofh.close()

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
  dataset_id = dba.ins_dataset( {'name': 'IMPC Phenotypes', 'source': "File %s from %s"%(IMPC_FILE, BASE_URL), 'app': PROGRAM, 'app_version': __version__, 'url': '%sREADME'%BASE_URL} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'phenotype', 'where_clause': "ptype = 'IMPC'"},
            {'dataset_id': dataset_id, 'table_name': 'xref', 'where_clause': "dataset_id = %d"%dataset_id} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)
  
  infile = (DOWNLOAD_DIR + IMPC_FILE).replace('.gz', '')
  line_ct = slmf.wcl(infile)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]

  if not args['--quiet']:
    print "\nProcessing {} lines from input file {}".format(line_ct, infile)
  with open(infile, 'rU') as csvfile:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    csvreader = csv.reader(csvfile)
    header = csvreader.next() # skip header line
    ct = 0
    tmark = {}
    pt_ct = 0
    mgixr_ct = 0
    notfnd = set()
    skipped = set()
    dba_err_ct = 0
    # 0: marker_accession_id
    # 1: marker_symbol
    # 2: phenotyping_center
    # 3: colony_id
    # 4: sex
    # 5: zygosity
    # 6: allele_accession_id
    # 7: allele_symbol
    # 8: allele_name
    # 9: strain_accession_id
    # 10: strain_name
    # 11: project_name
    # 12: project_fullname
    # 13: pipeline_name
    # 14: pipeline_stable_id
    # 15: procedure_stable_id
    # 16: procedure_name
    # 17: parameter_stable_id
    # 18: parameter_name
    # 19: top_level_mp_term_id
    # 20: top_level_mp_term_name
    # 21: mp_term_id
    # 22: mp_term_name
    # 23: p_value
    # 24: percentage_change
    # 25: effect_size
    # 26: statistical_method
    # 27: resource_name
    for row in csvreader:
      ct += 1
      sym = row[1].upper()
      if sym in notfnd:
        continue
      if not row[21] and not row[22]:
        # skip data with neither a term_id or term_name (IMPC has some of these)
        skipped.add(tuple(row))
        logger.warn("Row {} has no term_id or term_name".format(row))
        continue
      targets = dba.find_targets({'sym': sym}, idg = False)
      if not targets:
        notfnd.add(sym)
        logger.warn("Symbol {} not found".format(sym))
        continue
      for t in targets:
        tmark[t['id']] = True
        pid = t['components']['protein'][0]['id']
        rv = dba.ins_xref({'protein_id': pid, 'xtype': 'MGI ID', 'dataset_id': dataset_id, 'value': row[0]})
        if rv:
          mgixr_ct += 1
        else:
          dba_err_ct += 1
        if row[23] and row[23] != '':
          try:
            pval = "%.19f"%float(row[23])
          except ValueError:
            print "row: %s" % str(row)
            print "pval: %s" % row[23]
        else:
          pval = None
        rv = dba.ins_phenotype({'protein_id': pid, 'ptype': 'IMPC', 'top_level_term_id': row[19], 'top_level_term_name': row[20], 'term_id': row[21], 'term_name': row[22], 'p_value': pval, 'percentage_change': row[24], 'effect_size': row[25], 'statistical_method': row[26], 'sex': row[4]})
        if rv:
          pt_ct += 1
        else:
          dba_err_ct += 1
      pbar.update(ct)
  pbar.finish()
  print "{} lines processed.".format(ct)
  print "Loaded {} IMPC phenotypes for {} targets".format(pt_ct, len(tmark.keys()))
  print "  Inserted {} new MGI ID xref rows".format(mgixr_ct)
  if notfnd:
    print "No target found for {} gene symbols. See logfile {} for details.".format(len(notfnd), logfile)
  if skipped:
    print "{} lines have no term_id or term_name. See logfile {} for details.".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)


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
  
