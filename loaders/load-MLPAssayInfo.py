#!/usr/bin/env python
# Time-stamp: <2017-01-13 12:12:28 smathias>
"""Load mlp_assay_infos into TCRD from CSV files.

Usage:
    load-MLPAssayInfos.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
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
import requests
from bs4 import BeautifulSoup
import cPickle as pickle
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
LOGFILE = './%s.log'%PROGRAM
AIDGI_FILE = '../data/PubChem/entrez_assay_summ_mlp_tgt.csv'
ASSAYS_FILE = '../data/PubChem/entrez_assay_summ_mlp.csv'
EFETCH_PROTEIN_URL = "http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=protein&rettype=xml&id="
T2AID_PICKLE = 'tcrd4logs/Target2PubChemMLPAIDs.p'

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

  dba_params = {'dbhost': args['--dbhost'], 'dbname': args['--dbname'], 'logger_name': __name__}
  dba = DBAdaptor(dba_params)
  dbi = dba.get_dbinfo()
  logger.info("Connected to TCRD database %s (schema ver %s; data ver %s)", args['--dbname'], dbi['schema_ver'], dbi['data_ver'])
  if not args['--quiet']:
    print "\n%s (v%s) [%s]:" % (PROGRAM, __version__, time.strftime("%c"))
    print "\nConnected to TCRD database %s (schema ver %s; data ver %s)" % (args['--dbname'], dbi['schema_ver'], dbi['data_ver'])

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'MLP Assay Info', 'source': 'IDG-KMC generated data by Jeremy Yang at UNM.', 'app': PROGRAM, 'app_version': __version__, 'comments': "This data is generated at UNM from PubChem and EUtils data. It contains details about targets studied in assays that were part of NIH's Molecular Libraries Program."} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': 3, 'table_name': 'mlp_assay_info'})
  if not rv:
    print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
    sys.exit(1)

  if os.path.isfile(T2AID_PICKLE):
    t2aid = pickle.load( open(T2AID_PICKLE, 'rb'))
    act = 0
    for tid in t2aid.keys():
      for aid in t2aid[tid]:
        act += 1
    print "\n%d targets have link(s) to %d PubChem MLP assay(s)" % (len(t2aid.keys()), act)
  else:
    start_time = time.time()
    pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
    line_ct = wcl(AIDGI_FILE)
    t2aid = {}
    if not args['--quiet']:
      print "\nProcessing %d lines in file %s" % (line_ct, AIDGI_FILE)
    with open(AIDGI_FILE, 'rU') as csvfile:
      pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start()
      csvreader = csv.reader(csvfile)
      ct = 0
      skip_ct = 0
      fndgi_ct = 0
      fndpl_ct = 0
      notfnd = []
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
    elapsed = time.time() - start_time
    pickle.dump(t2aid, open(T2AID_PICKLE, "wb"))
    print "\n%d rows processed. Elapsed time: %s" % (ct, secs2str(elapsed))
    print "  Skipped %d non-huamn assay rows" % skip_ct
    print "  %d assays linked to TCRD targets" % assay_ct
    print "    %d linked by GI; %d linked via EUtils" % (fndgi_ct, fndpl_ct)
    print "  No target found for %d GIs" % len(notfnd)
    with open('GIsNotFound.csv', 'wb') as csvfile:
      csvwriter = csv.writer(csvfile)
      for gi in notfnd:
        csvwriter.writerow([gi])
    print "  %d distinct targets have PubChem MLP assay link(s)" % len(t2aid.keys())

  assay_info = {}
  start_time = time.time()
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  line_ct = wcl(ASSAYS_FILE)
  if not args['--quiet']:
    print "\nProcessing %d rows in file %s" % (line_ct, ASSAYS_FILE)
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
  print "Got assay info for %d assays. Elapsed time: %s" % (len(assay_info), secs2str(elapsed))

  start_time = time.time()
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  tct = len(t2aid.keys())
  if not args['--quiet']:
    print "\nLoading MLP Assay Info for %d targets" % tct
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
  elapsed = time.time() - start_time
  print "\n%d targets processed. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "  Inserted %d new mlp_assay_info rows" % mai_ct
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)
  
  if not args['--quiet']:
    print "\n%s: Done.\n" % PROGRAM


def wcl(fname):
  with open(fname) as f:
    for i, l in enumerate(f):
      pass
  return i + 1

def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])

if __name__ == '__main__':
    main()
