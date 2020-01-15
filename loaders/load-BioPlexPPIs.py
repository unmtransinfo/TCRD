#!/usr/bin/env python
# Time-stamp: <2019-10-15 09:15:29 smathias>
""" Load BioPlex ppis into TCRD from TSV file.

Usage:
    load-PPIsBioPlex.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-PPIsBioPlex.py -h | --help

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
__copyright__ = "Copyright 2015-2019, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "3.0.0"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import logging
import csv
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd6logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
# http://wren.hms.harvard.edu/bioplex/downloadInteractions.php
# http://bioplex.hms.harvard.edu/data/BioPlex_interactionList_v4a.tsv
# http://bioplex.hms.harvard.edu/data/interactome_update_MonYYYY.tsv
BIOPLEX_FILE = '../data/BioPlex/BioPlex_interactionList_v4a.tsv'
UPD_FILES = ['../data/BioPlex/interactome_update_Dec2015.tsv',
             '../data/BioPlex/interactome_update_May2016.tsv',
             '../data/BioPlex/interactome_update_Aug2016.tsv',
             '../data/BioPlex/interactome_update_Dec2016.tsv',
             '../data/BioPlex/interactome_update_April2017.tsv',
             '../data/BioPlex/interactome_update_Nov2017.tsv']
SRC_FILES = [os.path.basename(BIOPLEX_FILE)] + [os.path.basename(f) for f in UPD_FILES]

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
  dataset_id = dba.ins_dataset( {'name': 'BioPlex Protein-Protein Interactions', 'source': "Files %s from http://wren.hms.harvard.edu/bioplex/downloadInteractions.php"%", ".join(SRC_FILES), 'app': PROGRAM, 'app_version': __version__, 'url': 'http://wren.hms.harvard.edu/bioplex/index.php'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'ppi', 'where_clause': "ppitype = 'BioPlex'"})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)
    
  f = BIOPLEX_FILE
  line_ct = slmf.wcl(f)
  line_ct -= 1
  if not args['--quiet']:
    print "\nProcessing {} lines from BioPlex PPI file {}".format(line_ct, f)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  with open(f, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    header = tsvreader.next() # skip header line
    # GeneA   GeneB   UniprotA        UniprotB        SymbolA SymbolB pW      pNI     pInt
    ct = 0
    ppi_ct = 0
    same12_ct = 0
    k2pid = {}
    notfnd = set()
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
      pbar.update(ct)
      geneid1 = row[0]
      geneid2 = row[1]
      up1 = row[2]
      up2 = row[3]
      sym1 = row[4]
      sym2 = row[5]
      pw = row[6]
      pni = row[7]
      pint = row[8]
      # protein1
      k1 = "%s|%s|%s" % (up1, sym1, geneid1)
      if k1 in k2pid:
        pid1 = k2pid[k1]
      elif k1 in notfnd:
        continue
      else:
        t1 = find_target(dba, k1)
        if not t1:
          notfnd.add(k1)
          continue
        pid1 = t1['components']['protein'][0]['id']
      k2pid[k1] = pid1
      # protein2
      k2 = "%s|%s|%s" % (up2, sym2, geneid2)
      if k2 in k2pid:
        pid2 = k2pid[k2]
      elif k2 in notfnd:
        continue
      else:
        t2 = find_target(dba, k2)
        if not t2:
          notfnd.add(k2)
          continue
        pid2 = t2['components']['protein'][0]['id']
      k2pid[k2] = pid2
      if pid1 == pid2:
        same12_ct += 1
        continue
      # Insert PPI
      rv = dba.ins_ppi( {'ppitype': 'BioPlex','p_int': pint, 'p_ni': pni, 'p_wrong': pw,
                         'protein1_id': pid1, 'protein1_str': k1,
                         'protein2_id': pid2, 'protein2_str': k2} )
      if rv:
        ppi_ct += 1
      else:
        dba_err_ct += 1
  pbar.finish()
  for k in notfnd:
    logger.warn("No target found for: {}".format(k))
  print "{} BioPlex PPI rows processed.".format(ct)
  print "  Inserted {} new ppi rows".format(ppi_ct)
  if same12_ct:
    print "  Skipped {} PPIs involving the same protein".format(same12_ct)
  if notfnd:
    print "  No target found for {} UniProts/Syms/GeneIDs. See logfile {} for details.".format(len(notfnd), logfile) 
  if dba_err_ct > 0:
    print "WARNNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

  for f in UPD_FILES[1:]:
    start_time = time.time()
    line_ct = slmf.wcl(f)
    line_ct -= 1
    if not args['--quiet']:
      print "\nProcessing {} lines from BioPlex PPI update file {}".format(line_ct, f)
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    with open(f, 'rU') as tsv:
      tsvreader = csv.reader(tsv, delimiter='\t')
      header = tsvreader.next() # skip header line
      # plate_num       well_num        db_protein_id   symbol  gene_id bait_symbol     bait_geneid     pWrongID        pNoInt  pInt
      ct = 0
      ppi_ct = 0
      same12_ct = 0
      k2pid = {}
      notfnd = set()
      dba_err_ct = 0
      for row in tsvreader:
        ct += 1
        pbar.update(ct)
        geneid1 = row[6]
        geneid2 = row[4]
        sym1 = row[5]
        sym2 = row[3]
        pw = row[7]
        pni = row[8]
        pint = row[9]
        # protein1
        k1 = "|%s|%s" % (sym1, geneid1)
        if k1 in k2pid:
          pid1 = k2pid[k1]
        elif k1 in notfnd:
          continue
        else:
          t1 = find_target(dba, k1)
          if not t1:
            notfnd.add(k1)
            continue
          pid1 = t1['components']['protein'][0]['id']
          k2pid[k1] = pid1
        # protein2
        k2 = "|%s|%s" % (sym2, geneid2)
        if k2 in k2pid:
          pid2 = k2pid[k2]
        elif k2 in notfnd:
          continue
        else:
          t2 = find_target(dba, k2)
          if not t2:
            notfnd.add(k2)
            continue
          pid2 = t2['components']['protein'][0]['id']
          k2pid[k2] = pid2
        if pid1 == pid2:
          same12_ct += 1
          continue
        # Insert PPI
        rv = dba.ins_ppi( {'ppitype': 'BioPlex','p_int': pint, 'p_ni': pni, 'p_wrong': pw,
                           'protein1_id': pid1, 'protein1_str': k1,
                           'protein2_id': pid2, 'protein2_str': k2} )
        if rv:
          ppi_ct += 1
        else:
          dba_err_ct += 1
    pbar.finish()
    for k in notfnd:
      logger.warn("No target found for: {}".format(k))
    print "{} BioPlex PPI rows processed.".format(ct)
    print "  Inserted {} new ppi rows".format(ppi_ct)
    if same12_ct:
      print "  Skipped {} PPIs involving the same protein".format(same12_ct)
    if notfnd:
      print "  No target found for {} UniProts/Syms/GeneIDs. See logfile {} for details.".format(len(notfnd), logfile) 
    if dba_err_ct > 0:
      print "WARNNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

def find_target(dba, k):
  (up, sym, geneid) = k.split("|")
  targets = False
  if up != '': # No UniProt accessions in update files
    targets = dba.find_targets({'uniprot': up})
  if not targets:
    targets = dba.find_targets({'sym': sym})
  if not targets:
    targets = dba.find_targets({'geneid': geneid})
  if targets:
    return targets[0]
  else:
    return None


if __name__ == '__main__':
  print "\n{} (v{}) [{}]:".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  start_time = time.time()
  load(args)
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))
