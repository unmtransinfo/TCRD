#!/usr/bin/env python
# Time-stamp: <2019-04-16 14:50:52 smathias>
"""Load Expression Atlas disease associations into TCRD from TSV file.

Usage:
    load-ExpressionAtlas-Diseases.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-ExpressionAtlas-Diseases.py -? | --help

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
__copyright__ = "Copyright 2016-2019, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.2.0"

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
# To generate the input file:
# cd <TCRD ROOT>/data/ExpressionAtlas
# wget ftp://ftp.ebi.ac.uk/pub/databases/microarray/data/atlas/experiments/atlas-latest-data.tar.gz
# tar xf atlas-latest-data.tar.gz
# ./process.R
INPUT_FILE = '../data/ExpressionAtlas/disease_assoc_human_do_uniq.tsv'

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
  dataset_id = dba.ins_dataset( {'name': 'Expression Atlas', 'source': 'IDG-KMC generated data at UNM.', 'app': PROGRAM, 'app_version': __version__, 'url': 'https://www.ebi.ac.uk/gxa/', 'comment': 'Disease associations are derived from files from ftp://ftp.ebi.ac.uk/pub/databases/microarray/data/atlas/experiments/atlas-latest-data.tar.gz'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'disease', 'where_clause': "dtype = 'Expression Atlas'"})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)
  
  line_ct = slmf.wcl(INPUT_FILE)
  if not args['--quiet']:
    print "\nProcessing {} lines in file {}".format(line_ct, INPUT_FILE)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  with open(INPUT_FILE, 'rU') as tsv:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    tsvreader = csv.reader(tsv, delimiter='\t')
    header = tsvreader.next() # skip header line
    ct = 0
    k2pids = {}
    pmark = {}
    notfnd = set()
    dis_ct = 0
    dba_err_ct = 0
    for row in tsvreader:
      # 0: "Gene ID"
      # 1: "DOID"
      # 2: "Gene Name"
      # 3: "log2foldchange"
      # 4: "p-value"
      # 5: "disease"
      # 6: "experiment_id"
      # 7: "contrast_id"
      ct += 1
      sym = row[2]
      ensg = row[0]
      k = "%s|%s"%(sym,ensg)
      if k in k2pids:
        # we've already found it
        pids = k2pids[k]
      elif k in notfnd:
        # we've already not found it
          continue
      else:
        targets = dba.find_targets({'sym': sym}, idg = False)
        if not targets:
          targets = dba.find_targets_by_xref({'xtype': 'ENSG', 'value': ensg})
        if not targets:
          notfnd.add(k)
          logger.warn("No target found for {}".format(k))
          continue
        pids = []
        for t in targets:
          p = t['components']['protein'][0]
          pmark[p['id']] = True
          pids.append(p['id'])
        k2pids[k] = pids # save this mapping so we only lookup each target once
      for pid in pids:
        rv = dba.ins_disease( {'protein_id': pid, 'dtype': 'Expression Atlas', 'name': row[5],
                               'did': row[1], 'log2foldchange': "%.3f"%float(row[3]),
                               'pvalue': row[4]} )
        if not rv:
          dba_err_ct += 1
          continue
        dis_ct += 1
      pbar.update(ct)
  pbar.finish()
  print "{} lines processed.".format(ct)
  print "Loaded {} new disease rows for {} proteins.".format(dis_ct, len(pmark))
  if notfnd:
    print "No target found for {} symbols/ensgs. See logfile {} for details.".format(len(notfnd), logfile)
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
