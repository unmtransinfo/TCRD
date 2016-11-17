#!/usr/bin/env python
# Time-stamp: <2016-11-17 12:47:21 smathias>
"""Load HGNC annotations for TCRD targets via web API.

Usage:
    load-HGNC.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-HGNC.py -h | --help

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
__author__ = "Steve Mathias"
__email__ = "smathias@salud.unm.edu"
__org__ = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2014-2016, Steve Mathias"
__license__ = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__ = "2.0.0"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import logging
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
import shelve
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
DBHOST = 'localhost'
DBPORT = 3306
DBNAME = 'tcrdev'
LOGFILE = "%s.log" % PROGRAM
HGNC_URL = 'http://rest.genenames.org/fetch'
SHELF_FILE = 'tcrd4logs/load-HGNC.db'

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
  dataset_id = dba.ins_dataset( {'name': 'HGNC', 'source': 'Web API at %s'%HGNC_URL, 'app': PROGRAM, 'app_version': __version__, 'columns_touched': 'protein.sym/geneid/chr; xref.* where xtype is HGNC ID and MGI ID', 'url': 'http://www.genenames.org/'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'protein', 'column_name': 'sym', 'comment': "This cnly is only updated with HGNC data if data from UniProt is absent ir discrepant."},
            {'dataset_id': dataset_id, 'table_name': 'protein', 'column_name': 'geneid', 'comment': "This cnly is only updated with HGNC data if data from UniProt is absent ir discrepant."},
            {'dataset_id': dataset_id, 'table_name': 'protein', 'column_name': 'chr'} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    if not rv:
      print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
      sys.exit(1)

  start_time = time.time()

  s = shelve.open(SHELF_FILE, writeback=True)
  s['loaded'] = []
  s['retries'] = []
  s['notfound'] = []
  s['counts'] = defaultdict(int)
  
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  tct = dba.get_target_count(idg=False)
  if not args['--quiet']:
    print "\nLoading HGNC annotations for %d TCRD targets" % tct
  logger.info("Loading HGNC annotations for %d TCRD targets" % tct)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=tct).start()  
  ct = 0
  for target in dba.get_targets():
    ct += 1
    pbar.update(ct)
    logger.info("Processing target %d" % target['id'])
    p = target['components']['protein'][0]
    pid = p['id']
    # try by NCBI geneid
    if p['geneid']:
      (status, headers, xml) = get_hgnc(geneid=p['geneid'])
      if not status or status != 200:
        logger.error("Bad API response for %s" % p['geneid'])
        s['retries'].append(target['id'])
        continue
    else:
      # try by uniprot
      (status, headers, xml) = get_hgnc(uniprot=p['uniprot'])
      if not status or status != 200:
        logger.error("Bad API response for %s" % p['uniprot'])
        s['retries'].append(target['id'])
        continue
    hgnc_annotations = parse_hgnc_xml(xml)
    if not hgnc_annotations:
      s['notfound'].append(target['id'])
      continue
    load_annotations(dba, target, dataset_id, hgnc_annotations, s)
    pbar.update(ct)
  pbar.finish()
  print "Processed %d targets." % ct
  print "Loaded HGNC annotations for %d targets" % len(s['loaded'])
  if len(s['retries']) > 0:
    print "Total targets remaining for retries: %d " % len(s['retries'])

  loop = 1
  while len(s['retries']) > 0:
    if not args['--quiet']:
      print "\nRetry loop %d: Loading HGNC annotations for %d TCRD targets" % (loop, len(s['retries']))
    logger.info("Retry loop %d: Loading HGNC annotations for %d TCRD targets" % (loop, len(s['retries'])))
    pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
    pbar = ProgressBar(widgets=pbar_widgets, maxval=len(s['retries'])).start()
    ct = 0
    act = 0
    for i,tid in enumerate(s['retries']):
      ct += 1
      target = dba.get_target(tid, include_annotations=True)
      logger.info("Processing target %d" % tid)
      p = target['components']['protein'][0]
      pid = p['id']
      # try by NCBI geneid
      if p['geneid']:
        (status, headers, xml) = get_hgnc(geneid=p['geneid'])
        if not status or status != 200:
          logger.error("Bad API response for %s" % p['geneid'])
          s['retries'].append(target['id'])
          continue
      # try by uniprot
      else:
        (status, headers, xml) = get_hgnc(uniprot=p['uniprot'])
        if not status or status != 200:
          logger.error("Bad API response for %s" % p['uniprot'])
          s['retries'].append(target['id'])
          continue
      hgnc_annotations = parse_hgnc_xml(xml)
      if not hgnc_annotations:
        s['notfound'].append(target['id'])
        continue
      load_annotations(dba, target, dataset_id, hgnc_annotations, s)
      act += 1
      del s['retries'][i]
      pbar.update(ct)
    loop += 1
    pbar.finish()
    print "Processed %d targets." % ct
    print "  Annotated %d additional targets" % act
    print "  Total annotated targets: %d" % len(s['loaded'])
    if len(s['retries']) > 0:
      print "Total targets remaining for retries: %d " % len(s['retries'])
  
  print "\nUpdated/Inserted %d HGNC ID xrefs" % s['counts']['hgncid']
  print "Inserted %d new protein.sym values" % s['counts']['sym']
  print "Updated %d discrepant protein.sym values" % s['counts']['symdiscr']
  print "Updated/Inserted %d protein.chr values" % s['counts']['chr']
  print "Updated/Inserted %d protein.geneid values" % s['counts']['geneid']
  print "Updated/Inserted %d MGI ID xrefs" % s['counts']['mgi']
  if len(s['notfound']) > 0:
    print "WARNNING: %d targets did not find an HGNC record." % len(s['notfound'])
  if s['counts']['dba_err'] > 0:
    print "WARNNING: %d DB errors occurred. See logfile %s for details." % (len(shelf['counts']['dba_err']), logfile)
    
  elapsed = time.time() - start_time
  print "\n%s: Done. Elapsed time: %s" % (PROGRAM, secs2str(elapsed))
  print


def get_hgnc(sym=None, hgnc_id=None, geneid=None, uniprot=None):
  if sym:
    url = "%s/symbol/%s" % (HGNC_URL, sym)
  elif hgnc_id:
    url = "%s/hgnc_id/%s" % (HGNC_URL, hgnc_id)
  elif geneid:
    url = "%s/entrez_id/%s" % (HGNC_URL, geneid)
  elif uniprot:
    url = "%s/uniprot_ids/%s" % (HGNC_URL, uniprot)
  else:
    print "No query parameter sent to get_hgnc()"
    return False
  attempts = 0
  while attempts <= 5:
    try:
      r = requests.get(url)
      break
    except:
      attempts += 1
      time.sleep(2)
  if r:
    return (r.status_code, r.headers, r.text)
  else:
    return (False, False, False)

def parse_hgnc_xml(xml):
  annotations = {}
  soup = BeautifulSoup(xml, "xml")
  d = soup.find('doc')
  if not d:
    return False
  for s in d.findAll('str'):
    if s.attrs and 'name' in s.attrs:
      t = s.attrs['name']
      if t == 'hgnc_id':
        annotations['hgnc_id'] = s.text
      elif t == 'symbol':
        annotations['sym'] = s.text
      elif t == 'location':
        annotations['chr'] = s.text
      elif t == 'entrez_id':
        annotations['geneid'] = int(s.text)
    elif s.text.startswith('MGI'):
      annotations['mgi'] = s.text
  return annotations

def load_annotations(dba, t, dataset_id, hgnc_annotations, shelf):
  p = t['components']['protein'][0]
  pid = p['id']
  if 'hgnc_id' in hgnc_annotations:
    rv = dba.ins_xref({'protein_id': pid, 'xtype': 'HGNC', 'dataset_id': dataset_id, 'value': hgnc_annotations['hgnc_id']})
    if rv:
      shelf['counts']['hgncid'] += 1
    else:
      shelf['counts']['dba_err'] += 1
  if 'sym' in hgnc_annotations:
    if p['sym'] == None:
      rv = dba.upd_protein(pid, 'sym', hgnc_annotations['sym'])
      if rv:
        shelf['counts']['sym'] += 1
      else:
        shelf['counts']['dba_err'] += 1
    if p['sym'] != hgnc_annotations['sym']:
      rv = dba.upd_protein(pid, 'sym', hgnc_annotations['sym'])
      if rv:
        shelf['counts']['symdiscr'] += 1
      else:
        shelf['counts']['dba_err'] += 1
  if 'chr' in hgnc_annotations:
    if p['chr'] == None or p['chr'] != hgnc_annotations['chr']:
      rv = dba.upd_protein(pid, 'chr', hgnc_annotations['chr'])
      if rv:
        shelf['counts']['chr'] += 1
      else:
        shelf['counts']['dba_err'] += 1
  if 'geneid' in hgnc_annotations:
    if p['geneid'] == None or p['geneid'] != hgnc_annotations['geneid']:
      rv = dba.upd_protein(pid, 'geneid', hgnc_annotations['geneid'])
      if rv:
        shelf['counts']['geneid'] += 1
      else:
        shelf['counts']['dba_err'] += 1
  if 'mgi' in hgnc_annotations:
    rv = dba.ins_xref({'protein_id': pid, 'xtype': 'MGI ID', 'dataset_id': dataset_id, 'value': hgnc_annotations['mgi']})
    if rv:
      shelf['counts']['mgi'] += 1
    else:
      shelf['counts']['dba_err'] += 1
  shelf['loaded'].append(t['id'])

def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])


if __name__ == '__main__':
    main()
