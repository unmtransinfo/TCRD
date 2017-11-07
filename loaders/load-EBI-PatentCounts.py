#!/usr/bin/env python
# Time-stamp: <2017-06-22 10:02:21 smathias>
"""Load patent counts into TCRD from CSV file.

Usage:
    load-EBIPatentCounts.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>] 
    load-EBIPatentCounts.py -? | --help

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
__version__   = "2.1.0"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import csv
import logging
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
LOGFILE = "%s.log" % PROGRAM
BASE_URL = 'ftp://ftp.ebi.ac.uk/pub/databases/chembl/IDG/patent_counts/'
DOWNLOAD_DIR = '../data/EBI/patent_counts'
FILENAME = 'latest'
#INFILE = '../data/EBI/EBI_PatentCountsJensenTagger_20160711.csv'

def download():
  if os.path.exists(DOWNLOAD_DIR + FILENAME):
    os.rename(DOWNLOAD_DIR + FILENAME, DOWNLOAD_DIR + FILENAME + '.bak')
  print "\nDownloading ", BASE_URL + FILENAME
  print "         to ", DOWNLOAD_DIR + FILENAME
  urllib.urlretrieve(BASE_URL + FILENAME, DOWNLOAD_DIR + FILENAME)
  print "Done."

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

  # DBAdaptor uses same logger as main()
  dba_params = {'dbhost': args['--dbhost'], 'dbname': args['--dbname'], 'logger_name': __name__}
  dba = DBAdaptor(dba_params)
  dbi = dba.get_dbinfo()
  logger.info("Connected to TCRD database %s (schema ver %s; data ver %s)", args['--dbname'], dbi['schema_ver'], dbi['data_ver'])
  if not args['--quiet']:
    print "\nConnected to TCRD database %s (schema ver %s; data ver %s)" % (args['--dbname'], dbi['schema_ver'], dbi['data_ver'])

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'EBI Patent Counts', 'source': 'File %s'%BASE_URL+FILENAME, 'app': PROGRAM, 'app_version': __version__, 'url': 'https://www.surechembl.org/search/', 'comments': 'Patents from SureChEMBL were tagged using the JensenLab tagger.'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'patent_count'},
            {'dataset_id': dataset_id, 'table_name': 'tdl_info', 'where_clause': "itype = 'EBI Total Patent Count'"} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    if not rv:
      print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
      sys.exit(1)

  start_time = time.time()
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  patent_cts = {}
  notfnd = {}
  pc_ct = 0
  dba_err_ct = 0
  fname = BASE_URL + FILENAME
  line_ct = wcl(fname)
  if not args['--quiet']:
    print "\nProcessing %d data lines in file %s" % (line_ct, fname)
  with open(fname, 'rU') as csvfile:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    csvreader = csv.reader(csvfile)
    header = csvreader.next() # skip header line
    ct = 0
    for row in csvreader:
      ct += 1
      pbar.update(ct)
      up = row[0]
      targets = dba.find_targets({'uniprot': up})
      if not targets:
        targets = dba.find_targets_by_alias({'type': 'UniProt', 'value': up})
        if not targets:
          notfnd[up] = True
          continue
      pid = targets[0]['components']['protein'][0]['id']
      rv = dba.ins_patent_count({'protein_id': pid, 'year': row[2], 'count': row[3]} )
      if rv:
        pc_ct += 1
      else:
        dba_err_ct += 1
      if pid in patent_cts:
        patent_cts[pid] += int(row[3])
      else:
        patent_cts[pid] = int(row[3])
  pbar.finish()
  elapsed = time.time() - start_time
  print "%d input lines processed. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "\n%d targets have patent counts" % len(patent_cts.keys())
  print "Inserted %d new patent_count rows" % pc_ct
  if notfnd:
    print "No target found for %d symbols:" % len(notfnd)
    for up in notfnd.keys():
      print "  %s" % sym
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)
    
  if not args['--quiet']:
    print "\nLoading %d Patent Count tdl_infos" % len(patent_cts.keys())
  ct = 0
  ti_ct = 0
  dba_err_ct = 0
  for pid,count in patent_cts.items():
    ct += 1
    rv = dba.ins_tdl_info({'protein_id': pid, 'itype': 'EBI Total Patent Count', 
                           'integer_value': count} )
    if rv:
      ti_ct += 1
    else:
      dba_err_ct += 1
  print "  %d processed" % ct
  print "  Inserted %d new EBI Total Patent Count tdl_info rows" % ti_ct
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)

  if not args['--quiet']:
    print "\n%s: Done.\n" % PROGRAM
  

def wcl(fname):
  with open(fname) as f:
    for i, l in enumerate(f):
      pass
  return i + 1

def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])

if __name__ == '__main__':
  print "\n%s (v%s) [%s]:" % (PROGRAM, __version__, time.strftime("%c"))
  download()
  load()
  print "\n%s: Done.\n" % PROGRAM
