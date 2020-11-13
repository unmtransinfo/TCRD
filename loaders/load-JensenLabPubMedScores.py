#!/usr/bin/env python
# Time-stamp: <2020-11-12 08:49:26 smathias>
"""Load JensenLab PubMed Score tdl_infos in TCRD from TSV file.

Usage:
    load-JensenLabPubMedScores.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-JensenLabPubMedScores.py -h | --help

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
__copyright__ = "Copyright 2014-2020, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "3.0.0"

import os,sys,time
from docopt import docopt
from TCRD7 import DBAdaptor
import urllib
import csv
import logging
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd6logs"
#LOGDIR = "./tcrd7logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
DOWNLOAD_DIR = '../data/JensenLab/'
BASE_URL = 'http://download.jensenlab.org/KMC/Medline/'
FILENAME = 'protein_counts.tsv'

def download(args):
  if os.path.exists(DOWNLOAD_DIR + FILENAME):
    os.remove(DOWNLOAD_DIR + FILENAME)
  start_time = time.time()
  if not args['--quiet']:
    print "\nDownloading ", BASE_URL + FILENAME
    print "         to ", DOWNLOAD_DIR + FILENAME
  urllib.urlretrieve(BASE_URL + FILENAME, DOWNLOAD_DIR + FILENAME)
  elapsed = time.time() - start_time
  if not args['--quiet']:
    print "Done. Elapsed time: {}".format(slmf.secs2str(elapsed))

def load(args, dba, logfile, logger):
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  ensp2pids = {}
  pmscores = {} # protein.id => sum(all scores)
  pms_ct = 0
  upd_ct = 0
  notfnd = {}
  dba_err_ct = 0
  infile = DOWNLOAD_DIR + FILENAME
  line_ct = slmf.wcl(infile)
  if not args['--quiet']:
    print "\nProcessing {} input lines in file {}".format(line_ct, infile)
  with open(infile, 'rU') as tsv:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    for row in tsvreader:
      # sym  year  score
      ct += 1
      pbar.update(ct)
      if not row[0].startswith('ENSP'): continue
      ensp = row[0]
      if ensp in ensp2pids:
        # we've already found it
        pids = ensp2pids[ensp]
      elif ensp in notfnd:
        # we've already not found it
        continue
      else:
        targets = dba.find_targets({'stringid': ensp})
        if not targets:
          targets = dba.find_targets_by_xref({'xtype': 'STRING', 'value': '9606.'+ensp})
          if not targets:
            notfnd[ensp] = True
            logger.warn("No target found for {}".format(ensp))
            continue
        pids = []
        for target in targets:
          pids.append(target['components']['protein'][0]['id'])
        ensp2pids[ensp] = pids # save this mapping so we only lookup each target once
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
  print "{} input lines processed.".format(ct)
  print "  Inserted {} new pmscore rows for {} targets".format(pms_ct, len(pmscores))
  if len(notfnd) > 0:
    print "No target found for {} STRING IDs. See logfile {} for details.".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)
  
  print "\nLoading {} JensenLab PubMed Score tdl_infos".format(len(pmscores.keys()))
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
  print "{} processed".format(ct)
  print "  Inserted {} new JensenLab PubMed Score tdl_info rows".format(ti_ct)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format((dba_err_ct, logfile))


if __name__ == '__main__':
  print "\n%s (v%s) [%s]:\n" % (PROGRAM, __version__, time.strftime("%c"))
  
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  if args['--logfile']:
    logfile =  args['--logfile']
  else:
    logfile = LOGFILE
  loglevel = int(args['--loglevel'])
  logger = logging.getLogger(__name__)
  logger.setLevel(loglevel)
  if not args['--debug']:
    logger.propagate = False # turns off console logging
  fh = logging.FileHandler(LOGFILE)
  fmtr = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
  fh.setFormatter(fmtr)
  logger.addHandler(fh)

  dba_params = {'dbhost': args['--dbhost'], 'dbname': args['--dbname'], 'logger_name': __name__}
  dba = DBAdaptor(dba_params)
  dbi = dba.get_dbinfo()
  logger.info("Connected to TCRD database {} (schema ver {}; data ver {})".format(args['--dbname'], dbi['schema_ver'], dbi['data_ver']))
  if not args['--quiet']:
    print "Connected to TCRD database {} (schema ver {}; data ver {})".format(args['--dbname'], dbi['schema_ver'], dbi['data_ver'])

  download(args)
  start_time = time.time()
  load(args, dba, logfile, logger)
  elapsed = time.time() - start_time

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'JensenLab PubMed Text-mining Scores', 'source': 'File %s'%BASE_URL+FILENAME, 'app': PROGRAM, 'app_version': __version__, 'url': BASE_URL} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'pmscore'},
            {'dataset_id': dataset_id, 'table_name': 'tdl_info', 'where_clause': "itype = 'JensenLab PubMed Score'"} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    if not rv:
      print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
      sys.exit(1)
      
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))
