#!/usr/bin/env python
# Time-stamp: <2017-11-30 15:03:53 smathias>
"""Load IMPC mice tdl_infod into TCRD from CSV file.

Usage:
    load-IMPCMiceTDLInfos.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-IMPCMiceTDLInfos.py -? | --help

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
__copyright__ = "Copyright 2016-2017, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.0.0"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import logging
import csv
import shelve
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
IMPC_FILE = '../data/IMPC/IDG summary-1.csv'
OUT_FILE = '../data/IMPC/IDGSummary-1_TCRD.csv'
SHELF_FILE = 'tcrd4logs/load-IMPCMiceTDLInfos.db'

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

  s = shelve.open(SHELF_FILE, writeback=True)
  s['notfnd'] = set()

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'IMPC Mouse Clones', 'source': "File %s obtained directly from Terry Meehan/Steve Murray"%os.path.basename(IMPC_FILE), 'app': PROGRAM, 'app_version': __version__, 'url': 'http://www.mousephenotype.org/'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'tdl_info', 'where_clause': "itype = 'IMPC Clones'"},
            {'dataset_id': dataset_id, 'table_name': 'tdl_info', 'where_clause': "itype = 'IMPC Status'"} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    if not rv:
      print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
      sys.exit(1)

  start_time = time.time()
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  line_ct = wcl(IMPC_FILE)
  if not args['--quiet']:
    print "\nProcessing %d rows from input file %s" % (line_ct, IMPC_FILE)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  ct = 0
  skip_ct = 0
  ti1_ct = 0
  ti2_ct = 0
  dba_err_ct = 0
  annots = []
  with open(IMPC_FILE, 'rU') as csvfile:
    csvreader = csv.DictReader(csvfile)
    for d in csvreader:
      ct += 1
      pbar.update(ct)
      sym = d['Gene'].upper()
      targets = dba.find_targets({'sym': sym})
      if not targets:
        targets = dba.find_targets_by_xref({'xtype': 'MGI ID', 'value': d['MGI Accession']})
      if not targets:
        s['notfnd'].add("%s,%s"%(d['Gene'], d['MGI Accession']))
        logger.warn("No target found for %s,%s" % (d['Gene'], d['MGI Accession']))
        continue
      if not d['Best Status'] and not d['# Clones']:
        skip_ct += 1
        continue
      tids = list()
      tdls = list()
      for t in targets:
        d['TCRD ID'] = t['id']
        d['TDL'] = t['tdl']
        annots.append(d)
        pid = t['components']['protein'][0]['id']
        if not d['Best Status']:
          status = '?'
        else:
          status = d['Best Status']
        rv = dba.ins_tdl_info({'protein_id': pid, 'itype': 'IMPC Status',
                               'string_value': status})
        if rv:
          ti1_ct += 1
        else:
          dba_err_ct += 1
        if not d['# Clones']:
          continue
        rv = dba.ins_tdl_info({'protein_id': pid, 'itype': 'IMPC Clones',
                               'string_value': d['# Clones']})
        if rv:
          ti2_ct += 1
        else:
          dba_err_ct += 1
      tids.append(str(t['id']))
      tdls.append(t['tdl'])
      d['TCRD ID'] = "|".join(tids)
      d['TDL'] = "|".join(tdls)
  pbar.finish()
  
  if not args['--quiet']:
    print "%d rows processed." % ct
  print "Inserted %d new 'IMPC Status' tdl_info rows" % ti1_ct
  print "Inserted %d new 'IMPC Clones' tdl_info rows" % ti2_ct
  print "Skipped %d rows with no relevant info" % skip_ct
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)
  if len(s['notfnd']) > 0:
    print "No target found for %d rows. See logfile %s for details." % (len(s['notfnd']), logfile)
  s.close()
  # Output annots
  if not args['--quiet']:
    print "Writing %d annotated rows to file %s." % (len(annots), OUT_FILE)
  with open(OUT_FILE, 'wb') as outfile:
    dict_writer = csv.DictWriter(outfile, annots[0].keys())
    dict_writer.writeheader()
    dict_writer.writerows(annots)
    
def wcl(fname):
  with open(fname) as f:
    for i, l in enumerate(f):
      pass
  return i + 1

def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])

if __name__ == '__main__':
  print "\n%s (v%s) [%s]:" % (PROGRAM, __version__, time.strftime("%c"))
  start_time = time.time()
  load()
  elapsed = time.time() - start_time
  print "\n%s: Done. Elapsed time: %s\n" % (PROGRAM, secs2str(elapsed))
