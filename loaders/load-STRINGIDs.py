#!/usr/bin/env python
# Time-stamp: <2017-02-22 10:35:36 smathias>
"""Load JensenLab STRING IDs (ENSPs) into TCRD protein.ensp.

Usage:
    load-STRINGIDs.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-STRINGIDs.py -h | --help

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
__copyright__ = "Copyright 2014-2016, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.2.0"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import csv
import logging
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
LOGFILE = "%s.log" % PROGRAM
# http://string-db.org/mapping_files/uniprot_mappings/9606_reviewed_uniprot_2_string.04_2015.tsv.gz
INFILE1 = '../data/JensenLab/9606_reviewed_uniprot_2_string.04_2015.tsv'
# http://string-db.org/download/protein.aliases.v10/9606.protein.aliases.v10.txt.gz
INFILE2 = '../data/JensenLab/9606.protein.aliases.v10.txt'

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

  # DBAdaptor uses same logger as main()
  dba_params = {'dbhost': args['--dbhost'], 'dbname': args['--dbname'], 'logger_name': __name__}
  dba = DBAdaptor(dba_params)
  dbi = dba.get_dbinfo()
  logger.info("Connected to TCRD database %s (schema ver %s; data ver %s)", args['--dbname'], dbi['schema_ver'], dbi['data_ver'])
  if not args['--quiet']:
    print "\n%s (v%s) [%s]:" % (PROGRAM, __version__, time.strftime("%c"))
    print "\nConnected to TCRD database %s (schema ver %s; data ver %s)" % (args['--dbname'], dbi['schema_ver'], dbi['data_ver'])

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'JensenLab STRING IDs', 'source': 'Files %s and %s from from http://string-db.org/'%(os.path.basename(INFILE1), os.path.basename(INFILE2)), 'app': PROGRAM, 'app_version': __version__, 'columns_touched': 'protein.string_id', 'url': 'http://string-db.org/'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'protein', 'column_name': 'stringid'})
  if not rv:
    print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
    sys.exit(1)

  aliasmap = {}
  
  start_time = time.time()
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  skip_ct = 0
  notfnd = {}
  mult_ct = 0
  line_ct = wcl(INFILE1)
  line_ct -= 1 # file has header
  if not args['--quiet']:
    print "\nProcessing %d input lines in file %s" % (line_ct, INFILE1)
  with open(INFILE1, 'rU') as tsv:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    tsvreader = csv.reader(tsv, delimiter='\t')
    header = tsvreader.next() # skip header line
    ct = 0
    for row in tsvreader:
      # species   uniprot_ac|uniprot_id   string_id   identity   bit_score
      ct += 1
      pbar.update(ct)
      if row[3] != '100.00':
        skip_ct += 1
        continue
      [uniprot, name] = row[1].split("|")
      ensp = row[2]
      bitscore = row[4]
      if uniprot in aliasmap:
        # Only save mappings with highest bit scores
        if bitscore > aliasmap[uniprot][1]:
          aliasmap[uniprot] = (ensp, bitscore)
      else:
        aliasmap[uniprot] = (ensp, bitscore)
      if name in aliasmap:
        # Only save mappings with highest bit scores
        if bitscore > aliasmap[name][1]:
          aliasmap[name] = (ensp, bitscore)
      else:
        aliasmap[name] = (ensp, bitscore)
  pbar.finish()
  elapsed = time.time() - start_time
  unmap_ct = len(aliasmap.keys())
  print "%d input lines processed. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "  Skipped %d non-identity lines" % skip_ct
  print "  Got %d uniprot/name to STRING ID mappings" % unmap_ct
  if notfnd:
    print "No target found for %d UniProts/Names:" % len(notfnd.keys())

  start_time = time.time()
  line_ct = wcl(INFILE2)
  line_ct -= 1 # file has header
  if not args['--quiet']:
    print "\nProcessing %d input lines in file %s" % (line_ct, INFILE2)
  with open(INFILE2, 'rU') as tsv:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    tsvreader = csv.reader(tsv, delimiter='\t')
    header = tsvreader.next() # skip header line
    ct = 0
    err_ct = 0
    for row in tsvreader:
      ## string_protein_id ## alias ## source ##
      ct += 1
      pbar.update(ct)
      alias = row[1]
      ensp = row[0].replace('9606.', '')
      if alias in aliasmap and aliasmap[alias][0] != ensp:
        # do not replace mappings from *reviewed_uniprot_2_string* with aliases
        logger.info("Different ENSPs found for same alias %s: %s vs %s" % (alias, aliasmap[alias][0], ensp))
        err_ct += 1
        continue
      aliasmap[alias] = (ensp, None)
  pbar.finish()
  elapsed = time.time() - start_time
  amap_ct = len(aliasmap.keys()) - unmap_ct
  print "%d input lines processed. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "  Got %d alias to STRING ID mappings" % amap_ct
  if err_ct > 0:
    print "  Skipped %d aliases that would override reviewed mappings . See logfile %s for details." % (err_ct, logfile)

  start_time = time.time()
  tct = dba.get_target_count(idg=False)
  if not args['--quiet']:
    print "\nLoading STRING IDs for %d TCRD targets" % tct
  pbar = ProgressBar(widgets=pbar_widgets, maxval=tct).start()
  ct = 0
  upd_ct = 0
  dba_err_ct = 0
  for target in dba.get_targets(include_annotations=True):
    ct += 1
    pbar.update(ct)
    p = target['components']['protein'][0]
    geneid = 'hsa:' + str(p['geneid'])
    hgncid = None
    if 'HGNC' in p['xrefs']:
      hgncid = p['xrefs']['HGNC'][0]['value']
    ensp = None
    if p['name'] in aliasmap:
      ensp = aliasmap[p['name']][0]
    elif p['uniprot'] in aliasmap:
      ensp = aliasmap[p['uniprot']][0]
    elif geneid in aliasmap:
      ensp = aliasmap[geneid][0]
    elif hgncid and hgncid in aliasmap:
      ensp = aliasmap[hgncid][0]
    if not ensp: continue # No STRING ID for this target
    rv = dba.do_update({'table': 'protein', 'id': p['id'], 'col': 'stringid', 'val': ensp} )
    if rv:
      upd_ct += 1
    else:
      dba_err_ct += 1
  pbar.finish()
  elapsed = time.time() - start_time
  print "Updated %d STRING ID values" % upd_ct
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)
  
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
