#!/usr/bin/env python
# Time-stamp: <2019-01-28 12:13:08 smathias>
"""Load JensenLab STRING IDs (ENSPs) into TCRD protein.ensp.

Usage:
    load-STRINGIDs.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
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
  -d --debug           : turn on debugging output
  -? --help            : print this message and exit 
"""
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2014-2019, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.7.0"

import os,sys,time
from docopt import docopt
from TCRDMP import DBAdaptor
import csv
import logging
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd6logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
# http://string-db.org/mapping_files/uniprot/human.uniprot_2_string.2018.tsv.gz
INFILE1 = '../data/JensenLab/human.uniprot_2_string.2018.tsv'
# https://stringdb-static.org/download/protein.aliases.v11.0.txt.gz
# $ grep '^9606.' protein.aliases.v11.0.txt > 9606.protein.aliases.v11.0.txt
INFILE2 = '../data/JensenLab/9606.protein.aliases.v11.0.txt'

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

  # DBAdaptor uses same logger as load()
  dba_params = {'dbhost': args['--dbhost'], 'dbname': args['--dbname'], 'logger_name': __name__}
  dba = DBAdaptor(dba_params)
  dbi = dba.get_dbinfo()
  logger.info("Connected to TCRD database {} (schema ver {}; data ver {})".format(args['--dbname'], dbi['schema_ver'], dbi['data_ver']))
  if not args['--quiet']:
    print "\nConnected to TCRD database {} (schema ver {}; data ver {})".format(args['--dbname'], dbi['schema_ver'], dbi['data_ver'])

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'STRING IDs', 'source': 'Files %s and %s from from http://string-db.org/'%(os.path.basename(INFILE1), os.path.basename(INFILE2)), 'app': PROGRAM, 'app_version': __version__, 'url': 'http://string-db.org/'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'protein', 'column_name': 'stringid'})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

  aliasmap = {}
  
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  ct = 0
  skip_ct = 0
  mult_ct = 0
  line_ct = slmf.wcl(INFILE1)
  if not args['--quiet']:
    print "\nProcessing {} input lines in file {}".format(line_ct, INFILE1)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  with open(INFILE1, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    header = tsvreader.next() # skip header line
    ct += 1
    for row in tsvreader:
      # taxid   uniprot_ac|uniprot_id   string_id   identity   bit_score
      ct += 1
      pbar.update(ct)
      if float(row[3]) != 100:
        skip_ct += 1
        continue
      [uniprot, name] = row[1].split("|")
      ensp = row[2].replace('9606.', '')
      bitscore = float(row[4])
      if uniprot in aliasmap:
        # Save mapping with highest bit score
        if bitscore > aliasmap[uniprot][1]:
          aliasmap[uniprot] = (ensp, bitscore)
      else:
        aliasmap[uniprot] = (ensp, bitscore)
      if name in aliasmap:
        # Save mapping with highest bit score
        if bitscore > aliasmap[name][1]:
          aliasmap[name] = (ensp, bitscore)
      else:
        aliasmap[name] = (ensp, bitscore)
  pbar.finish()
  unmap_ct = len(aliasmap)
  print "{} input lines processed.".format(ct)
  print "  Skipped {} non-identity lines".format(skip_ct)
  print "  Got {} uniprot/name to STRING ID mappings".format(unmap_ct)

  line_ct = slmf.wcl(INFILE2)
  if not args['--quiet']:
    print "\nProcessing {} input lines in file {}".format(line_ct, INFILE2)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start()
  ct = 0
  warn_ct = 0
  with open(INFILE2, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    header = tsvreader.next() # skip header line
    ct += 1
    for row in tsvreader:
      ## string_protein_id ## alias ## source ##
      ct += 1
      pbar.update(ct)
      alias = row[1]
      ensp = row[0].replace('9606.', '')
      if alias in aliasmap and aliasmap[alias][0] != ensp:
        # do not replace mappings from *human.uniprot_2_string.2018* with aliases
        logger.warn("Different ENSPs found for same alias {}: {} vs {}".format(alias, aliasmap[alias][0], ensp))
        warn_ct += 1
        continue
      aliasmap[alias] = (ensp, None)
  pbar.finish()
  amap_ct = len(aliasmap) - unmap_ct
  print "{} input lines processed.".format(ct)
  print "  Added {} alias to STRING ID mappings".format(amap_ct)
  if warn_ct > 0:
    print "  Skipped {} aliases that would override UniProt mappings. See logfile {} for details.".format(warn_ct, logfile)

  tct = dba.get_target_count(idg=False)
  if not args['--quiet']:
    print "\nLoading STRING IDs for {} TCRD targets".format(tct)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=tct).start()
  ct = 0
  upd_ct = 0
  nf_ct = 0
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
    if p['uniprot'] in aliasmap:
      ensp = aliasmap[p['uniprot']][0]
    elif p['name'] in aliasmap:
      ensp = aliasmap[p['name']][0]
    elif geneid in aliasmap:
      ensp = aliasmap[geneid][0]
    elif hgncid and hgncid in aliasmap:
      ensp = aliasmap[hgncid][0]
    if not ensp:
      nf_ct += 1
      logger.warn("No stringid fo protein {} ({})".format(p['id'], p['uniprot']))
      continue
    rv = dba.do_update({'table': 'protein', 'id': p['id'], 'col': 'stringid', 'val': ensp} )
    if rv:
      upd_ct += 1
    else:
      dba_err_ct += 1
  pbar.finish()
  print "Updated {} STRING ID values".format(upd_ct)
  if nf_ct > 0:
    print "No stringid found for {} proteins. See logfile {} for details.".format(nf_ct, logfile)
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
