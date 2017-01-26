#!/usr/bin/env python
# Time-stamp: <2017-01-12 09:43:23 smathias>
"""Load KEGG Pathway links into TCRD via KEGG REST API.

Usage:
    load-PathwaysKEGG.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
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
  -d --debug DEBUGL    : set debugging output level (0-3) [default: 0]
  -? --help            : print this message and exit 
"""
__author__ = "Steve Mathias"
__email__ = "smathias@salud.unm.edu"
__org__ = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2015-2017, Steve Mathias"
__license__ = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__ = "2.0.0"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import requests
from bs4 import BeautifulSoup
import logging
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
KEGG_BASE_URL = 'http://rest.kegg.jp'

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
    print "Connected to TCRD database %s (schema ver %s; data ver %s)" % (args['--dbname'], dbi['schema_ver'], dbi['data_ver'])

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'KEGG Pathways', 'source': 'API at %s'%KEGG_BASE_URL, 'app': PROGRAM, 'app_version': __version__, 'url': 'http://www.genome.jp/kegg/pathway.html'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'pathway', 'where_clause': "pwtype = 'KEGG'"})
  if not rv:
    print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
    sys.exit(1)
    
  print "\nGetting KEGG pathway to gene list"
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

  start_time = time.time()
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pw_ct = len(kpw2geneids.keys())
  print "Processing mapping of %d KEGG Pathways to genes" % pw_ct
  pbar = ProgressBar(widgets=pbar_widgets, maxval=pw_ct).start()  
  ct = 0
  gid_mark = {}
  notfnd = {}
  net_errs = {}
  xml_errs = []
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
      logger.error("Bad API response for %s: %s" % (kpw, status))
      net_errs[kpw] = r.status_code
      continue
    soup = BeautifulSoup(r.text, "xml")
    if not soup.find('pathway'):
      logger.error("XML parsing error for KEGG Pathway: %s" % kpw)
      xml_errs.append(kpw)
      continue
    pw = soup.find('pathway').attrs
    for geneid in geneids:
      gid_mark[geneid] = True
      targets = dba.find_targets({'geneid': geneid})
      if not targets:
        notfnd[geneid] = True
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
  elapsed = time.time() - start_time
  print "Processed %d KEGG Pathways. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "  Inserted %d pathway rows" % pw_ct
  if notfnd:
    print "WARNNING: %d (of %d) KEGG IDs did not find a TCRD target." % (len(notfnd), len(gid_mark))
  if len(net_errs.keys()) > 0:
    print "WARNNING: %d network errors occurred. See logfile %s for details." % (len(net_errs), logfile)
  if len(xml_errs) > 0:
    print "WARNNING: %d XML parsing errors occurred. See logfile %s for details." % (len(xml_errs), logfile)
  if dba_err_ct > 0:
    print "WARNNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)
  

def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])

if __name__ == '__main__':
  print "\n%s (v%s) [%s]:\n" % (PROGRAM, __version__, time.strftime("%c"))
  load()
  print "\n%s: Done.\n" % PROGRAM
