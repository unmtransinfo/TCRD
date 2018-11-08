#!/usr/bin/env python
# Time-stamp: <2018-05-31 10:47:29 smathias>
"""Load KEGG Pathway links into TCRD via KEGG REST API.

Usage:
    load-PathwaysKEGG.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-PathwaysKEGG.py -? | --help

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
__author__ = "Steve Mathias"
__email__ = "smathias@salud.unm.edu"
__org__ = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2015-2018, Steve Mathias"
__license__ = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__ = "2.1.0"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import requests
from bs4 import BeautifulSoup
import logging
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd5logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
KEGG_BASE_URL = 'http://rest.kegg.jp'

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
  dataset_id = dba.ins_dataset( {'name': 'KEGG Pathways', 'source': 'API at %s'%KEGG_BASE_URL, 'app': PROGRAM, 'app_version': __version__, 'url': 'http://www.genome.jp/kegg/pathway.html'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'pathway', 'where_clause': "pwtype = 'KEGG'"})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)
    
  print "\nMapping KEGG pathways to gene lists"
  kpw2geneids = {}
  url = "%s/link/hsa/pathway" % KEGG_BASE_URL
  r = None
  attempts = 0
  while attempts < 3:
    try:
      r = requests.get(url)
      break
    except Exception, e:
      attempts += 1
  assert r.status_code == 200, "Error: Could not retrieve KEGG pathway to gene list."
  for line in r.text.splitlines():
    [kpw,kg] = line.split('\t')
    geneid = kg.replace('hsa:', '')
    if kpw in kpw2geneids:
      kpw2geneids[kpw].append(geneid)
    else:
      kpw2geneids[kpw] = [geneid]

  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pw_ct = len(kpw2geneids.keys())
  print "Processing {} KEGG Pathways".format(pw_ct)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=pw_ct).start()  
  ct = 0
  gid_mark = {}
  notfnd = set()
  net_err_ct = 0
  xml_err_ct = 0
  pw_ct = 0
  dba_err_ct = 0
  for kpw,geneids in kpw2geneids.items():
    ct += 1
    url = "%s/get/%s/kgml" % (KEGG_BASE_URL, kpw)
    attempts = 0
    while attempts < 3:
      try:
        r = requests.get(url)
        break
      except Exception, e:
        attempts += 1
    if r.status_code != 200:
      logger.error("Bad API response for {}: {}".format(kpw, status))
      net_err_ct += 1
      continue
    soup = BeautifulSoup(r.text, "xml")
    if not soup.find('pathway'):
      logger.error("XML parsing error for KEGG Pathway: {}".format(kpw))
      xml_err_ct += 1
      continue
    pw = soup.find('pathway').attrs
    for geneid in geneids:
      gid_mark[geneid] = True
      if geneid in notfnd:
        continue
      targets = dba.find_targets({'geneid': geneid})
      if not targets:
        notfnd.add(geneid)
        logger.warn("No target found for Gene ID: {}".format(geneid))
        continue
      for t in targets:
        pid = t['components']['protein'][0]['id']
        rv = dba.ins_pathway({'protein_id': pid, 'pwtype': 'KEGG', 'name': pw['title'],
                              'id_in_source': pw['name'], 'url': pw['link']})
        if rv:
          pw_ct += 1
        else:
          dba_err_ct += 1
    pbar.update(ct)
  pbar.finish()
  print "Processed {} KEGG Pathways.".format(ct)
  print "  Inserted {} pathway rows".format(pw_ct)
  if notfnd:
    print "WARNNING: {} (of {}) KEGG IDs did not find a TCRD target.".format(len(notfnd), len(gid_mark))
  if net_err_ct > 0:
    print "WARNNING: {} network errors occurred. See logfile {} for details.".format(len(net_errs), logfile)
  if xml_err_ct > 0:
    print "WARNNING: {} XML parsing errors occurred. See logfile {} for details.".format(len(xml_errs), logfile)
  if dba_err_ct > 0:
    print "WARNNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)
  

if __name__ == '__main__':
  print "\n{} (v{}) [{}]:".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  start_time = time.time()
  load(args)
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))
