#!/usr/bin/env python
# Time-stamp: <2017-11-20 10:57:48 smathias>
""" Load BioPlex ppis into TCRD from TSV file.

Usage:
    load-PPIsBioPlex.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
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
  -d --debug DEBUGL    : set debugging output level (0-3) [default: 0]
  -? --help            : print this message and exit 
"""
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2015-2017, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.0.0"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import logging
import csv
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])

# http://wren.hms.harvard.edu/bioplex/downloadInteractions.php
BIOPLEX_FILE = '/home/app/TCRD/data/PPIs/BioPlex_interactionList_v4.tsv'
PPI_FILES = ['../data/BioPlex/BioPlex_interactionList_v4.tsv',
             '../data/BioPlex/interactome_update_Aug2016.tsv',
             '../data/BioPlex/interactome_update_Dec2016.tsv']
SRC_FILES = [os.path.basename(f) for f in PPI_FILES]

def load():
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
    print "\nConnected to TCRD database %s (schema ver %s; data ver %s)" % (args['--dbname'], dbi['schema_ver'], dbi['data_ver'])

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'BioPlex Protein-Protein Interactions', 'source': "Files %s from http://wren.hms.harvard.edu/bioplex/downloadInteractions.php"%", ".join(SRC_FILES), 'app': PROGRAM, 'app_version': __version__, 'url': 'http://wren.hms.harvard.edu/bioplex/index.php'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'ppi', 'where_clause': "ppitype = 'BioPlex'"})
  if not rv:
    print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
    sys.exit(1)
    
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]

  start_time = time.time()
  f = PPI_FILES[0]
  line_ct = wcl(f)
  line_ct -= 1
  if not args['--quiet']:
    print "\nProcessing %d lines from BioPlex PPI file %s" % (line_ct, f)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  with open(f, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    header = tsvreader.next() # skip header line
    # GeneA   GeneB   UniprotA        UniprotB        SymbolA SymbolB pW      pNI     pInt
    ct = 0
    ppi_ct = 0
    k2pid = {}
    notfnd = {}
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
          notfnd[k1] = True
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
          notfnd[k2] = True
          continue
        pid2 = t2['components']['protein'][0]['id']
      k2pid[k2] = pid2
      # Insert PPI
      rv = dba.ins_ppi( {'ppitype': 'BioPlex','p_int': pint, 'p_ni': pni, 'p_wrong': pw,
                         'protein1_id': pid1, 'protein1_str': k1,
                         'protein2_id': pid2, 'protein2_str': k2} )
      if rv:
        ppi_ct += 1
      else:
        dba_err_ct += 1
  pbar.finish()
  elapsed = time.time() - start_time
  print "%d BioPlex PPI rows processed." % ct
  print "  Inserted %d new ppi rows" % ppi_ct
  if len(notfnd) > 0:
    print "  %d proteins NOT FOUND in TCRD:" % len(notfnd)
    #for d in notfnd:
    #  print d
  if dba_err_ct > 0:
    print "WARNNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)

  for f in PPI_FILES[1:]:
    start_time = time.time()
    line_ct = wcl(f)
    line_ct -= 1
    if not args['--quiet']:
      print "\nProcessing %d lines from BioPlex PPI update file %s" % (line_ct, f)
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    with open(f, 'rU') as tsv:
      tsvreader = csv.reader(tsv, delimiter='\t')
      header = tsvreader.next() # skip header line
      # plate_num       well_num        db_protein_id   symbol  gene_id bait_symbol     bait_geneid     pWrongID        pNoInt  pInt
      ct = 0
      ppi_ct = 0
      k2pid = {}
      notfnd = {}
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
            notfnd[k1] = True
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
            notfnd[k2] = True
            continue
          pid2 = t2['components']['protein'][0]['id']
          k2pid[k2] = pid2
        # Insert PPI
        rv = dba.ins_ppi( {'ppitype': 'BioPlex','p_int': pint, 'p_ni': pni, 'p_wrong': pw,
                           'protein1_id': pid1, 'protein1_str': k1,
                           'protein2_id': pid2, 'protein2_str': k2} )
        if rv:
          ppi_ct += 1
        else:
          dba_err_ct += 1
    pbar.finish()
    elapsed = time.time() - start_time
    print "%d BioPlex PPI rows processed." % ct
    print "  Inserted %d new ppi rows" % ppi_ct
    if len(notfnd) > 0:
      print "  %d proteins NOT FOUND in TCRD:" % len(notfnd)
    if dba_err_ct > 0:
      print "WARNNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)


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

def wcl(fname):
  with open(fname) as f:
    for i, l in enumerate(f):
      pass
  return i + 1

def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])

if __name__ == '__main__':
  print "\n%s (v%s) [%s]:\n" % (PROGRAM, __version__, time.strftime("%c"))
  load()
  print "\n%s: Done.\n" % PROGRAM
