#!/usr/bin/env python
# Time-stamp: <2016-12-09 11:00:00 smathias>
"""Load IMPC phenotype data into TCRD from CSV file.

Usage:
    load-IMPCPhenotypes.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-IMPCPhenotypes.py -? | --help

Options:
  -h --dbhost DBHOST   : MySQL database host name [default: localhost]
  -n --dbname DBNAME   : MySQL database name [default: tcrd]
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
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
DBHOST = 'localhost'
DBPORT = 3306
DBNAME = 'tcrdev'
LOGFILE = "%s.log" % PROGRAM

# Get from ftp://ftp.ebi.ac.uk/pub/databases/impc/release-*.*/csv/
IMPC_FILE = '/home/app/TCRD/data/IMPC/ALL_genotype_phenotype.csv'
IMPC_VER = '4.3'

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
  dataset_id = dba.ins_dataset( {'name': 'IMPC Phenotypes', 'source': "File %s from ftp://ftp.ebi.ac.uk/pub/databases/impc/release-%s/csv/"%(os.path.basename(IMPC_FILE), IMPC_VER), 'app': PROGRAM, 'app_version': __version__, 'url': 'ftp://ftp.ebi.ac.uk/pub/databases/impc/release-%s/csv/README'%IMPC_VER} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'phenotype', 'where_clause': "ptype = 'IMPC'"})
  if not rv:
    print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
    sys.exit(1)
  
  start_time = time.time()
  line_ct = wcl(IMPC_FILE)
  line_ct -= 1 # file has header row
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]

  if not args['--quiet']:
    print "\nProcessing %d lines from input file %s" % (line_ct, IMPC_FILE)
  with open(IMPC_FILE, 'rU') as csvfile:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    csvreader = csv.reader(csvfile)
    csvreader.next() # skip header line
    ct = 0
    tmark = {}
    pt_ct = 0
    ptmark = {} # the data file has the same data for male and female mice. These end up looking like duplicates since TCRD phenotype table does not have that level of detail. Keep track of loaded data so this doesn't happen.
    mgixr_ct = 0
    notfnd = set()
    dba_err_ct = 0
    for row in csvreader:
      ct += 1
      sym = row[1].upper()
      targets = dba.find_targets({'sym': sym}, idg = False)
      if not targets:
        notfnd.add(tuple(row))
        continue
      for t in targets:
        if not row[21] and not row[22]:
          # skip data with neither a term_id or term_name (IMPC has 134 of these)
          continue
        tmark[t['id']] = True
        pid = t['components']['protein'][0]['id']
        k = "%s|%s|%s|%s|%s|%s|%s|%s|%s" % (pid, row[19], row[20], row[21], row[22], row[23], row[24], row[25], row[26])
        if k in ptmark: # Don't add "duplicates"
          continue
        rv = dba.ins_xref({'protein_id': pid, 'xtype': 'MGI ID', 'dataset_id': dataset_id, 'value': row[0]})
        if rv:
          mgixr_ct += 1
        else:
          dba_err_ct += 1
        rv = dba.ins_phenotype({'protein_id': pid, 'ptype': 'IMPC', 'top_level_term_id': row[19], 'top_level_term_name': row[20], 'term_id': row[21], 'term_name': row[22], 'p_value': row[23], 'percentage_change': row[24], 'effect_size': row[25], 'statistical_method': row[26]})
        if rv:
          pt_ct += 1
          ptmark[k] = True
        else:
          dba_err_ct += 1
      pbar.update(ct)
  pbar.finish()

  print "%d rows processed." % ct
  print "%d targets annotated with IMPC phenotypes" % len(tmark.keys())
  print "  Inserted %d new phenotype rows" % pt_ct
  print "  Inserted %d new MGI ID xref rows" % mgixr_ct
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)
  if notfnd:
    print "No target found for %d gene symbols" % len(notfnd)
    #for row in notfnd:
    #  print row[0],row[1]

  print "\n%s: Done." % PROGRAM
  print


def wcl(fname):
  with open(fname) as f:
    for i, l in enumerate(f):
      pass
  return i + 1

def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])

if __name__ == '__main__':
    main()
