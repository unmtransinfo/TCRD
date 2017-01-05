#!/usr/bin/env python
# Time-stamp: <2017-01-05 16:35:36 smathias>
"""Load Drugable Epigenome TDL Infos into TCRD from CSV files.

Usage:
    load-DrugableEpigenomeTDLs.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-DrugableEpigenomeTDLs.py -? | --help

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
__version__   = "2.0.0"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import csv
import logging
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
INPUT_DIR = '/home/smathias/TCRD/data/Epigenetic-RWE/'
FILE_LIST = { 'Writer': {'Histone acetyltransferase': 'nrd3674-s3.csv',
                         'Protein methyltransferase': 'nrd3674-s8.csv'},
              'Eraser': {'Histone deacetylase': 'nrd3674-s4.csv',
                         'Lysine demethylase': 'nrd3674-s5.csv'},
              'Reader': {'Bromodomain': 'nrd3674-s1.csv',
                         'Chromodomain': 'nrd3674-s2.csv',
                         'Methyl-*-binding domain': 'nrd3674-s6.csv',
                         'PHD-containing protein': 'nrd3674-s7.csv',
                         'PWWP domain': 'nrd3674-s9.csv',
                         'Tudor domain': 'nrd3674-s10.csv'} }
OUTFILE = '../TCRDv111_EpigeneticRWEs_Mapping.csv'
RESULTS = { 'Writers': {'Histone acetyltransferases': {'Tdark': 0, 'Tgray': 0, 'Tmacro': 0, 'Tchem': 0, 'Tclin': 0, 'Tclin+': 0},
                        'Protein methyltransferases': {'Tdark': 0, 'Tgray': 0, 'Tmacro': 0, 'Tchem': 0, 'Tclin': 0, 'Tclin+': 0}},
            'Erasers': {'Histone deacetylases': {'Tdark': 0, 'Tgray': 0, 'Tmacro': 0, 'Tchem': 0, 'Tclin': 0, 'Tclin+': 0},
                        'Lysine demethylases': {'Tdark': 0, 'Tgray': 0, 'Tmacro': 0, 'Tchem': 0, 'Tclin': 0, 'Tclin+': 0}},
            'Readers': {'Bromodomains': {'Tdark': 0, 'Tgray': 0, 'Tmacro': 0, 'Tchem': 0, 'Tclin': 0, 'Tclin+': 0},
                        'Chromodomains': {'Tdark': 0, 'Tgray': 0, 'Tmacro': 0, 'Tchem': 0, 'Tclin': 0, 'Tclin+': 0},
                        'Methyl-*-binding domains': {'Tdark': 0, 'Tgray': 0, 'Tmacro': 0, 'Tchem': 0, 'Tclin': 0, 'Tclin+': 0},
                        'PHD-containing proteins': {'Tdark': 0, 'Tgray': 0, 'Tmacro': 0, 'Tchem': 0, 'Tclin': 0, 'Tclin+': 0},
                        'PWWP domains': {'Tdark': 0, 'Tgray': 0, 'Tmacro': 0, 'Tchem': 0, 'Tclin': 0, 'Tclin+': 0},
                        'Tudor domains': {'Tdark': 0, 'Tgray': 0, 'Tmacro': 0, 'Tchem': 0, 'Tclin': 0, 'Tclin+': 0}} }
TDLS = {'Tdark': 0, 'Tgray': 0, 'Tmacro': 0, 'Tchem': 0, 'Tclin': 0, 'Tclin+': 0}

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
  dataset_id = dba.ins_dataset( {'name': 'Drugable Epigenome Domains', 'source': 'Files from http://www.nature.com/nrd/journal/v11/n5/suppinfo/nrd3674.html', 'app': PROGRAM, 'app_version': __version__, 'url': 'http://www.nature.com/nrd/journal/v11/n5/suppinfo/nrd3674.html'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'tdl_info', 'where_clause': "itype = 'Drugable Epigenome Class'"})
  if not rv:
    print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
    sys.exit(1)

  total_ti_ct = 0
  for k,d in FILE_LIST.items():
    if not args['--quiet']:
      print "\nProcessing Epigenetic %ss" % k
    for dom,f in d.items():
      f = INPUT_DIR + f
      line_ct = wcl(f)
      if not args['--quiet']:
        print 'Processing %d lines from %s input file %s' % (line_ct, dom, f)
      with open(f, 'rU') as csvfile:
        csvreader = csv.reader(csvfile)
        header = csvreader.next() # skip header lines
        ct = 0
        not_fnd_ct = 0
        tct = 0
        ti_ct = 0
        dba_err_ct = 0
        for row in csvreader:
          ct += 1
          targets = dba.find_targets({'sym': row[0]})
          if not targets:
            targets = dba.find_targets({'geneid': row[3]})
          if not targets:
            targets = dba.find_targets({'uniprot': row[2]})
          if not targets:
            not_fnd_ct += 1
            continue
          tct += 1
          t = targets[0]
          p = t['components']['protein'][0]
          if len(row) == 5:
            val = "Epigenetic %s - %s" % (k, dom)
          else:
            val = "Epigenetic %s - %s %s: %s" % (k, dom, row[4], row[5])
          rv = dba.ins_tdl_info({'protein_id': p['id'], 'itype': 'Drugable Epigenome Class', 'string_value': val})
          if not rv:
            dba_err_ct += 1
            continue
          ti_ct += 1
        if not args['--quiet']:
          print "  %d lines processed. Found %d, skipped %d" % (ct, tct, not_fnd_ct)
          print "  Inserted %d new tdl_info rows" % ti_ct
        if dba_err_ct > 0:
          print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)
        total_ti_ct += ti_ct

  if not args['--quiet']:
    print "\nInserted a total of %d new Drugable Epigenome Class tdl_infos" %  total_ti_ct
  print "\n%s: Done.\n" % PROGRAM


def wcl(fname):
  with open(fname) as f:
    for i, l in enumerate(f):
      pass
  return i + 1

if __name__ == '__main__':
  main()








