#!/usr/bin/env python
# Time-stamp: <2018-03-21 15:10:44 smathias>
"""Load Jackson Labs phenotype data into TCRD from TSV files.

Usage:
    load-JAXPhenotypes.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-JAXPhenotypes.py -? | --help

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
__copyright__ = "Copyright 2015-2018, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.2.0"

import os,sys,time,re
from docopt import docopt
from TCRD import DBAdaptor
import logging
import csv
import urllib
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd5logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
DOWNLOAD_DIR = '../data/JAX/'
BASE_URL = 'http://www.informatics.jax.org/downloads/reports/'
MPO_FILE = 'VOC_MammalianPhenotype.rpt'
PT_FILE = 'HMD_HumanPhenotype.rpt'

def download(args):
  for f in [MPO_FILE, PT_FILE]:
    if os.path.exists(DOWNLOAD_DIR + f):
      os.remove(DOWNLOAD_DIR + f)
    if not args['--quiet']:
      print "\nDownloading", BASE_URL + f
      print "         to", DOWNLOAD_DIR + f
    urllib.urlretrieve(BASE_URL + f, DOWNLOAD_DIR + f)

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

  dba_params = {'dbhost': args['--dbhost'], 'dbname': args['--dbname'], 'logger_name': __name__}
  dba = DBAdaptor(dba_params)
  dbi = dba.get_dbinfo()
  logger.info("Connected to TCRD database {} (schema ver {}; data ver {})".format(args['--dbname'], dbi['schema_ver'], dbi['data_ver']))
  if not args['--quiet']:
    print "\nConnected to TCRD database {} (schema ver {}; data ver {})".format(args['--dbname'], dbi['schema_ver'], dbi['data_ver'])

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'JAX/MGI Mouse/Human Orthology Phenotypes', 'source': 'File %s from ftp.informatics.jax.org'%PT_FILE, 'app': PROGRAM, 'app_version': __version__, 'url': 'http://www.informatics.jax.org/'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'phenotype', 'where_clause': "ptype = 'JAX/MGI Human Ortholog Phenotyp'"},
            {'dataset_id': dataset_id, 'table_name': 'xref', 'where_clause': "dataset_id = %d"%dataset_id} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)
  
  mpo = {}
  fn = DOWNLOAD_DIR + MPO_FILE
  line_ct = slmf.wcl(fn)
  if not args['--quiet']:
    print "\nProcessing {} lines in MPO file {}".format(line_ct, fn)
  with open(fn, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    tsvreader.next() # skip header line
    for row in tsvreader:
      mpo[row[0]] = {'name': row[1], 'description': row[2]}
  if not args['--quiet']:
    print "  Saved {} MPO entries".format(len(mpo.keys()))

  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  fn = DOWNLOAD_DIR + PT_FILE
  line_ct = slmf.wcl(fn)
  if not args['--quiet']:
    print "\nProcessing {} lines from input file {}".format(line_ct, fn)
  with open(fn, 'rU') as tsv:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start()
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    pt_ct = 0
    mgixr_ct = 0
    pmark = {}
    notfnd = set()
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
      #print "[DEBUG] line %d: ``%s''" % (ct, row[5])
      if not row[6] or row[6] == '':
        continue
      sym = row[0]
      geneid = row[1]
      k = "%s|%s"%(sym,geneid)
      if k in notfnd:
        continue
      targets = dba.find_targets({'sym': sym}, idg = False)
      if not targets:
        targets = dba.find_targets({'geneid': geneid}, idg = False)
      if not targets:
        notfnd.add(k)
        logger.warn("No target found for {}".format(k))
        continue
      for t in targets:
        pid = t['components']['protein'][0]['id']
        pmark[pid] = True
        rv = dba.ins_xref({'protein_id': pid, 'xtype': 'MGI ID', 'dataset_id': dataset_id, 'value': row[4]})
        if rv:
          mgixr_ct += 1
        else:
          dba_err_ct += 1
        for mpid in row[6].split():
          rv = dba.ins_phenotype({'protein_id': pid, 'ptype': 'JAX/MGI Human Ortholog Phenotype', 'term_id': mpid, 'term_name': mpo[mpid]['name'],' term_description': mpo[mpid]['description']})
          if rv:
            pt_ct += 1
          else:
            dba_err_ct += 1
      pbar.update(ct)
  pbar.finish()
  print "{} lines processed.".format(ct)
  print "Loaded {} new phenotype rows for {} targets".format(pt_ct, len(pmark.keys()))
  print "  Loaded/Skipped {} new MGI xrefs".format(mgixr_ct)
  if notfnd:
    print "No target found for {} gene symbols/ids. See logfile {} for details.".format(len(notfnd), logfile)
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
  


