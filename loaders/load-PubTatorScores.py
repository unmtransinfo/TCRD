#!/usr/bin/env python
# Time-stamp: <2019-04-11 10:08:38 smathias>
"""Load PubTator PubMed Score tdl_infos in TCRD from TSV file.

Usage:
    load-PubTatorScores.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-PubTatorScores.py -h | --help

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
  -d --debug           : turn on debugging output
  -? --help            : print this message and exit 
"""
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2016-2019, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.2.0"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import urllib
import csv
import logging
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd6logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
DOWNLOAD_DIR = '../data/JensenLab/'
BASE_URL = 'http://download.jensenlab.org/KMC/Medline/'
FILENAME = 'pubtator_counts.tsv'

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
  dataset_id = dba.ins_dataset( {'name': 'PubTator Text-mining Scores', 'source': 'File %s'%BASE_URL+FILENAME, 'app': PROGRAM, 'app_version': __version__, 'url': 'https://www.ncbi.nlm.nih.gov/CBBresearch/Lu/Demo/PubTator/', 'comments': 'PubTator data was subjected to the same counting scheme used to generate JensenLab PubMed Scores.'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'ptscore'},
            {'dataset_id': dataset_id, 'table_name': 'tdl_info', 'where_clause': "itype = 'PubTator PubMed Score'"} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  ptscores = {} # protein.id => sum(all scores)
  pts_ct = 0
  dba_err_ct = 0
  infile = DOWNLOAD_DIR + FILENAME
  line_ct = slmf.wcl(infile)
  if not args['--quiet']:
    print "\nProcessing {} lines in file {}".format(line_ct, infile)
  with open(infile, 'rU') as tsv:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    geneid2pid = {}
    notfnd = set()
    for row in tsvreader:
      # NCBI Gene ID  year  score
      ct += 1
      pbar.update(ct)
      gidstr = row[0].replace(',', ';')
      geneids = gidstr.split(';')
      for geneid in geneids:
        if not geneid or '(tax:' in geneid:
          continue
        if geneid in geneid2pid:
          # we've already found it
          pids = geneid2pid[geneid]
        elif geneid in notfnd:
          # we've already not found it
          continue
        else:
          targets = dba.find_targets({'geneid': geneid})
          if not targets:
            notfnd.add(geneid)
            logger.warn("No target found for {}".format(geneid))
            continue
          pids = []
          for target in targets:
            pids.append(target['components']['protein'][0]['id'])
            geneid2pid[geneid] = pids # save this mapping so we only lookup each target once
        for pid in pids:
          rv = dba.ins_ptscore({'protein_id': pid, 'year': row[1], 'score': row[2]} )
          if rv:
            pts_ct += 1
          else:
            dba_err_ct += 1
          if pid in ptscores:
            ptscores[pid] += float(row[2])
          else:
            ptscores[pid] = float(row[2])
  pbar.finish()
  print "{} lines processed.".format(ct)
  print "  Inserted {} new ptscore rows for {} targets.".format(pts_ct, len(ptscores))
  if notfnd:
    print "No target found for {} NCBI Gene IDs. See logfile {} for details.".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)
  
  print "\nLoading {} PubTator Score tdl_infos".format(len(ptscores))
  ct = 0
  ti_ct = 0
  dba_err_ct = 0
  for pid,score in ptscores.items():
    ct += 1
    rv = dba.ins_tdl_info({'protein_id': pid, 'itype': 'PubTator Score', 
                           'number_value': score} )
    if rv:
      ti_ct += 1
    else:
      dba_err_ct += 1
  print "{} processed".format(ct)
  print "Inserted {} new PubTator PubMed Score tdl_info rows".format(ti_ct)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)


if __name__ == '__main__':
  print "\n{} (v{}) [{}]:".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  start_time = time.time()
  download(args)
  load(args)
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))
