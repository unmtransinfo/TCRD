#!/usr/bin/env python
# Time-stamp: <2017-02-23 11:10:15 smathias>
"""Load Ma'ayan Lab Harmonizome data into TCRD via API.

Usage:
    load-Harmonizome.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-Harmonizome.py -? | --help

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
__copyright__ = "Copyright 2015-2016, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "1.4.1"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import urllib,json,codecs
import cPickle as pickle
import csv
import logging
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
LOGFILE = "%s.log" % PROGRAM
HARMO_API_BASE_URL = 'http://amp.pharm.mssm.edu/Harmonizome/'
SYM2PID_P = 'tcrd4logs/Sym2pidv4.p'
DATASET_DONE_FILE = 'tcrd4logs/DatasetsDone.txt'

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
  dataset_id = dba.ins_dataset( {'name': 'Harmonogram Data', 'source': "API at %s"%HARMO_API_BASE_URL, 'app': PROGRAM, 'app_version': __version__, 'url': 'http://amp.pharm.mssm.edu/Harmonizome/'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'gene_attribute'},
            {'dataset_id': dataset_id, 'table_name': 'gene_attribute_type'},
            {'dataset_id': dataset_id, 'table_name': 'hgram_cdf'} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    if not rv:
      print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
      sys.exit(1)

  if not os.path.exists(SYM2PID_P):
    print "\nFinding targets with Harmonizome genes"
    logger.info("Finding targets with Harmonizome genes")
    pickle_sym2pid(dba, logger, SYM2PID_P)
  print "\nLoading mapping of Harmonizome genes to TCRD targets from pickle file %s" % SYM2PID_P
  sym2pid = pickle.load( open(SYM2PID_P, 'rb') )
  print "  Got %d symbol to protein_id mappings" % len(sym2pid)

  start_time = time.time()
  if os.path.isfile(DATASET_DONE_FILE):
    # If we are restarting, this file has the names of datasets already loaded
    with open(DATASET_DONE_FILE) as f:
      datasets_done = f.read().splitlines()
  else:
    datasets_done = []
  datasets = get_datasets(HARMO_API_BASE_URL)
  print "\nProcessing %d Ma'ayan Lab datasets" % len(datasets)
  ct = 0
  gat_ct = 0
  total_ga_ct = 0
  err_ct = 0
  dba_err_ct = 0
  for dsname in datasets.keys():
    ct += 1
    ds_start_time = time.time()
    if dsname in datasets_done:
      print "  Skipping previously loaded dataset \"%s\"" % dsname
      continue
    ds_ga_ct = 0
    ds = get_dataset(HARMO_API_BASE_URL, datasets[dsname])
    if not ds:
      logger.error("Error getting dataset %s (%s)" % (dsname, datasets[dsname]))
      err_ct += 1
      continue
    if not args['--quiet']:
      print "  Processing dataset \"%s\" containing %d gene sets" % (dsname, len(ds['geneSets']))
    logger.info("Processing dataset \"%s\" containing %d gene sets" % (dsname, len(ds['geneSets'])))
    rsc = get_resource(HARMO_API_BASE_URL, ds['resource']['href'])
    gat_id = dba.ins_gene_attribute_type( {'name': ds['name'], 'association': ds['association'], 'description': rsc['description'], 'resource_group': ds['datasetGroup'], 'measurement': ds['measurement'], 'attribute_group': ds['attributeGroup'], 'attribute_type': ds['attributeType'], 'pubmed_ids': "|".join([str(pmid) for pmid in rsc['pubMedIds']]), 'url': rsc['url']} )
    if gat_id:
      gat_ct += 1
    else:
      dba_err_ct += 1
    for d in ds['geneSets']:
      name = d['name'].encode('utf-8')
      gs = get_geneset(HARMO_API_BASE_URL, d['href'])
      if not gs:
        logger.error("Error getting gene set %s (%s)" % (name, d['href']))
        err_ct += 1
        continue
      if 'associations' not in gs: # used to be 'features'
        logger.error("No associations in gene set %s" % name)
        err_ct += 1
        continue
      logger.info("  Processing gene set \"%s\" containing %d associations" % (name, len(gs['associations'])))
      ga_ct = 0
      for f in gs['associations']: # used to be 'features'
        sym = f['gene']['symbol']
        if sym not in sym2pid: continue # symbol does not map to a TCRD target
        rv = dba.ins_gene_attribute( {'protein_id': sym2pid[sym], 'gat_id': gat_id, 'name': name, 'value':  f['thresholdValue']} )
        if not rv:
          dba_err_ct += 1
        else:
          ga_ct += 1
      ds_ga_ct += ga_ct
      time.sleep(1)
    total_ga_ct += ds_ga_ct
    ds_elapsed = time.time() - ds_start_time
    logger.info("  Inserted a total of %d new gene_attribute rows for dataset %s. Elapsed time: %s" % (ds_ga_ct, dsname, secs2str(ds_elapsed)))
    if err_ct > 0:
      logger.info("  WARNING: Error getting %d gene set(s) " % err_ct)
    # Save dataset names that are loaded, in case we need to restart
    with open(DATASET_DONE_FILE, "a") as dsdfile:
      dsdfile.write(dsname+'\n')
  elapsed = time.time() - start_time
  print "\nProcessed %d Ma'ayan Lab datasets. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "Inserted %d new gene_attribute_type rows" % gat_ct
  print "Inserted a total of %d gene_attribute rows" % total_ga_ct
  if err_ct > 0:
    print "WARNING: %d errors occurred. See logfile %s for details." % (err_ct, logfile)
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)

  print "\n%s: Done." % PROGRAM
  print

def get_datasets(api_base_url):
  datasets = {}
  endpoint = '/api/1.0/dataset?'
  url = api_base_url + endpoint
  while 1:
    #print "[DEBUG] Fetching URL: %s" % url 
    try:
      # API returns 100 datasets at a time and gives endpoint for next 100 gene sets
      jsondata = json.loads(urllib.urlopen(url).read().decode('unicode_escape'),
                            encoding='utf_8')
    except Exception as e:
      #try again
      try:
        jsondata = json.loads(urllib.urlopen(url).read().decode('unicode_escape'), encoding='utf_8')
      except Exception as e:
        break
    if not jsondata['entities']: break
    for d in jsondata['entities']:
      datasets[d['name']] = d['href']
    #print "[DEBUG] Now have %d datasets" % len(datasets.keys()) 
    endpoint = jsondata['next']
    #print "[DEBUG] Next endpoint: %s" % endpoint
    url = api_base_url + endpoint
  return datasets

def get_dataset(api_base_url, endpoint):
  url = api_base_url + endpoint
  jsondata = None
  attempts = 0
  while attempts < 5:
    try:
      jsondata = json.loads(urllib.urlopen(url).read().decode('unicode_escape'), encoding='utf_8')
      break
    except Exception as e:
      attempts += 1
  if jsondata:
    return jsondata
  else:
    return False

def get_resource(api_base_url, endpoint):
  url = api_base_url + endpoint
  jsondata = None
  attempts = 0
  while attempts < 5:
    try:
      jsondata = json.loads(urllib.urlopen(url).read().decode('unicode_escape'), encoding='utf_8')
      break
    except Exception as e:
      attempts += 1
  if jsondata:
    return jsondata
  else:
    return False

def get_geneset(api_base_url, endpoint):
  url = api_base_url + endpoint
  jsondata = None
  attempts = 0
  while attempts < 5:
    try:
      jsondata = json.loads(urllib.urlopen(url).read().decode('unicode_escape'), encoding='utf_8')
      break
    except Exception as e:
      attempts += 1
  if jsondata:
    return jsondata
  else:
    return False

def get_gene(sym):
  url = 'http://amp.pharm.mssm.edu/Harmonizome/api/1.0/gene/' + sym
  #logger.debug("Getting %s" % url)
  jsondata = None
  attempts = 0
  while attempts < 5:
    try:
      jsondata = json.loads(urllib.urlopen(url).read().decode('unicode_escape'), encoding='utf_8')
      break
    except Exception as e:
      attempts += 1
  if jsondata:
    return jsondata
  else:
    return False

def wcl(fname):
  with open(fname) as f:
    for i, l in enumerate(f):
      pass
  return i + 1

def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])

def pickle_sym2pid(dba, logger, pfile):
  '''
  This goes through all TCRD targets and checks (by symbol) if the Harmonizome has a corresponding gene. An additional check is done to make sure the NCBI Gene ID in the Harmonizome matches that in TCRD. For those that do, results are saved to a pickle file. 
  '''
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  tct = dba.get_target_count(idg=False)
  print "Processing %d TCRD targets" % tct
  logger.info("Processing %d TCRD targets" % tct)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=tct).start()  
  ct = 0
  sym2pid = {}
  notfnd = []
  skip_ct = 0
  errors = {}
  for target in dba.get_targets():
    ct += 1
    pbar.update(ct)
    logger.info("Processing target %d" % target['id'])
    p = target['components']['protein'][0]
    k = "%d:%s"%(target['id'],p['sym'])
    if not p['sym']:
      logger.info("Skipping - target has no symbol")
      skip_ct += 1
      continue
    jsondata = get_gene(p['sym'])
    if not jsondata:
      logger.error("No JSON for %s" % k)
      errors[k] = 'No JSON'
    elif 'status' in jsondata and jsondata['status'] == 400:
      # Bad request:
      logger.warn("Bad request for %s" % k)
      notfnd.append(k)
    else:
      if p['geneid']:
        if 'ncbiEntrezGeneId' in jsondata and jsondata['ncbiEntrezGeneId'] == p['geneid']:
          sym2pid[p['sym']] = p['id']
        else:
          logger.error('GeneID mismatch: JSON: %s vs TCRD: %d' % (jsondata['ncbiEntrezGeneId'], p['geneid']))
          errors[k] = 'GeneID mismatch: JSON: %s vs TCRD: %d' % (jsondata['ncbiEntrezGeneId'], p['geneid'])
      else:
        sym2pid[p['sym']] = p['id']
  pbar.finish()
  print "  %d targets processed." % ct
  print "  Dumping %d sym => TCRD protein_id mappings to file %s" % (len(sym2pid), pfile)
  pickle.dump(sym2pid, open(pfile, 'wb'))
  if skip_ct > 0:
    print "  Skipped %d targets with no sym" % skip_ct
  if notfnd:
    print "  %d targets not found in harmonizome. See logfile %s for details." % (len(notfnd), logfile)
    #for k in notfnd:
    #  print k
  if len(errors) > 0:
    print "  %d targets had errors. See logfile %s for details." % (len(errors), logfile)
    #for k,msg in errors.items():
    #  print "%s: %s" % (k, msg)
  return True

if __name__ == '__main__':
  main()

# ct = 0
# sym2pid = {}
# notfnd = []
# skip_ct = 0
# errors = {}
# for target in dba.get_targets():
#   ct += 1
#   p = target['components']['protein'][0]
#   k = "%d:%s"%(target['id'],p['sym'])
#   if not p['sym']:
#     skip_ct += 1
#     continue
#   jsondata = get_gene(p['sym'])
#   if not jsondata:
#     errors[k] = 'No JSON'
#   elif 'status' in jsondata and jsondata['status'] == 400:
#     # Bad request:
#     notfnd.append(k)
#   else:
#     if p['geneid']:
#       if 'ncbiEntrezGeneId' in jsondata and jsondata['ncbiEntrezGeneId'] == p['geneid']:
#         sym2pid[p['sym']] = p['id']
#       else:
#         errors[k] = 'GeneID mismatch: JSON: %s vs TCRD: %d' % (jsondata['ncbiEntrezGeneId'], p['geneid'])
#     else:
#       sym2pid[p['sym']] = p['id']

    
  
