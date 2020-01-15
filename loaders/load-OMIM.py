#!/usr/bin/env python
# Time-stamp: <2019-04-17 11:11:06 smathias>
"""Load phenotypes into TCRD from OMIM genemap.txt file.

Usage:
    load-OMIM.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-OMIM.py -h | --help

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
__version__   = "2.2.0"

import os,sys,time
from docopt import docopt
from TCRDMP import DBAdaptor
import csv
import logging
import urllib
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd6logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
DOWNLOAD_DIR = '../data/OMIM/'
# One must register to get OMIM downloads. This gives a user-specific download link.
# NB. the phenotypic series file must be added to one's key's entitlements by OMIM staff.
# To view a list of all the data a key has access to, go to:
# https://omim.org/downloads/<key>
BASE_URL = 'https://data.omim.org/downloads/ey9G4kaCTGCQ-q_Yx0XAPg/'
GENEMAP_FILE = 'genemap.txt'
TITLES_FILE = 'mimTitles.txt'
PS_FILE = 'phenotypicSeries.txt'

def download():
  print
  for fn in [GENEMAP_FILE, TITLES_FILE, PS_FILE]:
    if os.path.exists(DOWNLOAD_DIR + fn):
      os.rename(DOWNLOAD_DIR + fn, DOWNLOAD_DIR + fn + '.bak')
    print "Downloading ", BASE_URL + fn
    print "         to ", DOWNLOAD_DIR + fn
    urllib.urlretrieve(BASE_URL + fn, DOWNLOAD_DIR + fn)
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
  dataset_id = dba.ins_dataset( {'name': 'OMIM', 'source': 'Files %s downloaded from omim.org'%", ".join([GENEMAP_FILE, TITLES_FILE, PS_FILE]), 'app': PROGRAM, 'app_version': __version__, 'url': 'http://omim.org/', 'comments': 'Confirmed OMIM phenotypes and OMIM Phenotype Series info'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'omim'},
            {'dataset_id': dataset_id, 'table_name': 'omim_ps'},
            {'dataset_id': dataset_id, 'table_name': 'phenotype', 'where_clause': "ptype = 'OMIM'"} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

  # OMIMs and Phenotypic Series
  fname = DOWNLOAD_DIR + TITLES_FILE
  line_ct = slmf.wcl(fname)
  if not args['--quiet']:
    print '\nProcessing %d lines from input file %s' % (line_ct, fname)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start()
  with open(fname, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    skip_ct = 0
    omim_ct = 0
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
      if row[0].startswith('#'):
        # The file has commented lines
        skip_ct += 1
        continue
      # The fields are:
      # 0: Prefix ???
      # 1: Mim Number
      # 2: Preferred Title; symbol Alternative Title(s); symbol(s)
      # 3: Included Title(s); symbols
      title = row[2].partition(';')[0]
      rv = dba.ins_omim({'mim': row[1], 'title': title})
      if not rv:
        dba_err_ct += 1
        continue
      omim_ct += 1
      pbar.update(ct)
  pbar.finish()
  print "{} lines processed".format(ct)
  print "  Skipped {} commented lines.".format(skip_ct)
  print "Loaded {} new omim rows".format(omim_ct)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

  fname = DOWNLOAD_DIR + PS_FILE
  line_ct = slmf.wcl(fname)
  if not args['--quiet']:
    print '\nProcessing %d lines from input file %s' % (line_ct, fname)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start()
  with open(fname, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    skip_ct = 0
    ps_ct = 0
    err_ct = 0
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
      if row[0].startswith('#'):
        # The file has commented lines
        skip_ct += 1
        continue
      # The fields are:
      # 0: Phenotypic Series Number
      # 1: Mim Number
      # 2: Phenotype
      if len(row) ==2:
        init = {'omim_ps_id': row[0], 'title': row[1]}
      elif len(row) == 3:
        init = {'omim_ps_id': row[0], 'mim': row[1], 'title': row[2]}
      else:
        err_ct += 1
        logger.warn("Parsing error for row {}".format(row))
        continue
      rv = dba.ins_omim_ps(init)
      if not rv:
        dba_err_ct += 1
        continue
      ps_ct += 1
      pbar.update(ct)
  pbar.finish()
  print "{} lines processed".format(ct)
  print "  Skipped {} commented lines.".format(skip_ct)
  print "Loaded {} new omim_ps rows".format(ps_ct)
  if err_ct > 0:
    print "WARNING: {} parsing errors occurred. See logfile {} for details.".format(er_ct, logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)
    
  # Phenotypes
  fname = DOWNLOAD_DIR + GENEMAP_FILE
  line_ct = slmf.wcl(fname)
  if not args['--quiet']:
    print '\nProcessing %d lines from input file %s' % (line_ct, fname)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start()
  with open(fname, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    tmark = {}
    skip_ct = 0
    notfnd_ct = 0
    prov_ct = 0
    dds_ct = 0
    pt_ct = 0
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
      if row[0].startswith('#'):
        # The file has commented lines
        skip_ct += 1
        continue
      # The fields are:
      # 0 - Sort ???
      # 1 - Month
      # 2 - Day
      # 3 - Year
      # 4 - Cytogenetic location
      # 5 - Gene Symbol(s)
      # 6 - Confidence
      # 7 - Gene Name
      # 8 - MIM Number
      # 9 - Mapping Method
      # 10 - Comments
      # 11 - Phenotypes
      # 12 - Mouse Gene Symbol
      pts = row[11]
      if pts.startswith('?'):
        prov_ct += 1
        continue
      if '(4)' in pts:
        dds_ct += 1
      trait = "MIM Number: %s" % row[8]
      if row[11]:
        trait += "; Phenotype: %s" % pts
      found = False
      syms = row[5].split(', ')
      logger.info("Checking for OMIM syms: {}".format(syms))
      for sym in syms:
        targets = dba.find_targets({'sym': sym})
        if targets:
          found = True
          for t in targets:
            p = t['components']['protein'][0]
            logger.info("  Symbol {} found target {}: {}, {}".format(sym, t['id'], p['name'], p['description']))
            rv = dba.ins_phenotype({'protein_id': p['id'], 'ptype': 'OMIM', 'trait': trait})
            if not rv:
              dba_err_ct += 1
              continue
            tmark[t['id']] = True
            pt_ct += 1
      if not found:
        notfnd_ct += 1
        logger.warn("No target found for row {}".format(row))
      pbar.update(ct)
  pbar.finish()
  print "{} lines processed".format(ct)
  print "  Skipped {} commented lines.".format(skip_ct)
  print "  Skipped {} provisional phenotype rows.".format(prov_ct)
  print "  Skipped {} deletion/duplication syndrome rows.".format(dds_ct)
  print "Loaded {} OMIM phenotypes for {} targets".format(pt_ct, len(tmark))
  if notfnd_ct > 0:
    print "No target found for {} good lines. See logfile {} for details.".format(notfnd_ct, logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)


if __name__ == '__main__':
  print "\n{} (v{}) [{}]:".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  download()
  start_time = time.time()
  load(args)
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))








