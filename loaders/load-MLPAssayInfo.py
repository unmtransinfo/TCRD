#!/usr/bin/env python
# Time-stamp: <2018-05-31 10:48:02 smathias>
"""Load mlp_assay_infos into TCRD from CSV files.

Usage:
    load-MLPAssayInfos.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-MLPAssayInfos.py -? | --help

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

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import logging
import csv
import requests
from bs4 import BeautifulSoup
import cPickle as pickle
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd5logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
AIDGI_FILE = '../data/PubChem/entrez_assay_summ_mlp_tgt.csv'
ASSAYS_FILE = '../data/PubChem/entrez_assay_summ_mlp.csv'
EFETCH_PROTEIN_URL = "http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=protein&rettype=xml&id="
T2AID_PICKLE = 'tcrd5logs/Target2PubChemMLPAIDs.p'

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
  dataset_id = dba.ins_dataset( {'name': 'MLP Assay Info', 'source': 'IDG-KMC generated data by Jeremy Yang at UNM.', 'app': PROGRAM, 'app_version': __version__, 'comments': "This data is generated at UNM from PubChem and EUtils data. It contains details about targets studied in assays that were part of NIH's Molecular Libraries Program."} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': 3, 'table_name': 'mlp_assay_info'})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

  if os.path.isfile(T2AID_PICKLE):
    t2aid = pickle.load( open(T2AID_PICKLE, 'rb'))
    act = 0
    for tid in t2aid.keys():
      for aid in t2aid[tid]:
        act += 1
    if not args['--debug']:
      print "\n{} targets have link(s) to {} PubChem MLP assay(s)".format(len(t2aid), act)
  else:
    pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
    line_ct = slmf.wcl(AIDGI_FILE)
    t2aid = {}
    if not args['--quiet']:
      print "\nProcessing {} lines in file {}".format(line_ct, AIDGI_FILE)
    with open(AIDGI_FILE, 'rU') as csvfile:
      pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start()
      csvreader = csv.reader(csvfile)
      ct = 0
      skip_ct = 0
      fndgi_ct = 0
      fndpl_ct = 0
      notfnd = set()
      assay_ct = 0
      dba_err_ct = 0
      for row in csvreader:
        # aid, tgt_gi, tgt_species, tgt_name
        #print "[DEBUG]", row
        ct += 1
        if row[2] != 'Homo sapiens':
          skip_ct += 1
          continue
        gi = row[1]
        targets = dba.find_targets_by_xref({'xtype': 'NCBI GI', 'value': gi})
        if targets:
          fndgi_ct += 1
        else:
          url = EFETCH_PROTEIN_URL + gi
          r = requests.get(url)
          if r.status_code == 200:
            soup = BeautifulSoup(r.text, "xml")
            grl = soup.find('Gene-ref_locus')
            if grl:
              sym = grl.text
              targets = dba.find_targets({'sym': sym})
          if targets:
            fndpl_ct += 1
          else:
            notfnd.append(gi)
            logger.warn("No target found for GI {}".format(gi))
            continue
        t = targets[0]
        tid = t['id']
        if tid in t2aid:
          t2aid[tid].append(row[0])
          assay_ct += 1
        else:
          t2aid[tid] = [row[0]]
          assay_ct += 1
        pbar.update(ct)
    pbar.finish()
    pickle.dump(t2aid, open(T2AID_PICKLE, "wb"))
    print "\n{} rows processed.".format(ct)
    print "  {} assays linked to {} TCRD targets".format(assay_ct, len(t2aid))
    print "  Skipped {} non-huamn assay rows".format(skip_ct)
    print "    {} linked by GI; {} linked via EUtils".format(fndgi_ct, fndpl_ct)
    print "  No target found for {} GIs. See logfile {} for details".format(len(notfnd), logfile)

  assay_info = {}
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  line_ct = slmf.wcl(ASSAYS_FILE)
  if not args['--quiet']:
    print "\nProcessing {} rows in file {}".format(line_ct, ASSAYS_FILE)
  with open(ASSAYS_FILE, 'rU') as csvfile:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start()
    csvreader = csv.reader(csvfile)
    ct = 0
    for row in csvreader:
      # ID,ActivityOutcomeMethod,AssayName,SourceName,ModifyDate,DepositDate,ActiveSidCount,InactiveSidCount,InconclusiveSidCount,TotalSidCount,ActiveCidCount,TotalCidCount,ProteinTargetList
      aid = row[0]
      assay_info[aid] = row[1:]
      pbar.update(ct)
  pbar.finish()
  elapsed = time.time() - start_time
  print "Got assay info for {} assays.".format(len(assay_info))

  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  tct = len(t2aid.keys())
  if not args['--quiet']:
    print "\nLoading MLP Assay Info for {} targets".format(tct)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start()
  ct = 0
  ti_ct = 0
  mai_ct = 0
  dba_err_ct = 0
  for tid, aids in t2aid.items():
    ct += 1
    for aid in aids:
      ainfo = assay_info[aid]
      rv = dba.ins_mlp_assay_info({'protein_id': tid, 'aid': aid, 'assay_name': ainfo[1], 'method': ainfo[0], 'active_sids': ainfo[5], 'inactive_sids': ainfo[6], 'iconclusive_sids': ainfo[7], 'total_sids': ainfo[8]})
      if rv:
        mai_ct += 1
      else:
        dba_err_ct += 1
    pbar.update(ct)
  pbar.finish()
  print "\n{} targets processed.".format(ct)
  print "  Inserted {} new mlp_assay_info rows".format(mai_ct)
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
