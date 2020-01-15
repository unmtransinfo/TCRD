#!/usr/bin/env python
# Time-stamp: <2019-08-28 11:44:29 smathias>
"""Load Is Transcription Factor tdl_infos into TCRD from CSV file.

Usage:
    load-TF_TDLInfos.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>] [--pastid=<int>]
    load-TF_TDLInfos.py -h | --help

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
  -p --pastid PASTID   : TCRD target id to start at (for restarting frozen run)
  -q --quiet           : set output verbosity to minimal level
  -d --debug           : turn on debugging output
  -? --help            : print this message and exit 
"""
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2018-2019, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.0.0"

import os,sys,time
from docopt import docopt
from TCRDMP import DBAdaptor
import urllib
import csv
import logging
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = 'tcrd6logs/'
LOGFILE = LOGDIR + '%s.log'%PROGRAM
DOWNLOAD_DIR = '../data/UToronto/'
BASE_URL = 'http://humantfs.ccbr.utoronto.ca/download/v_1.01/'
FILENAME = 'DatabaseExtract_v_1.01.csv'

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
  dataset_id = dba.ins_dataset( {'name': 'Transcription Factor Flags', 'source': BASE_URL+FILENAME, 'app': PROGRAM, 'app_version': __version__, 'url': 'http://humantfs.ccbr.utoronto.ca/'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'tdl_info', 'where_clause': "itype = 'Is Transcription Factor'"})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  TDLs = {'Tdark': 0, 'Tbio': 0, 'Tchem': 0, 'Tclin': 0}

  ifn = DOWNLOAD_DIR + FILENAME
  line_ct = slmf.wcl(ifn)
  if not args['--quiet']:
    print "\nProcessing {} lines in input file {}".format(line_ct, ifn)
  with open(ifn, 'rU') as ifh:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    csvreader = csv.reader(ifh)
    header = csvreader.next() # skip header line
    ct = 0
    ti_ct = 0
    skip_ct = 0
    notfnd = set()
    dba_err_ct = 0
    for row in csvreader:
      # 0 Ensembl ID
      # 1 HGNC symbol
      # 2 DBD
      # 3 Is TF?
      # 4 TF assessment
      # 5 Binding mode,Motif status
      # 6 Final Notes
      # 7 Final Comments
      # 8 Interpro ID(s)
      # 9 EntrezGene ID
      # 10 EntrezGene Description
      # 11 PDB ID
      # 12 TF tested by HT-SELEX?
      # 13 TF tested by PBM?
      # 14 Conditional Binding Requirements
      # 15 Original Comments
      # 16 Vaquerizas 2009 classification
      # 17 CisBP considers it a TF?
      # 18 TFCat classification
      # 19 Is a GO TF?
      # 20 Initial assessment
      # 21 Curator 1
      # 22 Curator 2
      # 23 TFclass considers
      ct += 1
      if row[3] != 'Yes':
        skip_ct += 1
        continue
      sym = row[1]
      targets = dba.find_targets({'sym': sym})
      if not targets:
        gid = row[9]
        if gid != 'None' and not gid.startswith('IPR'):
          targets = dba.find_targets({'geneid': gid})
      if not targets:
        ensg = row[0]
        targets = dba.find_targets_by_xref({'xtype': 'Ensembl', 'value': ensg})
      if not targets:
        k = "%s|%s|%s"%(sym,gid,ensg)
        notfnd.add(k)
        continue
      t = targets[0]
      TDLs[t['tdl']] += 1
      pid = t['components']['protein'][0]['id']
      rv = dba.ins_tdl_info({'protein_id': pid, 'itype': 'Is Transcription Factor', 
                             'boolean_value': 1} )
      if rv:
        ti_ct += 1
      else:
        dba_err_ct += 1
      pbar.update(ct)
  pbar.finish()
  for k in notfnd:
    logger.warn("No target found for {}".format(k))
  print "\n{} lines processed.".format(ct)
  print "  Inserted {} new 'Is Transcription Factor' tdl_infos".format(ti_ct)
  print "  Skipped {} non-TF lines".format(skip_ct)
  if notfnd:
    print "No target found for {} symbols/geneids/ENSGs. See logfile {} for details.".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)
  for tdl in ['Tclin', 'Tchem', 'Tbio', 'Tdark']:
    print "%s: %d" % (tdl, TDLs[tdl])


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
