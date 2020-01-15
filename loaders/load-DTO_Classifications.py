#!/usr/bin/env python
# Time-stamp: <2019-10-17 11:48:12 smathias>
"""Load DTO IDs and classifications into TCRD from CSV files.

Usage:
    load-DTO.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-DTO.py --help

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

import os,sys,time,re
from docopt import docopt
from TCRDMP import DBAdaptor
import csv
import logging
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = 'tcrd6logs/'
LOGFILE = LOGDIR + '%s.log'%PROGRAM
MAPPING_FILE = '../data/UMiami/DTO2UniProt_DTOv2.csv'
CLASS_FILE = '../data/UMiami/Final_ProteomeClassification_Sep232019.csv'
SRC_FILES = [os.path.basename(MAPPING_FILE),
             os.path.basename(CLASS_FILE)]

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
  dataset_id = dba.ins_dataset( {'name': 'Drug Target Ontology IDs and Classifications', 'source': 'Files %s from Schurer Group'%(", ".join(SRC_FILES)), 'app': PROGRAM, 'app_version': __version__, 'url': 'http://drugtargetontology.org/'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'protein', 'column_name': 'dtoid'},
            {'dataset_id': dataset_id, 'table_name': 'protein', 'column_name': 'dtoclass'} ]
            #{'dataset_id': dataset_id, 'table_name': 'dto'} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  
  line_ct = slmf.wcl(MAPPING_FILE)
  if not args['--quiet']:
    print "\nProcessing {} lines in file {}".format(line_ct, MAPPING_FILE)
  logger.info("Processing {} input lines in file {}".format(line_ct, MAPPING_FILE))
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  up2dto = {}
  up2pid = {}
  ct = 0
  with open(MAPPING_FILE, 'rU') as csvfile:
    csvreader = csv.reader(csvfile)
    header = csvreader.next() # skip header line
    ct += 1
    upd_ct = 0
    notfnd = set()
    dba_err_ct = 0
    for row in csvreader:
      ct += 1
      dtoid = row[0]
      up = row[1]
      logger.info("Searching for UniProt: {}".format(up))
      targets = dba.find_targets({'uniprot': up})
      if not targets:
        notfnd.add(up)
        continue
      t = targets[0]
      pid = t['components']['protein'][0]['id']
      rv = dba.upd_protein(pid, 'dtoid', dtoid)
      if rv:
        upd_ct += 1
        up2dto[up] = dtoid
        up2pid[up] = pid
      else:
        dba_err_ct += 1
      pbar.update(ct)
  pbar.finish()
  for up in notfnd:
    logger.warn("No target found for UniProt: {}".format(up))
  print "{} lines processed.".format(ct)
  print "  Updated {} protein.dtoid values".format(upd_ct)
  print "Got {} UniProt to DTO mappings for TCRD targets".format(len(up2dto))
  print "Got {} UniProt to Protein ID mappings for TCRD targets".format(len(up2pid))
  if notfnd:
    print "WARNING: No target found for {} UniProts. See logfile {} for details.".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

  # Classifications
  line_ct = slmf.wcl(CLASS_FILE)
  if not args['--quiet']:
    print "\nProcessing {} lines in file {}".format(line_ct, CLASS_FILE)
  logger.info("Processing {} input lines in file {}".format(line_ct, CLASS_FILE))
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  ct = 0
  dto_mark = {}
  with open(CLASS_FILE) as csvfile:
    csvreader = csv.reader(csvfile)
    header = csvreader.next() # skip header line
    ct += 1
    upd_ct = 0
    notfnd = set()
    dba_err_ct = 0
    for row in csvreader:
      ct += 1
      up = row[0]
      dto_class = row[1]
      if up not in up2pid:
        notfnd.add(up)
        continue
      pid = up2pid[up]
      rv = dba.upd_protein(pid, 'dtoclass', dto_class)
      if rv:
        upd_ct += 1
      else:
        dba_err_ct += 1
      # if dto_class in dto_mark:
      #   # we've already loaded this term/tree
      #   continue
      # term_tree = extract_tree(row)
      
      # rv = dba.ins_dto({'id': dtoid, 'name': dtoname, 'parent': leaf_term_parent_id})
      # if rv:
      #   dto_mark[dtoid] = True
      # else:
      #   dba_err_ct += 1
    pbar.update(ct)
  pbar.finish()
  for up in notfnd:
    logger.warn("UniProt {} not in map.".format(up))
  print "{} lines processed.".format(ct)
  print "  Updated {} protein.dtoclass values".format(upd_ct)
  if notfnd:
    print "WARNING: Got {} unmapped UniProts. See logfile {} for details.".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

def extract_tree(row):
  terms = list(reversed([t for t in row[2:] if t != '']))
  return terms


if __name__ == '__main__':
  print "\n{} (v{}) [{}]:".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  start_time = time.time()
  load(args)
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))
