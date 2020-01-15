#!/usr/bin/env python
# Time-stamp: <2019-08-26 14:18:22 smathias>
"""Load patent counts into TCRD from CSV file.

Usage:
    load-EBIPatentCounts.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>] 
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
  -d --debug           : turn on debugging output
  -? --help            : print this message and exit 
"""
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2015-2019, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "3.0.0"

import os,sys,time
from docopt import docopt
from TCRDMP import DBAdaptor
import csv
import urllib
import logging
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd6logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
BASE_URL = 'ftp://ftp.ebi.ac.uk/pub/databases/chembl/IDG/patent_counts/'
DOWNLOAD_DIR = '../data/EBI/patent_counts/'
FILENAME = 'latest'

def download(args):
  if os.path.exists(DOWNLOAD_DIR + FILENAME):
    os.rename(DOWNLOAD_DIR + FILENAME, DOWNLOAD_DIR + FILENAME + '.bak')
  if not args['--quiet']:
    print "\nDownloading ", BASE_URL + FILENAME
    print "         to ", DOWNLOAD_DIR + FILENAME
  urllib.urlretrieve(BASE_URL + FILENAME, DOWNLOAD_DIR + FILENAME)
  if not args['--quiet']:
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

  # DBAdaptor uses same logger as main()
  dba_params = {'dbhost': args['--dbhost'], 'dbname': args['--dbname'], 'logger_name': __name__}
  dba = DBAdaptor(dba_params)
  dbi = dba.get_dbinfo()
  logger.info("Connected to TCRD database {} (schema ver {}; data ver {})".format(args['--dbname'], dbi['schema_ver'], dbi['data_ver']))
  if not args['--quiet']:
    print "\nConnected to TCRD database {} (schema ver {}; data ver {})".format(args['--dbname'], dbi['schema_ver'], dbi['data_ver'])

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'EBI Patent Counts', 'source': 'File %s'%BASE_URL+FILENAME, 'app': PROGRAM, 'app_version': __version__, 'url': 'https://www.surechembl.org/search/', 'comments': 'Patents from SureChEMBL were tagged using the JensenLab tagger.'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'patent_count'},
            {'dataset_id': dataset_id, 'table_name': 'tdl_info', 'where_clause': "itype = 'EBI Total Patent Count'"} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]

  patent_cts = {}
  notfnd = set()
  pc_ct = 0
  dba_err_ct = 0
  fname = DOWNLOAD_DIR + FILENAME
  line_ct = slmf.wcl(fname)
  if not args['--quiet']:
    print "\nProcessing {} lines in file {}".format(line_ct, fname)
  with open(fname, 'rU') as csvfile:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    csvreader = csv.reader(csvfile)
    header = csvreader.next() # skip header line
    ct = 0
    for row in csvreader:
      ct += 1
      up = row[0]
      targets = dba.find_targets({'uniprot': up})
      if not targets:
        targets = dba.find_targets_by_alias({'type': 'UniProt', 'value': up})
        if not targets:
          notfnd.add(up)
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
      pbar.update(ct)
  pbar.finish()
  for up in notfnd:
    logger.warn("No target found for {}".format(up))
  print "{} lines processed.".format(ct)
  print "Inserted {} new patent_count rows for {} proteins".format(pc_ct, len(patent_cts))
  if notfnd:
    print "No target found for {} UniProts. See logfile {} for details.".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)
    
  if not args['--quiet']:
    print "\nLoading {} Patent Count tdl_infos".format(len(patent_cts))
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
  print "  {} processed".format(ct)
  print "  Inserted {} new EBI Total Patent Count tdl_info rows".format(ti_ct)
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
