#!/usr/bin/env python
# Time-stamp: <2018-01-29 11:57:16 smathias>
"""TCRD with latest NCBI Gene data via EUtils.

Usage:
    load-NCBIGene.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-NCBIGene.py -h | --help

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
__copyright__ = "Copyright 2014-2018, Steve Mathias"
__license__ = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__ = "2.1.1"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import requests
from bs4 import BeautifulSoup
import logging
from collections import defaultdict
import shelve
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd5logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
EFETCH_GENE_URL = "http://www.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=Gene&rettype=xml&id="
SHELF_FILE = '%s/load-NCBIGene.db'%LOGDIR

# find proteins with the same geneid:
#select count(*) from protein where geneid in (select geneid from protein group by geneid having count(*) > 1);

xtypes = {}

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
  logger.info("Connected to TCRD database %s (schema ver %s; data ver %s)", args['--dbname'], dbi['schema_ver'], dbi['data_ver'])
  if not args['--quiet']:
    print "\nConnected to TCRD database %s (schema ver %s; data ver %s)" % (args['--dbname'], dbi['schema_ver'], dbi['data_ver'])
    
  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'NCBI Gene', 'source': 'EUtils web API at %s'%EFETCH_GENE_URL, 'app': PROGRAM, 'app_version': __version__, 'url': 'http://www.ncbi.nlm.nih.gov/gene'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'tdl_info', 'where_clause': "itype = 'NCBI Gene Summary'"},
            {'dataset_id': dataset_id, 'table_name': 'tdl_info', 'where_clause': "itype = 'NCBI Gene PubMed Count'"},
            {'dataset_id': dataset_id, 'table_name': 'generif'},
            {'dataset_id': dataset_id, 'table_name': 'xref', 'where_clause': "dataset_id = %d"%dataset_id},
            {'dataset_id': dataset_id, 'table_name': 'alias', 'where_clause': "dataset_id = %d"%dataset_id} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    if not rv:
      print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
      sys.exit(1)

  start_time = time.time()
  global xtypes
  xtypes = dba.get_xref_types()
  
  s = shelve.open(SHELF_FILE, writeback=True)
  s['loaded'] = []
  s['retries'] = {}
  s['counts'] = defaultdict(int)
  
  tct = dba.get_target_count()
  if not args['--quiet']:
    print "\nLoading NCBI Gene annotations for %d TCRD targets" % tct
  logger.info("Loading NCBI Gene annotations for %d TCRD targets\n" % tct)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=tct).start()  
  ct = 0
  skip_ct = 0
  for t in dba.get_targets(include_annotations=False):
    tid = t['id']
    #if tid < 17872: continue
    ct += 1
    p = t['components']['protein'][0]
    pid = p['id']
    if p['geneid'] == None:
      skip_ct += 1
      continue
    geneid = str(p['geneid'])
    logger.info("Processing target %d: geneid %s" % (tid, geneid))
    (status, headers, xml) = get_ncbigene(geneid)
    if not status:
      logger.warn("Failed getting Gene ID %s" % geneid)
      s['retries'][tid] = True
      continue
    if status != 200:
      logger.warn("Bad API response for Gene ID %s: %s" % (geneid, status))
      s['retries'][tid] = True
      continue
    gene_annotations = parse_genexml(xml)
    if not gene_annotations:
      s['counts']['xml_err'] += 1
      logger.error("XML Error for Gene ID %s" % geneid)
      s['retries'][tid] = True
      continue
    load_annotations(dba, t, dataset_id, gene_annotations, s)
    time.sleep(0.5)
    pbar.update(ct)
  pbar.finish()
  print "Processed %d targets." % ct
  if skip_ct > 0:
    print "Skipped %d targets with no geneid" % skip_ct 
  print "Loaded NCBI annotations for %d targets" % len(s['loaded'])
  if len(s['retries']) > 0:
    print "Total targets remaining for retries: %d " % len(s['retries'])

  loop = 1
  while len(s['retries']) > 0:
    print "\nRetry loop %d: Loading NCBI Gene annotations for %d TCRD targets" % (loop, len(s['retries']))
    logger.info("Retry loop %d: Loading NCBI Gene annotations for %d TCRD targets" % (loop, len(s['retries'])))
    pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
    pbar = ProgressBar(widgets=pbar_widgets, maxval=len(s['retries'])).start()
    ct = 0
    act = 0
    for tid,_ in s['retries'].items():
      ct += 1
      t = dba.get_target(tid, include_annotations=False)
      geneid = str(t['components']['protein'][0]['geneid'])
      logger.info("Processing target %d: geneid %s" % (tid, geneid))
      (status, headers, xml) = get_ncbigene(geneid)
      if not status:
        logger.warn("Failed getting Gene ID %s" % geneid)
        continue
      if status != 200:
        logger.warn("Bad API response for Gene ID %s: %s" % (geneid, status))
        continue
      gene_annotations = parse_genexml(xml)
      if not gene_annotations:
        s['counts']['xml_err'] += 1
        logger.error("XML Error for Gene ID %s" % geneid)
        continue
      load_annotations(dba, t, dataset_id, gene_annotations, s)
      act += 1
      del s['retries'][tid]
      time.sleep(0.5)
      pbar.update(ct)
    loop += 1
    if loop ==5:
      print("Completed 5 retry loops. Aborting.")
      break
    pbar.finish()
    print "Processed %d targets." % ct
    print "  Annotated %d additional targets" % act
    print "  Total annotated targets: %d" % len(s['loaded'])
    if len(s['retries']) > 0:
      print "Total targets remaining for retries: %d " % len(s['retries'])
  
  print "\nInserted %d aliases" % s['counts']['alias']
  print "Inserted %d NCBI Gene Summary tdl_infos" % s['counts']['summary']
  print "Inserted %d NCBI Gene PubMed Count tdl_infos" % s['counts']['pmc']
  print "Inserted %d GeneRIFs" % s['counts']['generif']
  print "Inserted %d PubMed xrefs" % s['counts']['pmxr']
  print "Inserted %d other xrefs" % s['counts']['xref']  
  if s['counts']['xml_err'] > 0:
    print "WARNNING: %d XML parsing errors occurred. See logfile %s for details." % (s['counts']['xml_err'], logfile)
  if s['counts']['dba_err'] > 0:
    print "WARNNING: %d DB errors occurred. See logfile %s for details." % (s['counts']['dba_err'], logfile)

def get_ncbigene(id):
  url = "%s%s.xml" % (EFETCH_GENE_URL, id)
  r = None
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

def parse_genexml(xml):
  global xtypes
  annotations = {}
  soup = BeautifulSoup(xml, "xml")
  if not soup:
    return False
  try:
    g = soup.find('Entrezgene')
  except:
    return False
  if not g:
    return False
  comments = g.find('Entrezgene_comments')
  # Aliases
  annotations['aliases'] = []
  if g.find('Gene-ref_syn'):
    for grse in g.find('Gene-ref_syn').findAll('Gene-ref_syn_E'):
      annotations['aliases'].append(grse.text)
  # Gene Summary
  if g.find('Entrezgene_summary'):
    annotations['summary'] = g.find('Entrezgene_summary').text
  # PubMed IDs
  annotations['pmids'] = []
  gcrefs = comments.find('Gene-commentary_refs')
  if gcrefs:
    # use set() to get rid of potential duplicates
    annotations['pmids'] = set( [pmid.text for pmid in gcrefs.findAll('PubMedId')] )
  # GeneRIFs
  annotations['generifs'] = []
  for gc in comments.findAll('Gene-commentary', recursive=False):
    if gc.findChild('Gene-commentary_heading') and gc.find('Gene-commentary_heading').text == 'Interactions': continue
    gctype = gc.findChild('Gene-commentary_type')
    if gctype.attrs['value'] == 'generif':
      gctext = gc.find('Gene-commentary_text')
      if gctext:
        annotations['generifs'].append( {'pubmed_ids': "|".join([pmid.text for pmid in gc.findAll('PubMedId')]), 'text': gctext.text} )
  # Other XRefs
  annotations['xrefs'] = []
  for gc in comments.findAll('Gene-commentary', recursive=False):
    if gc.findChild('Gene-commentary_heading'):
      if gc.find('Gene-commentary_heading').text == 'Interactions':
        continue
      if gc.find('Gene-commentary_heading').text == 'Additional Links':
        for gc2 in gc.findAll('Gene-commentary'):
          if not gc2.find('Dbtag_db'): continue
          xt = gc2.find('Dbtag_db').text
          if xt in xtypes:
            if gc2.find('Object-id_str'):
              val = gc2.find('Object-id_str').text
            elif gc2.find('Object-id_id'):
              val = gc2.find('Object-id_id').text
            else:
              continue
            if gc2.find('Other-source_url'):
              url = gc2.find('Other-source_url').text
              init = {'xtype': xt, 'value': val, 'url': url}
            else:
              init = {'xtype': xt, 'value': val}
            annotations['xrefs'].append(init)
  return annotations

def load_annotations(dba, t, dataset_id, gene_annotations, shelf):
  p = t['components']['protein'][0]
  pid = p['id']
  for a in gene_annotations['aliases']:
    rv = dba.ins_alias({'protein_id': pid, 'type': 'symbol', 'dataset_id': dataset_id, 'value': a})
    if rv:
      shelf['counts']['alias'] += 1
    else:
      shelf['counts']['dba_err'] += 1
  if 'summary' in gene_annotations:
    rv = dba.ins_tdl_info({'protein_id': pid, 'itype': 'NCBI Gene Summary',
                           'string_value': gene_annotations['summary']})
    if rv:
      shelf['counts']['summary'] += 1
    else:
      shelf['counts']['dba_err'] += 1
  if 'pmids' in gene_annotations:
    pmct = len(gene_annotations['pmids'])
  else:
    pmct = 0
  rv = dba.ins_tdl_info({'protein_id': pid, 'itype': 'NCBI Gene PubMed Count',
                         'integer_value': pmct})
  if rv:
    shelf['counts']['pmc'] += 1
  else:
    shelf['counts']['dba_err'] += 1
  for pmid in gene_annotations['pmids']:
    rv = dba.ins_xref({'protein_id': pid, 'xtype': 'PubMed', 'dataset_id': dataset_id, 'value': pmid})
    if rv:
      shelf['counts']['pmxr'] += 1
    else:
      shelf['counts']['dba_err'] += 1
  if 'generifs' in gene_annotations:
    for grd in gene_annotations['generifs']:
      grd['protein_id'] = pid
      rv = dba.ins_generif(grd)
      if rv:
        shelf['counts']['generif'] += 1
      else:
        shelf['counts']['dba_err'] += 1
  if 'xrefs' in gene_annotations:
    for xrd in gene_annotations['xrefs']:
      xrd['protein_id'] = pid
      xrd['dataset_id'] = dataset_id
      rv = dba.ins_xref(xrd)
      if rv:
        shelf['counts']['xref'] += 1
      else:
        shelf['counts']['dba_err'] += 1
  shelf['loaded'].append(t['id'])


if __name__ == '__main__':
  print "\n{} (v{}) [{}]:".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  start_time = time.time()
  load(args)
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))
