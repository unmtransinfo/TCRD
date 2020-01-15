#!/usr/bin/env python
# Time-stamp: <2019-08-21 15:47:59 smathias>
"""
Load LINCS data into TCRD from CSV file.

Usage:
    load-LINCS.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-LINCS.py -h | --help

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
__copyright__ = "Copyright 2019, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "1.0.0"

import os,sys,time
from docopt import docopt
from TCRDMP import DBAdaptor
import csv
import logging
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = 'tcrd6logs/'
LOGFILE = LOGDIR + '%s.log'%PROGRAM
# The input file is exported from Oleg's lincs PostgreSQL database on seaborgium with:
# COPY (SELECT level5_lm.pr_gene_id, level5_lm.zscore, perturbagen.dc_id, perturbagen.canonical_smiles, signature.cell_id FROM level5_lm, perturbagen, signature where level5_lm.sig_id = signature.sig_id and signature.pert_id = perturbagen.pert_id and perturbagen.dc_id is NOT NULL) TO '/tmp/LINCS.csv';
INPUT_FILE = '../data/LINCS.csv'

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
  dataset_id = dba.ins_dataset( {'name': 'LINCS', 'source': "CSV file exported from Oleg Ursu's lincs PostgreSQL database on seaborgium. I do not know the origin of this database at this time.", 'app': PROGRAM, 'app_version': __version__, 'url': 'http://lincsproject.org/LINCS/'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'lincs'})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

  line_ct = slmf.wcl(INPUT_FILE)
  if not args['--quiet']:
    print "\nProcessing {} lines in file {}".format(line_ct, INPUT_FILE)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  ct = 0
  gid2pids = {}
  notfnd = set()
  dba_err_ct = 0
  pmark = {}
  lincs_ct = 0
  with open(INPUT_FILE, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    for row in tsvreader:
      # 0: level5_lm.pr_gene_id
      # 1: level5_lm.zscore
      # 2: perturbagen.dc_id
      # 3: perturbagen.canonical_smiles
      # 4: signature.cell_id
      ct += 1
      gid = row[0]
      if gid in gid2pids:
        # we've already found it
        pids = gid2pids[gid]
      elif gid in notfnd:
        # we've already not found it
        continue
      else:
        # look it up
        targets = dba.find_targets({'geneid': gid}, False)
        if not targets:
          notfnd.add(gid)
          continue
        pids = []
        for t in targets:
          pid = t['components']['protein'][0]['id']
          pids.append(pid)
        gid2pids[gid] = pids # save this mapping so we only lookup each target once
      for pid in pids:
        rv = dba.ins_lincs( {'protein_id': pid, 'cellid': row[4], 'zscore': row[1],
                             'pert_dcid': row[2], 'pert_smiles': row[3]} )
        if not rv:
          dba_err_ct += 1
          continue
        pmark[pid] = True
        lincs_ct += 1
      pbar.update(ct)
  pbar.finish()
  for gid in notfnd:
    logger.warn("No target found for {}".format(gid))
  print "{} lines processed.".format(ct)
  print "Loaded {} new lincs rows for {} proteins.".format(lincs_ct, len(pmark))
  if notfnd:
    print "No target found for {} geneids. See logfile {} for details.".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)


if __name__ == '__main__':
  print "\n{} (v{}) [{}]:".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  start_time = time.time()
  load(args)
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))
