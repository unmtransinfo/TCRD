#!/usr/bin/env python
# Time-stamp: <2018-02-05 11:35:14 smathias>
""" Load Drug Central data into TCRD from TSV files.

Usage:
    load-DrugCentral.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-DrugCentral.py -h | --help

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
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd5logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
FILES_DATE = '08302017'
TCLIN_FILE = '../data/DrugCentral/tclin_%s.tsv'%FILES_DATE
TCHEM_FILE = '../data/DrugCentral/tchem_drugs_%s.tsv'%FILES_DATE
DRUGINFO_FILE = '../data/DrugCentral/drug_info_%s.tsv'%FILES_DATE
DRUGIND_FILE = '../data/DrugCentral/drug_indications_%s.tsv'%FILES_DATE
SRC_FILES = [os.path.basename(TCLIN_FILE),
             os.path.basename(TCHEM_FILE),
             os.path.basename(DRUGINFO_FILE),
             os.path.basename(DRUGIND_FILE)]

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

  # DBAdaptor uses same logger as main()
  dba_params = {'dbhost': args['--dbhost'], 'dbname': args['--dbname'], 'logger_name': __name__}
  dba = DBAdaptor(dba_params)
  dbi = dba.get_dbinfo()
  logger.info("Connected to TCRD database {} (schema ver {}; data ver {})".format(args['--dbname'], dbi['schema_ver'], dbi['data_ver']))
  if not args['--quiet']:
    print "\nConnected to TCRD database {} (schema ver {}; data ver {})".format(args['--dbname'], dbi['schema_ver'], dbi['data_ver'])

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'Drug Central', 'source': "Drug Central files (%s) obtained directly from Oleg Ursu"%", ".join(SRC_FILES), 'app': PROGRAM, 'app_version': __version__, 'url': 'http://drugcentral.org/'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset. See logfile {} for details.".format(logfile)
    sys.exit(1)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'drug_activity'},
            {'dataset_id': dataset_id, 'table_name': 'disease', 'where_clause': "dtype = 'DrugCentral Indication'"} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    if not rv:
      print "WARNING: Error inserting provenance. See logfile {} for details.".format(logfile)
      sys.exit(1)
  
  # First get drug info fields
  infos = {}
  line_ct = slmf.wcl(DRUGINFO_FILE)
  if not args['--quiet']:
    print "\nProcessing {} input lines in file {}".format(line_ct, DRUGINFO_FILE)
  with open(DRUGINFO_FILE, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    dct = 0
    for row in tsvreader:
      ct += 1
      if row[0].startswith('#'): continue
      infos[row[0]] = row[1].replace("\n", '')
  print "{} input lines processed.".format(ct)
  print "Saved {} keys in infos map".format(len(infos.keys()))

  #
  # MOA activities
  #
  drug2targets = {}
  line_ct = slmf.wcl(TCLIN_FILE)
  line_ct -= 1
  if not args['--quiet']:
    print "\nProcessing {} lines from DrugDB MOA activities file {}".format(line_ct, TCLIN_FILE)
  with open(TCLIN_FILE, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    header = tsvreader.next() # skip header line
    # uniprot swissprot       drug_name       act_value       act_type        action_type     source_name     reference       smiles  ChEMBL_Id
    ct = 0
    da_ct = 0
    ti_ct = 0
    notfnd = []
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
      up = row[0]
      sp = row[1]
      drug = row[2]
      targets = dba.find_targets({'uniprot': up})
      if not targets:
        targets = dba.find_targets({'name': sp})
        if not targets:
          notfnd.append(up)
          continue
      t = targets[0]
      tid = t['id']
      if drug in drug2targets:
        drug2targets[drug].append(tid)
      else:
         drug2targets[drug] = [tid]
      init = {'target_id': tid, 'drug': drug, 'has_moa': 1, 'source': row[5]}
      if row[3]:
        init['act_value'] = row[3]
      if row[4]:
        init['act_type'] = row[4]
      if row[5]:
        init['action_type'] = row[5]
      if row[6]:
        init['source'] = row[6]
      if row[7]:
        init['reference'] = row[7]
      if row[8]:
        init['smiles'] = row[8]
      if row[9]:
        init['cmpd_chemblid'] = row[9]
      if drug in infos:
        init['nlm_drug_info'] = infos[drug]
      rv = dba.ins_drug_activity(init)
      if rv:
        da_ct += 1
      else:
        dba_err_ct += 1
  print "{} DrugCentral Tclin rows processed.".format(ct)
  print "  Inserted {} new drug_activity rows".format(da_ct)
  if len(notfnd) > 0:
    print "WARNNING: {} Uniprot/Swissprot Accessions NOT FOUND in TCRD:".format(len(notfnd))
    for up in notfnd:
      print up
  if dba_err_ct > 0:
    print "WARNNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)
  
  #
  # Non-MOA activities
  #
  line_ct = slmf.wcl(TCHEM_FILE)
  line_ct -= 1
  if not args['--quiet']:
    print "\nProcessing {} lines from Non-MOA activities file {}".format(line_ct, TCHEM_FILE)
  with open(TCHEM_FILE, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    header = tsvreader.next() # skip header line
    # uniprot swissprot       drug_name       act_value       act_type        action_type     source_name     reference       smiles  ChEMBL_Id
    ct = 0
    da_ct = 0
    ti_ct = 0
    notfnd = []
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
      up = row[0]
      sp = row[1]
      drug = row[2]
      targets = dba.find_targets({'uniprot': up})
      if not targets:
        targets = dba.find_targets({'name': sp})
        if not targets:
          notfnd.append(up)
          continue
      t = targets[0]
      tid = t['id']
      if drug in drug2targets:
        drug2targets[drug].append(tid)
      else:
         drug2targets[drug] = [tid]
      init = {'target_id': tid, 'drug': drug, 'has_moa': 0, 'source': row[5]}
      if row[3]:
        init['act_value'] = row[3]
      if row[4]:
        init['act_type'] = row[4]
      if row[5]:
        init['action_type'] = row[5]
      if row[6]:
        init['source'] = row[6]
      if row[7]:
        init['reference'] = row[7]
      if row[8]:
        init['smiles'] = row[8]
      if row[9]:
        init['chemblid'] = row[9]
      if drug in infos:
        init['nlm_drug_info'] = infos[drug]
      rv = dba.ins_drug_activity(init)
      if rv:
        da_ct += 1
      else:
        dba_err_ct += 1
  print "{} DrugCentral Tchem rows processed.".format(ct)
  print "  Inserted {} new drug_activity rows".format(da_ct)
  if len(notfnd) > 0:
    print "WARNNING: {} DrugDB Uniprot Accessions NOT FOUND in TCRD:".format(len(notfnd))
    for up in notfnd:
      print up
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

  #
  # Indications (diseases)
  #
  line_ct = slmf.wcl(DRUGIND_FILE)
  line_ct -= 1
  if not args['--quiet']:
    print "\nProcessing {} lines from indications file {}".format(line_ct, DRUGIND_FILE)
  with open(DRUGIND_FILE, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    header = tsvreader.next() # skip header line
    # DRUG_ID DRUG_NAME       INDICATION_FDB  UMLS_CUI        SNOMEDCT_CUI    DOID
    ct = 0
    t2d_ct = 0
    notfnd = {}
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
      drug = row[1]
      if drug not in drug2targets:
        notfnd[drug] = True
        continue
      for tid in drug2targets[drug]:
        rv = dba.ins_disease({'target_id': tid, 'dtype': 'DrugCentral Indication',
                              'name': row[2], 'doid': row[5], 'drug_name': drug})
        if rv:
          t2d_ct += 1
        else:
          dba_err_ct += 1
  print "{} DrugCentral indication rows processed.".format(ct)
  print "  Inserted {} new target2disease rows".format(t2d_ct)
  if len(notfnd.keys()) > 0:
    print "WARNNING: {} drugs NOT FOUND in activity files:".format(len(notfnd))
    #for drug in notfnd:
    #  print drug
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)
    

if __name__ == '__main__':
  print "\n%s (v%s) [%s]:" % (PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if int(args['--debug']):
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  start_time = time.time()
  load(args)
  elapsed = time.time() - start_time
  print "\n%s: Done. Elapsed time: %s\n" % (PROGRAM, slmf.secs2str(elapsed))
