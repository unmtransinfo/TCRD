#!/usr/bin/env python
# Time-stamp: <2016-11-28 12:36:02 smathias>
"""Load JensenLab PubMed Score tdl_infos in TCRD from TSV file.

Usage:
    load-JensenLabPubMedScores.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-JensenLabPubMedScores.py -h | --help

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
__copyright__ = "Copyright 2014-2016, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.0.0"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import urllib
import csv
import shelve
import logging
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
DBHOST = 'localhost'
DBPORT = 3306
DBNAME = 'tcrdev'
LOGFILE = "%s.log" % PROGRAM
SHELF_FILE = 'tcrd4logs/protein_counts_not-found.db'
DOWNLOAD_DIR = '../data/JensenLab/'
BASE_URL = 'http://download.jensenlab.org/KMC/Medline/'
FILENAME = 'protein_counts.tsv'

def download():
  if os.path.exists(DOWNLOAD_DIR + FILENAME):
    os.remove(DOWNLOAD_DIR + FILENAME)
  start_time = time.time()
  print "\nDownloading ", BASE_URL + FILENAME
  print "         to ", DOWNLOAD_DIR + FILENAME
  urllib.urlretrieve(BASE_URL + FILENAME, DOWNLOAD_DIR + FILENAME)
  elapsed = time.time() - start_time
  print "Done. Elapsed time: %s" % secs2str(elapsed)

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

  # Use logger from this module
  dba_params = {'dbhost': args['--dbhost'], 'dbname': args['--dbname'], 'logger_name': __name__}
  dba = DBAdaptor(dba_params)
  dbi = dba.get_dbinfo()
  logger.info("Connected to TCRD database %s (schema ver %s; data ver %s)", args['--dbname'], dbi['schema_ver'], dbi['data_ver'])
  if not args['--quiet']:
    
    print "\nConnected to TCRD database %s (schema ver %s; data ver %s)" % (args['--dbname'], dbi['schema_ver'], dbi['data_ver'])

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'JensenLab PubMed Text-mining Scores', 'source': 'File %s'%BASE_URL+FILENAME, 'app': PROGRAM, 'app_version': __version__, 'url': BASE_URL} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % dba_logfile
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'pmscore'},
            {'dataset_id': dataset_id, 'table_name': 'tdl_info', 'where_clause': "itype = 'JensenLab PubMed Score'"} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    if not rv:
      print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
      sys.exit(1)
  
  start_time = time.time()
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pmscores = {} # protein.id => sum(all scores)
  
  s = shelve.open(SHELF_FILE, writeback=True)
  s['notfnd'] = set()
  pms_ct = 0
  upd_ct = 0
  dba_err_ct = 0
  infile = DOWNLOAD_DIR + FILENAME
  line_ct = wcl(infile)
  if not args['--quiet']:
    print "\nProcessing %d input lines in file %s" % (line_ct, infile)
  with open(infile, 'rU') as tsv:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    ensp2pid = {}
    for row in tsvreader:
      # sym  year  score
      ct += 1
      pbar.update(ct)
      if not row[0].startswith('ENSP'): continue
      ensp = row[0]
      if ensp in ensp2pid:
        # we've already found it
        pids = ensp2pid[ensp]
      elif ensp in s['notfnd']:
        # we've already not found it
        continue
      else:
        targets = dba.find_targets({'stringid': ensp})
        if not targets:
          s['notfnd'].add(ensp)
          continue
        pids = []
        for target in targets:
          pids.append(target['components']['protein'][0]['id'])
          ensp2pid[ensp] = pids # save this mapping so we only lookup each target once
      for pid in pids:
        rv = dba.ins_pmscore({'protein_id': pid, 'year': row[1], 'score': row[2]} )
        if rv:
          pms_ct += 1
        else:
          dba_err_ct += 1
        if pid in pmscores:
          pmscores[pid] += float(row[2])
        else:
          pmscores[pid] = float(row[2])
  pbar.finish()

  elapsed = time.time() - start_time
  print "%d input lines processed. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "  %d targets have JensenLab PubMed Scores" % len(pmscores.keys())
  print "  Inserted %d new pmscore rows" % pms_ct
  if len(s['notfnd']) > 0:
    print "No target found for %d STRING IDs. Saved to file: %s" % (len(s['notfnd']), SHELF_FILE)
  s.close()
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)
  
  print "\nLoading %d JensenLab PubMed Score tdl_infos" % len(pmscores.keys())
  ct = 0
  ti_ct = 0
  dba_err_ct = 0
  for pid,score in pmscores.items():
    ct += 1
    rv = dba.ins_tdl_info({'protein_id': pid, 'itype': 'JensenLab PubMed Score', 
                           'number_value': score} )
    if rv:
      ti_ct += 1
    else:
      dba_err_ct += 1
  print "  %d processed" % ct
  print "  Inserted %d new JensenLab PubMed Score tdl_info rows" % ti_ct
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, dba_logfile)

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
