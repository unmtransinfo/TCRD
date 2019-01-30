#!/usr/bin/env python
# Time-stamp: <2019-01-08 15:36:31 smathias>
"""Load HGNC annotations for TCRD targets from downloaded TSV file.

Usage:
    load-HGNC.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-HGNC.py -h | --help

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
__copyright__ = "Copyright 2014-2019, Steve Mathias"
__license__ = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__ = "3.0.0"

import os,sys,time
from docopt import docopt
from TCRDMP import DBAdaptor
import logging
import csv
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd6logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
HGNC_TSV_FILE = '../data/HGNC/HGNC_20190104.tsv'
SHELF_FILE = '%s/load-HGNC.db' % LOGDIR

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
  dataset_id = dba.ins_dataset( {'name': 'HGNC', 'source': 'Custom download file from https://www.genenames.org/download/custom/', 'app': PROGRAM, 'app_version': __version__, 'url': 'http://www.genenames.org/', 'comments': 'File downloaded with the following column data: HGNC ID Approved symbol Approved name   Status  UniProt ID NCBI Gene ID    Mouse genome database ID'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile {} for details.".format(logfile)
    sys.exit(1)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'protein', 'column_name': 'sym', 'comment': "This is only updated with HGNC data if data from UniProt is absent."},
            {'dataset_id': dataset_id, 'table_name': 'protein', 'column_name': 'geneid', 'comment': "This is only updated with HGNC data if data from UniProt is absent."},
            {'dataset_id': dataset_id, 'table_name': 'xref', 'where_clause': "dataset_id = %d"%dataset_id} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    if not rv:
      print "WARNING: Error inserting provenance. See logfile {} for details.".format(logfile)
      sys.exit(1)

  line_ct = slmf.wcl(HGNC_TSV_FILE)
  if not args['--quiet']:
    print "\nProcessing {} lines in file {}".format(line_ct, HGNC_TSV_FILE)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start()
  ct = 0
  tmark = {}
  hgnc_ct = 0
  mgi_ct = 0
  sym_ct = 0
  symdiscr_ct = 0
  geneid_ct = 0
  geneiddiscr_ct = 0
  nf_ct = 0
  db_err_ct = 0
  with open(HGNC_TSV_FILE, 'rU') as ifh:
    tsvreader = csv.reader(ifh, delimiter='\t')
    header = tsvreader.next() # skip header line
    ct += 1
    for row in tsvreader:
      # 0: HGNC ID
      # 1: Approved symbol
      # 2: Approved name
      # 3: Status
      # 4: UniProt ID
      # 5: NCBI Gene ID
      # 6: Mouse genome database ID
      ct += 1
      pbar.update(ct)
      sym = row[1]
      geneid = row[5]
      up = row[4]
      targets = dba.find_targets({'sym': sym})
      if not targets:
        targets = dba.find_targets({'geneid': geneid})
      if not targets:
        targets = dba.find_targets({'uniprot': up})
      if not targets:
        nf_ct += 1
        #logger.warn("No target found for {}|{}|{}".format(sym, geneid, up))
        continue
      for t in targets:
        p = t['components']['protein'][0]
        pid = p['id']
        tmark[pid] = True
        # HGNC xref
        rv = dba.ins_xref({'protein_id': pid, 'xtype': 'HGNC',
                           'dataset_id': dataset_id, 'value': row[0]})
        if rv:
          hgnc_ct += 1
        else:
          db_err_ct += 1
        # MGI xref
        rv = dba.ins_xref({'protein_id': pid, 'xtype': 'MGI ID',
                           'dataset_id': dataset_id, 'value': row[6]})
        if rv:
          mgi_ct += 1
        else:
          db_err_ct += 1
        # Add missing syms
        if p['sym'] == None:
          rv = dba.upd_protein(pid, 'sym', sym)
          if rv:
            logger.info("Inserted new sym {} for protein {}, {}".format(sym, pid, p['uniprot']))
            sym_ct += 1
          else:
            db_err_ct += 1
        else:
          # Check for symbol discrepancies
          if p['sym'] != sym:
            logger.warn("Symbol discrepancy: UniProt=%s, HGNC=%s" % (p['sym'], sym))
            symdiscr_ct += 1
        if geneid:
          # Add missing geneids
          if p['geneid'] == None:
            rv = dba.upd_protein(pid, 'geneid', geneid)
            if rv:
              logger.info("Inserted new geneid {} for protein {}, {}".format(geneid, pid, p['uniprot']))
              geneid_ct += 1
            else:
              db_err_ct += 1
          else:
            # Check for geneid discrepancies
            if p['geneid'] != int(geneid):
              logger.warn("GeneID discrepancy: UniProt={}, HGNC={}".format(p['geneid'], geneid))
              geneiddiscr_ct += 1
  pbar.finish()
  print "Processed {} lines - {} targets annotated.".format(ct, len(tmark))
  print "No target found for {} lines.".format(nf_ct)
  print "  Inserted {} HGNC ID xrefs".format(hgnc_ct)
  print "  Inserted {} MGI ID xrefs".format(mgi_ct)
  if sym_ct > 0:
    print "  Added {} new HGNC symbols".format(sym_ct)
  if symdiscr_ct > 0:
    print "WARNING: {} discrepant HGNC symbols. See logfile {} for details".format(symdiscr_ct, logfile)
  if geneid_ct > 0:
    print "  Added {} new NCBI Gene IDs".format(geneid_ct)
  if geneiddiscr_ct > 0:
    print "WARNING: {} discrepant NCBI Gene IDs. See logfile {} for details".format(geneiddiscr_ct, logfile)
  if db_err_ct > 0:
    print "WARNNING: {} DB errors occurred. See logfile {} for details.".format(db_err_ct, logfile)


if __name__ == '__main__':
  print "\n{} (v{}) [{}]:".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  start_time = time.time()
  load(args)
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))
