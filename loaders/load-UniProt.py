#!/usr/bin/env python
# Time-stamp: <2017-01-05 16:42:59 smathias>
"""Load protein data from UniProt.org into TCRD via the web.

Usage:
    load-UniProt.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-UniProt.py -? | --help

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
__copyright__ = "Copyright 2014-2016, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.0.0"

import os,sys,time,re
from docopt import docopt
from TCRD import DBAdaptor
import logging
import csv
import requests
from bs4 import BeautifulSoup
import shelve
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
LOGFILE = "%s.log" % PROGRAM

# Download tab-delimited file from:
# http://www.uniprot.org/uniprot/?query=reviewed:yes+AND+organism:9606
UPHUMAN_FILE = '../data/UniProt/uniprot-human-reviewed_20161116.tab'
BASEURL = "http://www.uniprot.org/uniprot/"
SHELF_FILE = './tcrd4logs/load-UniProt.db'

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
  dataset_id = dba.ins_dataset( {'name': 'UniProt', 'source': 'Web API at %s'%BASEURL, 'app': PROGRAM, 'app_version': __version__, 'url': 'http://www.uniprot.org/uniprot'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset. See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  provs = [ {'dataset_id': 1, 'table_name': 'target', 'column_name': 'ttype'},
            {'dataset_id': dataset_id, 'table_name': 'target', 'column_name': 'name'},
            {'dataset_id': dataset_id, 'table_name': 'protein'},
            {'dataset_id': dataset_id, 'table_name': 'tdl_info', 'where_clause': "itype = 'UniProt Function'"},
            {'dataset_id': dataset_id, 'table_name': 'goa'},  
            {'dataset_id': dataset_id, 'table_name': 'expression', 'where_clause': "etype = 'UniProt Tissue'"},
            {'dataset_id': dataset_id, 'table_name': 'pathway', 'where_clause': "type = 'uniprot'"},
            {'dataset_id': dataset_id, 'table_name': 'disease', 'where_clause': "dtype = 'uniprot'"},
            {'dataset_id': dataset_id, 'table_name': 'feature'} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    if not rv:
      print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
      sys.exit(1)
  
  start_time = time.time()
  xtypes = dba.get_xref_types()
  # see EvidenceOntology.ipynb for where this comes from
  e2e = {'ECO:0000250': 'ISS', 'ECO:0000269': 'EXP', 'ECO:0000270': 'IEP', 'ECO:0000303': 'NAS', 
         'ECO:0000304': 'TAS', 'ECO:0000305': 'IC' ,'ECO:0000314': 'IDA','ECO:0000315': 'IMP',
         'ECO:0000316': 'IGI','ECO:0000318': 'IBA', 'ECO:0000353': 'IPI', 'ECO:0000501': 'IEA'}

  s = shelve.open(SHELF_FILE, writeback=True)
  s['ups'] = []
  s['loaded'] = {}
  s['retries'] = {}
  s['errors'] = {}

  line_ct = wcl(UPHUMAN_FILE)
  line_ct -= 1 # file has header row
  if not args['--quiet']:
    print "\nProcessing %d records in UniProt file %s" % (line_ct, UPHUMAN_FILE)
  with open(UPHUMAN_FILE, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    tsvreader.next() # skip header line
    for row in tsvreader:
      up = row[0]
      s['ups'].append(up)

  print "\nLoading data for %d proteins" % len(s['ups'])
  logger.info("Loading data for %d proteins" % len(s['ups']))
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=len(s['ups'])).start()
  ct = 0
  xml_err_ct = 0
  dba_err_ct = 0
  for i,up in enumerate(s['ups']):
    ct += 1
    logger.info("Processing UniProt entry %d: %s" % (i, up))
    (status, headers, upxml) = get_uniprot(up)
    # Code	Description
    # 200	The request was processed successfully.
    # 300 Obsolete.
    # 400	Bad request. There is a problem with your input.
    # 404	Not found. The resource you requested doesn't exist.
    # 410	Gone. The resource you requested was removed.
    # 500	Internal server error. Most likely a temporary problem, but if the problem persists please contact us.
    # 503	Service not available. The server is being updated, try again later.
    if not status:
      logger.warn("Failed getting accession %s" % up)
      s['retries'][up] = True
      continue
    if status != 200:
      logger.error("Bad UniProt API response for %s: %s" % (up, status))
      s['errors'][up] = status
      continue
    target = uniprotxml2target(up, upxml, dataset_id, xtypes, e2e)
    if not target:
      xml_err_ct += 1
      logger.error("XML Error for %s" % up)
      continue
    tid = dba.ins_target(target)
    if tid:
      logger.debug("Target insert id: %s" % tid)
      s['loaded'][up] = tid
    else:
      dba_err_ct += 1
    time.sleep(0.5)
    pbar.update(ct)
  pbar.finish()
  print "Processed %d UniProt records." % ct
  print "  Total loaded targets/proteins: %d" % len(s['loaded'].keys())
  if len(s['retries']) > 0:
    print "  Total targets/proteins remaining for retries: %d " % len(s['retries'])
  if len(s['errors']) > 0:
    print "WARNING: %d API errors occurred. See logfile %s for details." % (len(s['errors']), logfile)
  if xml_err_ct > 0:
    print "WARNING: %d XML parsing errors occurred." % xml_err_ct
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)
  
  loop = 1
  while len(s['retries']) > 0:
    print "\nRetry loop %d: Trying to load data for %d proteins" % (loop, len(s['retries']))
    logger.info("Retry loop %d: Trying to load data for %d proteins" % (loop, len(s['retries'])))
    pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
    pbar = ProgressBar(widgets=pbar_widgets, maxval=len(s['retries'])).start()
    ct = 0
    tct = 0
    xml_err_ct = 0
    dba_err_ct = 0
    for up,_ in s['retries'].items():
      ct += 1
      logger.info("Processing UniProt entry %s" % up)
      (status, headers, upxml) = get_uniprot(up)
      # Code	Description
      # 200	The request was processed successfully.
      # 300 Obsolete.
      # 400	Bad request. There is a problem with your input.
      # 404	Not found. The resource you requested doesn't exist.
      # 410	Gone. The resource you requested was removed.
      # 500	Internal server error. Most likely a temporary problem, but if the problem persists please contact us.
      # 503	Service not available. The server is being updated, try again later.
      if not status:
        logger.warn("Failed getting accession %s" % up)
        continue
      if status != 200:
        logger.error("Bad UniProt API response for %s: %s" % (up, status))
        s['errors'][up] = status
        continue
      target = uniprotxml2target(up, upxml, dataset_id, xtypes, e2e)
      if not target:
        xml_err_ct += 1
        logger.error("XML Error for %s" % up)
        continue
      tid = dba.ins_target(target)
      if tid:
        tct += 1
        logger.debug("Target insert id: %s" % tid)
        s['loaded'][up] = tid
        del s['retries'][up]
      else:
        dba_err_ct += 1
      time.sleep(0.5)
      pbar.update(ct)
    loop += 1
    pbar.finish()
    print "Processed %d UniProt records." % ct
    print "  Loaded %d new targets/proteins" % tct
    print "  Total loaded targets/proteins: %d" % len(s['loaded'].keys())
    if len(s['retries']) > 0:
      print "  Total targets/proteins remaining for next loop: %d " % len(s['retries'])
    if len(s['errors']) > 0:
      print "WARNING: %d API errors occurred. See logfile %s for details." % (len(s['errors']), logfile)
    if xml_err_ct > 0:
      print "WARNING: %d XML parsing errors occurred." % xml_err_ct
    if dba_err_ct > 0:
      print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)
  
  s.close()

  elapsed = time.time() - start_time
  print "\n%s: Done. Elapsed time: %s" % (PROGRAM, secs2str(elapsed))
  print
  

def wcl(fname):
  with open(fname) as f:
    for i, l in enumerate(f):
      pass
  return i + 1

def get_uniprot(acc):
  url = "%s%s.xml" % (BASEURL, acc)
  attempts = 0
  r = None
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

def uniprotxml2target(up, upxml, dataset_id, xtypes, e2e):
  """
  Parse a UniProt XML entry and return a target dictionary suitable for passing to TCRD.DBAdaptor.ins_target().
  """
  soup = BeautifulSoup(upxml, "xml")
  if not soup:
    return False
  try:
    e = soup.uniprot.find('entry')
  except:
    return False
  target = {'ttype': 'Single Protein'}
  target['components'] = {}
  target['components']['protein'] = []
  protein = {'uniprot': up}
  aliases = []
  xrefs = []
  tdl_infos = []
  goas = []
  exps = []
  pathways = []
  diseases = []
  features = []
  for acc in e.findAll('accession'):
    if acc.text != up: aliases.append({'type': 'uniprot', 'dataset_id': dataset_id, 'value': acc.text})
  protein['name'] = e.find('name').text
  recname = e.find('recommendedName')
  protein['description'] = recname.fullName.text
  target['name'] = recname.fullName.text
  if recname.shortName:
    aliases.append({'type': 'uniprot', 'dataset_id': dataset_id, 'value': recname.shortName.text})
  protein['sym'] = None
  if e.find('gene') and e.find('gene').findChild('name'):
    gn = e.find('gene').findChild('name')
    if gn.attrs['type'] == 'primary':
      protein['sym'] = gn.text
  seq = [s for s in e.findAll('sequence') if 'checksum' in s.attrs][0]
  protein['seq'] = seq.text.replace('\n', '')
  protein['up_version'] = seq.attrs['version']
  for c in e.find_all('comment'):
    if c.attrs['type'] == 'function':
      tdl_infos.append( {'itype': 'UniProt Function',  'string_value': c.text.strip()} )
    if c.attrs['type'] == 'pathway':
      pathways.append( {'pwtype': 'UniProt', 'name': c.findChild('text').text} )
    if c.attrs['type'] == 'similarity':
      protein['family'] = c.findChild('text').text
    if c.attrs['type'] == 'disease':
      if not c.findChild('name'): continue
      da = {'dtype': 'UniProt Disease', 'name':c.findChild('name').text }
      if c.findChild('description'):
        da['description'] = c.findChild('description').text
      if c.findChild('dbReference'):
        dbr = c.findChild('dbReference')
        da['did'] = "%s:%s"%(dbr.attrs['type'],dbr.attrs['id'])
      if 'evidence' in c.attrs:
        da['evidence'] = c.attrs['evidence']
      diseases.append(da)
  for dbr in e.findAll('dbReference'):
    if dbr.attrs['type'] == 'GeneID':
      protein['geneid'] =  dbr.attrs['id']
    elif dbr.attrs['type'] in ['InterPro', 'Pfam', 'PROSITE', 'SMART']:
      xtra = None
      for p in dbr.findAll('property'):
        if p.attrs['type'] == 'entry name':
          xtra = p.attrs['value']
      xrefs.append( {'xtype': dbr.attrs['type'], 'dataset_id': dataset_id, 'value': dbr.attrs['id'], 'xtra': xtra} )
    elif dbr.attrs['type'] == 'GO':
      name = None
      goeco = None
      for p in dbr.findAll('property'):
        if p.attrs['type'] == 'term':
          name = p.attrs['value']
        elif p.attrs['type'] == 'evidence':
          goeco = p.attrs['value']
      goas.append( {'go_id': dbr.attrs['id'], 'go_term': name,
                    'goeco': goeco, 'evidence': e2e[goeco]} )
    elif dbr.attrs['type'] == 'Ensembl':
      xrefs.append( {'xtype': 'Ensembl', 'dataset_id': dataset_id, 'value': dbr.attrs['id']} )
      for p in dbr.findAll('property'):
        if p.attrs['type'] == 'protein sequence ID':
          xrefs.append( {'xtype': 'Ensembl', 'dataset_id': dataset_id, 'value': p.attrs['value']} )
        elif p.attrs['type'] == 'gene ID':
          xrefs.append( {'xtype': 'Ensembl', 'dataset_id': dataset_id, 'value': p.attrs['value']} )
    elif dbr.attrs['type'] == 'STRING':
      xrefs.append( {'xtype': 'STRING', 'dataset_id': dataset_id, 'value': dbr.attrs['id']} )
    elif dbr.attrs['type'] == 'Reactome':
      xtra = None
      for p in dbr.findAll('property'):
        if p.attrs['type'] == 'pathway name':
          xtra = p.attrs['value']
      xrefs.append( {'xtype': 'Reactome', 'dataset_id': dataset_id, 'value': dbr.attrs['id'], 'xtra': xtra} )
    elif dbr.attrs['type'] == 'DrugBank':
      xtra = None
      for p in dbr.findAll('property'):
        if p.attrs['type'] == 'generic name':
            xtra = p.attrs['value']
      xrefs.append( {'xtype': 'DrugBank', 'dataset_id': dataset_id, 'value': dbr.attrs['id'], 'xtra': xtra} )
    else:
      if dbr.attrs['type'] in xtypes:
        xrefs.append( {'xtype': dbr.attrs['type'], 'dataset_id': dataset_id, 'value': dbr.attrs['id']} )
      #else:
      #  print "Unexpected xref_type:", dbr.attrs['type']
  for k in e.findAll('keyword'):
    xrefs.append( {'xtype': 'UniProt Keyword', 'dataset_id': dataset_id, 'value': k.attrs['id'], 'xtra': k.text} )
  for r in e.find_all('reference'):
    if r.findChild('tissue'):
      tissue = r.findChild('tissue').text
      ex = {'etype': 'UniProt Tissue', 'tissue': tissue, 'boolean_value': 1}
      if r.findChild('dbReference'):
        ex['pubmed_id'] = r.findChild('dbReference').attrs['id']
      exps.append(ex)
  for f in e.findAll('feature'):
    init = {'type': f.attrs['type']}
    if 'evidence' in f.attrs:
      init['evidence'] = f.attrs['evidence']
    if 'description' in f.attrs:
      init['description'] = f.attrs['description']
    if 'id' in f.attrs:
      init['srcid'] = f.attrs['id']
    if f.findChild('location'):
      loc = f.findChild('location')
      if loc.findChild('position'):
        pos = loc.findChild('position')
        init['position'] = pos.attrs['position']
      else:
        if loc.findChild('begin'):
          beg = loc.findChild('begin')
          if 'position' in beg.attrs:
            init['begin'] = beg.attrs['position']
        if loc.findChild('end'):
          end = loc.findChild('end')
          if 'position' in end.attrs:
            init['end'] = end.attrs['position']
    features.append(init)
  protein['aliases'] = aliases
  protein['xrefs'] = xrefs
  protein['tdl_infos'] = tdl_infos
  protein['goas'] = goas
  protein['expressions'] = exps
  protein['pathways'] = pathways
  protein['diseases'] = diseases
  protein['features'] = features
  target['components']['protein'].append(protein)

  return target

def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])

if __name__ == '__main__':
  main()

# # for ipython:
# import requests
# from bs4 import BeautifulSoup
# BASEURL = "http://www.uniprot.org/uniprot/"
# up = 'Q8TBF5'
# url = "%s%s.xml" % (BASEURL, up)
# r = requests.get(url)
# soup = BeautifulSoup(r.text, "xml")


