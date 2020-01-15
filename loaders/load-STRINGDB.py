#!/usr/bin/env python
# Time-stamp: <2019-10-15 09:31:33 smathias>
"""Load JensenLab STRINGDB ppis into TCRD.

Usage:
    load-STRINGDB.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-STRINGDB.py -h | --help

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
from collections import defaultdict
import logging
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd6logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
# https://stringdb-static.org/download/protein.links.v10.5/9606.protein.links.v10.5.txt.gz
# INFILE = '../data/JensenLab/9606.protein.links.v10.5.txt'
# https://stringdb-static.org/download/protein.links.v11.0/9606.protein.links.v11.0.txt.gz
INFILE = '../data/STRING/9606.protein.links.v11.0.txt'

def load(args):
  loglevel = int(args['--loglevel'])
  if args['--logfile']:
    logfile = args['--logfile']
  else:
    logfile = LOGFILE
  logger = logging.getLogger(__name__)
  logger.setLevel(loglevel)
  if not args['--debug']:
    logger.propagate = False # turns off console logging when debug is 0
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
  dataset_id = dba.ins_dataset( {'name': 'STRINGDB', 'source': 'File %s from https://stringdb-static.org/download/protein.links.v11.0/'%(os.path.basename(INFILE)), 'app': PROGRAM, 'app_version': __version__, 'url': 'http://string-db.org/'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'ppi', 'where_clause': 'ppitype = "STRINGDB"'})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  line_ct = slmf.wcl(INFILE)
  if not args['--quiet']:
    print "\nProcessing {} lines in file {}".format(line_ct, INFILE)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  ct = 0
  # So we only look up target(s) for each ENSP once,
  # save mapping of ENSP to list of (pid, sym) tuples
  ensp2pids = defaultdict(list)
  same12_ct = 0
  notfnd = set()
  ppi_ct = 0
  dba_err_ct = 0
  with open(INFILE, 'r') as ifh:
    for line in ifh:
      # protein1 protein2 combined_score
      line.rstrip('\n')
      ct += 1
      if ct == 1:
        # skip header line
        continue
      [ensp1, ensp2, score] = line.split()
      ensp1 = ensp1.replace('9606.', '')
      ensp2 = ensp2.replace('9606.', '')
      # ENSP1
      if ensp1 in ensp2pids:
        p1s = ensp2pids[ensp1]
      elif ensp1 in notfnd:
        continue
      else:
        targets = find_targets(dba, ensp1)
        if not targets:
          notfnd.add(ensp1)
          continue
        p1s = []
        for t in targets:
          p = t['components']['protein'][0]
          p1s.append( (p['id'], p['sym']) )
        ensp2pids[ensp1] = p1s
      # ENSP2
      if ensp2 in ensp2pids:
        p2s = ensp2pids[ensp2]
      elif ensp2 in notfnd:
        continue
      else:
        targets = find_targets(dba, ensp2)
        if not targets:
          notfnd.add(ensp2)
          continue
        p2s = []
        for t in targets:
          p = t['components']['protein'][0]
          p2s.append( (p['id'], p['sym']) )
        ensp2pids[ensp2] = p2s
      # Insert PPI(s)
      for p1 in p1s:
        for p2 in p2s:
          if p1[0] == p2[0]:
            same12_ct += 1
            continue
          rv = dba.ins_ppi( {'ppitype': 'STRINGDB', 
                             'protein1_id': p1[0], 'protein1_str': p1[1],
                             'protein2_id': p2[0], 'protein2_str': p2[1], 'score': score} )
          if rv:
            ppi_ct += 1
          else:
            dba_err_ct += 1
      pbar.update(ct)
  pbar.finish()
  for ensp in notfnd:
    logger.warn("No target found for {}".format(ensp))
  print "{} lines processed.".format(ct)
  print "  Inserted {} new ppi rows".format(ppi_ct)
  if same12_ct:
    print "  Skipped {} PPIs involving the same protein".format(same12_ct)
  if notfnd:
    print "No target found for {} ENSPs. See logfile {} for details.".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

def find_targets(dba, ensp):
  targets = dba.find_targets({'stringid': ensp})
  if not targets:
    targets = dba.find_targets_by_xref({'xtype': 'STRING', 'value': '9606.'+ensp})
  if targets:
    return targets
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

# with open(INFILE1, 'rU') as tsv:
#   tsvreader = csv.reader(tsv, delimiter='\t')
#   header = tsvreader.next() # skip header line
#   for row in tsvreader:
#     # species   uniprot_ac|uniprot_id   string_id   identity   bit_score
#     if row[3] != '100.00':
#       continue
#     [uniprot, name] = row[1].split("|")
#     ensp = row[2]
#     bitscore = row[4]
#     if uniprot in aliasmap:
#       # Only save mappings with highest bit scores
#       if bitscore > aliasmap[uniprot][1]:
#         aliasmap[uniprot] = (ensp, bitscore)
#     else:
#       aliasmap[uniprot] = (ensp, bitscore)
#     if name in aliasmap:
#       # Only save mappings with highest bit scores
#       if bitscore > aliasmap[name][1]:
#         aliasmap[name] = (ensp, bitscore)
#     else:
#       aliasmap[name] = (ensp, bitscore)
# with open(INFILE2, 'rU') as tsv:
#   tsvreader = csv.reader(tsv, delimiter='\t')
#   header = tsvreader.next() # skip header line
#   for row in tsvreader:
#     ## string_protein_id ## alias ## source ##
#     alias = row[1]
#     ensp = row[0].replace('9606.', '')
#     if alias in aliasmap and aliasmap[alias][0] != ensp:
#       # do not replace mappings from *reviewed_uniprot_2_string* with aliases
#       continue
#     aliasmap[alias] = (ensp, None)
