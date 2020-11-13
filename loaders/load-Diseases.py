#!/usr/bin/env python
# Time-stamp: <2020-07-27 15:06:58 smathias>
"""Load disease associations into TCRD.

Usage:
    load-Diseases.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-Diseases.py -? | --help

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
__copyright__ = "Copyright 2020, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "1.0.0"

import os,sys,time
from docopt import docopt
from TCRD7 import DBAdaptor
import logging
import csv
import gzip
from collections import defaultdict
import urllib,json,codecs
import shelve
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd7logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
CONFIG = {'DISEASES': {'DOWNLOAD_DIR': '../data/JensenLab/',
                       'BASE_URL': 'http://download.jensenlab.org/',
                       'FILENAME_K': 'human_disease_knowledge_filtered.tsv',
                       'FILENAME_E': 'human_disease_experiments_filtered.tsv',
                       'FILENAME_T': 'human_disease_textmining_filtered.tsv',
                       'SRC_FILES': "human_disease_knowledge_filtered.tsv, human_disease_experiments_filtered.tsv, human_disease_textmining_filtered.tsv"},
          'DisGeNET': {'DOWNLOAD_DIR': '../data/DisGeNET/',
                       'BASE_URL': 'http://www.disgenet.org/static/disgenet_ap1/files/downloads/',
                       'FILENAME': 'curated_gene_disease_associations.tsv.gz'},
          'Expression Atlas': {'FILENAME': '../data/ExpressionAtlas/disease_assoc_human_do_uniq.tsv'},
          'Monarch': {'API_BASE_URL': 'https://api.monarchinitiative.org/api/bioentity/gene/',
                      'API_QUERY_PARAMS': '/diseases?rows=100&facet=false&unselect_evidence=true&exclude_automatic_assertions=true&fetch_objects=false&use_compact_associations=false&direct=true&direct_taxon=false&association_type=both'},
          # Must download CTD file manually now due to Captcha
          'CTD': {'FILENAME': '../data/CTD/CTD_genes_diseases.tsv'},
                 #{'DOWNLOAD_DIR': '../data/CTD/',
                 # 'BASE_URL': 'http://ctdbase.org/reports/',
                 # 'FILENAME': 'CTD_genes_diseases.tsv.gz'},
          'eRAM': {'SHELF_FILE': '../data/eRAM/eRAM.db'},
          }

def download_DISEASES(args):
  for fn in [CONFIG['DISEASES']['FILENAME_K'], CONFIG['DISEASES']['FILENAME_E'], CONFIG['DISEASES']['FILENAME_T']]:
    if os.path.exists(CONFIG['DISEASES']['DOWNLOAD_DIR'] + fn):
      os.remove(CONFIG['DISEASES']['DOWNLOAD_DIR'] + fn)
    if not args['--quiet']:
      print "Downloading ", CONFIG['DISEASES']['BASE_URL'] + fn
      print "         to ", CONFIG['DISEASES']['DOWNLOAD_DIR'] + fn
    urllib.urlretrieve(CONFIG['DISEASES']['BASE_URL'] + fn, CONFIG['DISEASES']['DOWNLOAD_DIR'] + fn)

def load_DISEASES(args, dba, logger, logfile):
  # Knowledge channel
  fn = CONFIG['DISEASES']['DOWNLOAD_DIR'] + CONFIG['DISEASES']['FILENAME_K']
  line_ct = slmf.wcl(fn)
  if not args['--quiet']:
    print "Processing {} lines in DISEASES Knowledge file {}".format(line_ct, fn)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  with open(fn, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    pmark = {}
    notfnd = set()
    dis_ct = 0
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
      ensp = row[0]
      sym = row[1]
      k = "%s|%s"%(ensp,sym)
      if k in notfnd:
        continue
      targets = dba.find_targets({'stringid': ensp})
      if not targets:
        targets = dba.find_targets({'sym': sym}, idg = False)
      if not targets:
        notfnd.add(k)
        logger.warn("No target found for {}".format(k))
        continue
      dtype = 'JensenLab Knowledge ' + row[4]
      for t in targets:
        p = t['components']['protein'][0]
        pmark[p['id']] = True
        rv = dba.ins_disease( {'protein_id': p['id'], 'dtype': dtype, 'name': row[3],
                               'did': row[2], 'evidence': row[5], 'conf': row[6]} )
        if not rv:
          dba_err_ct += 1
          continue
        dis_ct += 1
      pbar.update(ct)
  pbar.finish()
  print "{} lines processed.".format(ct)
  print "Inserted {} new disease rows for {} proteins".format(dis_ct, len(pmark))
  if notfnd:
    print "  No target found for {} stringids/symbols. See logfile {} for details.".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)
    
  # Experiment channel
  fn = CONFIG['DISEASES']['DOWNLOAD_DIR'] + CONFIG['DISEASES']['FILENAME_E']
  line_ct = slmf.wcl(fn)
  if not args['--quiet']:
    print "Processing {} lines in DISEASES Experiment file {}".format(line_ct, fn)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  with open(fn, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    pmark = {}
    notfnd = set()
    dis_ct = 0
    skip_ct = 0
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
      if row[6] == '0':
        # skip zero confidence rows
        skip_ct += 1
        continue
      ensp = row[0]
      sym = row[1]
      k = "%s|%s"%(ensp,sym)
      if k in notfnd:
        continue
      targets = dba.find_targets({'stringid': ensp})
      if not targets:
        targets = dba.find_targets({'sym': sym})
      if not targets:
        notfnd.add(k)
        logger.warn("No target found for {}".format(k))
        continue
      dtype = 'JensenLab Experiment ' + row[4]
      for t in targets:
        p = t['components']['protein'][0]
        pmark[p['id']] = True
        rv = dba.ins_disease( {'protein_id': p['id'], 'dtype': dtype, 'name': row[3],
                               'did': row[2], 'evidence': row[5], 'conf': row[6]} )
        if not rv:
          dba_err_ct += 1
          continue
        dis_ct += 1
      pbar.update(ct)
  pbar.finish()
  print "{} lines processed.".format(ct)
  print "Inserted {} new disease rows for {} proteins".format(dis_ct, len(pmark))
  if skip_ct > 0:
    print "  Skipped {} zero confidence rows".format(skip_ct)
  if notfnd:
    print "  No target found for {} stringids/symbols. See logfile {} for details.".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

  # Text Mining channel
  fn = CONFIG['DISEASES']['DOWNLOAD_DIR'] + CONFIG['DISEASES']['FILENAME_T']
  line_ct = slmf.wcl(fn)
  if not args['--quiet']:
    print "Processing {} lines in DISEASES Text Mining file {}".format(line_ct, fn)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  with open(fn, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    pmark = {}
    notfnd = set()
    dis_ct = 0
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
      ensp = row[0]
      sym = row[1]
      k = "%s|%s"%(ensp,sym)
      if k in notfnd:
        continue
      targets = dba.find_targets({'stringid': ensp})
      if not targets:
        targets = dba.find_targets({'sym': sym})
      if not targets:
        notfnd.add(k)
        logger.warn("No target found for {}".format(k))
        continue
      dtype = 'JensenLab Text Mining'
      for t in targets:
        p = t['components']['protein'][0]
        pmark[p['id']] = True
        rv = dba.ins_disease( {'protein_id': p['id'], 'dtype': dtype, 'name': row[3],
                               'did': row[2], 'zscore': row[4], 'conf': row[5]} )
        if not rv:
          dba_err_ct += 1
          continue
        dis_ct += 1
      pbar.update(ct)
  pbar.finish()
  print "{} lines processed.".format(ct)
  print "Inserted {} new disease rows for {} proteins".format(dis_ct, len(pmark))
  if notfnd:
    print "  No target found for {} stringids/symbols. See logfile {} for details.".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'Jensen Lab DISEASES', 'source': 'Files %s from %s'%(", ".join(CONFIG['DISEASES']['SRC_FILES']), CONFIG['DISEASES']['BASE_URL']), 'app': PROGRAM, 'app_version': __version__, 'url': 'http://diseases.jensenlab.org/'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'disease', 'where_clause': "dtype LIKE 'JensenLab %'"})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

def download_DisGeNET(args):
  gzfn = CONFIG['DisGeNET']['DOWNLOAD_DIR'] + CONFIG['DisGeNET']['FILENAME']
  if os.path.exists(gzfn):
    os.remove(gzfn)
  fn = gzfn.replace('.gz', '')
  if os.path.exists(fn):
    os.remove(fn)
  if not args['--quiet']:
    print "Downloading", CONFIG['DisGeNET']['BASE_URL'] + CONFIG['DisGeNET']['FILENAME']
    print "         to", CONFIG['DisGeNET']['DOWNLOAD_DIR'] + CONFIG['DisGeNET']['FILENAME']
  urllib.urlretrieve(CONFIG['DisGeNET']['BASE_URL'] + CONFIG['DisGeNET']['FILENAME'],
                     CONFIG['DisGeNET']['DOWNLOAD_DIR'] + CONFIG['DisGeNET']['FILENAME'])
  if not args['--quiet']:
    print "Uncompressing", gzfn
  ifh = gzip.open(gzfn, 'rb')
  ofh = open(fn, 'wb')
  ofh.write( ifh.read() )
  ifh.close()
  ofh.close()

def load_DisGeNET(args, dba, logger, logfile):
  fn = (CONFIG['DisGeNET']['DOWNLOAD_DIR'] + CONFIG['DisGeNET']['FILENAME']).replace('.gz', '')
  line_ct = slmf.wcl(fn)
  if not args['--quiet']:
     print "Processing {} lines in DisGeNET file {}".format(line_ct, fn)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  with open(fn, 'rU') as f:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start()
    ct = 0
    k2pids = {}
    pmark = {}
    notfnd = set()
    dis_ct = 0
    dba_err_ct = 0
    for line in f:
      # 0: geneId
      # 1: geneSymbol
      # 2: DSI
      # 3: DPI
      # 4: diseaseId
      # 5: diseaseName
      # 6: diseaseType
      # 7: diseaseClass
      # 8: diseaseSemanticType
      # 9: score
      # 10: EI
      # 11: YearInitial
      # 12: YearFinal
      # 13: NofPmids
      # 14: NofSnps
      # 15: source
      ct += 1
      if line.startswith('#'):
        continue
      if line.startswith('geneId'):
        # header row
        continue
      data = line.split('\t')
      geneid = data[0].strip()
      sym = data[1]
      k = "%s|%s"%(sym,geneid)
      if k in k2pids:
        # we've already found it
        pids = k2pids[k]
      elif k in notfnd:
        # we've already not found it
          continue
      else:
        targets = dba.find_targets({'sym': sym})
        if not targets:
          targets = dba.find_targets({'geneid': geneid})
        if not targets:
          notfnd.add(k)
          logger.warn("No target found for {}".format(k))
          continue
        pids = []
        for t in targets:
          p = t['components']['protein'][0]
          pmark[p['id']] = True
          pids.append(p['id'])
        k2pids[k] = pids # save this mapping so we only lookup each target once
      pmid_ct = data[13].strip()
      snp_ct = data[14].strip()
      if pmid_ct != '0':
        if snp_ct != '0':
          ev = "%s PubMed IDs; %s SNPs"%(pmid_ct, snp_ct)
        else:
          ev = "%s PubMed IDs"%pmid_ct
      else:
        ev = "%s SNPs"%snp_ct
      for pid in pids:
        rv = dba.ins_disease( {'protein_id': pid, 'dtype': 'DisGeNET', 'name': data[5],
                               'did': data[4], 'score': data[9], 'source': data[15].strip(),
                               'evidence': ev} )
        if not rv:
          dba_err_ct += 1
          continue
        dis_ct += 1
      pbar.update(ct)
  pbar.finish()
  print "{} lines processed.".format(ct)
  print "Loaded {} new disease rows for {} proteins.".format(dis_ct, len(pmark))
  if notfnd:
    print "  No target found for {} symbols/geneids. See logfile {} for details.".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'DisGeNET Disease Associations', 'source': 'File %s from %s.'%(CONFIG['DisGeNET']['FILENAME'], CONFIG['DisGeNET']['BASE_URL']), 'app': PROGRAM, 'app_version': __version__, 'url': 'http://www.disgenet.org/web/DisGeNET/menu'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'disease', 'where_clause': "dtype = 'DisGeNET'"})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

def load_ExpressionAtlas(args, dba, logger, logfile):
  # To generate the input file:
  # cd <TCRD ROOT>/data/ExpressionAtlas
  # wget ftp://ftp.ebi.ac.uk/pub/databases/microarray/data/atlas/experiments/atlas-latest-data.tar.gz
  # tar xf atlas-latest-data.tar.gz
  # ./process.R
  fn = CONFIG['Expression Atlas']['FILENAME']
  line_ct = slmf.wcl(fn)
  if not args['--quiet']:
    print "Processing {} lines in Expression Atlas file {}".format(line_ct, fn)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  with open(fn, 'rU') as tsv:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    tsvreader = csv.reader(tsv, delimiter='\t')
    header = tsvreader.next() # skip header line
    ct = 0
    k2pids = {}
    pmark = {}
    notfnd = set()
    dis_ct = 0
    dba_err_ct = 0
    for row in tsvreader:
      # 0: "Gene ID"
      # 1: "DOID"
      # 2: "Gene Name"
      # 3: "log2foldchange"
      # 4: "p-value"
      # 5: "disease"
      # 6: "experiment_id"
      # 7: "contrast_id"
      ct += 1
      sym = row[2]
      ensg = row[0]
      k = "%s|%s"%(sym,ensg)
      if k in k2pids:
        # we've already found it
        pids = k2pids[k]
      elif k in notfnd:
        # we've already not found it
          continue
      else:
        targets = dba.find_targets({'sym': sym}, idg = False)
        if not targets:
          targets = dba.find_targets_by_xref({'xtype': 'ENSG', 'value': ensg})
        if not targets:
          notfnd.add(k)
          logger.warn("No target found for {}".format(k))
          continue
        pids = []
        for t in targets:
          p = t['components']['protein'][0]
          pmark[p['id']] = True
          pids.append(p['id'])
        k2pids[k] = pids # save this mapping so we only lookup each target once
      for pid in pids:
        rv = dba.ins_disease( {'protein_id': pid, 'dtype': 'Expression Atlas', 'name': row[5],
                               'did': row[1], 'log2foldchange': "%.3f"%float(row[3]),
                               'pvalue': row[4]} )
        if not rv:
          dba_err_ct += 1
          continue
        dis_ct += 1
      pbar.update(ct)
  pbar.finish()
  print "{} lines processed.".format(ct)
  print "Loaded {} new disease rows for {} proteins.".format(dis_ct, len(pmark))
  if notfnd:
    print "  No target found for {} symbols/ensgs. See logfile {} for details.".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'Expression Atlas', 'source': 'IDG-KMC/UNM processed version of data obtained here: ftp://ftp.ebi.ac.uk/pub/databases/microarray/data/atlas/experiments/atlas-latest-data.tar.gz.', 'app': PROGRAM, 'app_version': __version__, 'url': 'https://www.ebi.ac.uk/gxa/', 'comment': 'Disease associations are derived from files from ftp://ftp.ebi.ac.uk/pub/databases/microarray/data/atlas/experiments/atlas-latest-data.tar.gz'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'disease', 'where_clause': "dtype = 'Expression Atlas'"})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

def get_monarch_disease_assocs(geneid):
  url = CONFIG['Monarch']['API_BASE_URL'] + urllib.quote_plus('NCBIGene:' + str(geneid)) + CONFIG['Monarch']['API_QUERY_PARAMS']
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

def load_Monarch(args, dba, logger, logfile):
  tct = dba.get_target_count()
  if not args['--quiet']:
    print "Loading Monarch disease associations for {} TCRD targets".format(tct)
  logger.info("Loading Monarch disease associations for {} TCRD targets".format(tct))
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=tct).start()
  ct = 0
  dis_ct = 0
  skip_ct = 0
  pmark = {}
  dba_err_ct = 0
  net_err_ct = 0
  for target in dba.get_targets():
    ct += 1
    pbar.update(ct)
    p = target['components']['protein'][0]
    pid = p['id']
    if not p['geneid']:
      skip_ct += 1
      continue
    jd = get_monarch_disease_assocs(p['geneid'])
    if not jd:
      logger.warn("Network error getting disease associations for NCBIGene:%d"%p['geneid'])
      net_err_ct += 1
      continue
    if 'associations' not in jd:
      logger.warn("No disease associations in JSON for NCBIGene:%d"%p['geneid'])
      skip_ct += 1
      continue
    for da in jd['associations']:
      ev = "|".join(["%s: %s"%(d['id'],d['label']) for d in da['evidence_types']])
      rv = dba.ins_disease( {'protein_id': pid, 'dtype': 'Monarch',
                             'name': da['object']['label'], 'did': da['object']['id'],
                             'evidence': ev} )
      if not rv:
        dba_err_ct += 1
        continue
      dis_ct += 1
      pmark[pid] = True
  pbar.finish()
  print "{} targets processed.".format(ct)
  print "Loaded {} new disease rows for {} proteins.".format(dis_ct, len(pmark))
  if skip_ct > 0:
    print "  Skipped {} targets with no geneid or no associations.".format(skip_ct)
  if net_err_ct > 0:
    print "WARNING: {} Network errors occurred. See logfile {} for details.".format(net_err_ct, logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

def download_CTD(args):
  gzfn = CONFIG['CTD']['DOWNLOAD_DIR'] + CONFIG['CTD']['FILENAME']
  if os.path.exists(gzfn):
    os.remove(gzfn)
  fn = gzfn.replace('.gz', '')
  if os.path.exists(fn):
    os.remove(fn)
  if not args['--quiet']:
    print "Downloading", CONFIG['CTD']['BASE_URL'] + CONFIG['CTD']['FILENAME']
    print "         to", CONFIG['CTD']['DOWNLOAD_DIR'] + CONFIG['CTD']['FILENAME']
  urllib.urlretrieve(CONFIG['CTD']['BASE_URL'] + CONFIG['CTD']['FILENAME'],
                     CONFIG['CTD']['DOWNLOAD_DIR'] + CONFIG['CTD']['FILENAME'])
  if not args['--quiet']:
    print "Uncompressing", gzfn
  ifh = gzip.open(gzfn, 'rb')
  ofh = open(fn, 'wb')
  ofh.write( ifh.read() )
  ifh.close()
  ofh.close()

def load_CTD(args, dab, logger, logfile):
  mesh2doid = dba.get_db2do_map('MESH')
  omim2doid = dba.get_db2do_map('OMIM')
  fn = CONFIG['CTD']['FILENAME']
  line_ct = slmf.wcl(fn)
  if not args['--quiet']:
    print "Processing {} lines in CTD file {}".format(line_ct, fn)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start()
  with open(fn, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    k2pids = {}
    pmark = {}
    notfnd = set()
    skip_ct = 0
    dis_ct = 0
    dba_err_ct = 0
    for row in tsvreader:
      # 0: GeneSymbol
      # 1: GeneID
      # 2: DiseaseName
      # 3: DiseaseID (MeSH or OMIM identifier)
      # 4: DirectEvidence ('|'-delimited list)
      # 5: InferenceChemicalName
      # 6: InferenceScore
      # 7: OmimIDs ('|'-delimited list)
      # 8: PubMedIDs ('|'-delimited list)
      ct += 1
      if row[0].startswith('#'):
        continue
      if not row[4]: # only load associations with direct evidence
        skip_ct += 1
        continue
      sym = row[0]
      geneid = row[1]
      k = "%s|%s"%(sym,geneid)
      if k in k2pids:
        # we've already found it
        pids = k2pids[k]
      elif k in notfnd:
        # we've already not found it
        continue
      else:
        targets = dba.find_targets({'sym': sym})
        if not targets:
          targets = dba.find_targets({'geneid': geneid})
        if not targets:
          notfnd.add(geneid)
          logger.warn("No target found for {}".format(k))
          continue
        pids = []
        for t in targets:
          p = t['components']['protein'][0]
          pids.append(p['id'])
        k2pids[k] = pids # save this mapping so we only lookup each target once
      # Try to map MeSH and OMIM IDs to DOIDs
      file_did = row[3]
      if file_did.startswith('MESH:'):
        mesh = file_did.replace('MESH:', '')
        if mesh in mesh2doid:
          dids = mesh2doid[mesh]
        else:
          dids = [file_did]
      elif file_did.startswith('OMIM:'):
        omim = file_did.replace('OMIM:', '')
        if omim in omim2doid:
          dids = omim2doid[omim]
        else:
          dids = [file_did]
      else:
        dids = [file_did]
      for pid in pids:
        for did in dids:
          rv = dba.ins_disease( {'protein_id': pid, 'dtype': 'CTD', 'name': row[2],
                                 'did': did, 'evidence': row[4]} )
          if not rv:
            dba_err_ct += 1
            continue
          dis_ct += 1
          pmark[p['id']] = True
      pbar.update(ct)
  pbar.finish()
  print "{} lines processed.".format(ct)
  print "Loaded {} new disease rows for {} proteins.".format(dis_ct, len(pmark))
  if skip_ct > 0:
    print "  Skipped {} with no direct evidence.".format(skip_ct)
  if notfnd:
    print "  No target found for {} symbols/geneids. See logfile {} for details.".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'CTD Disease Associations', 'source': 'File http://ctdbase.org/reports/%s.'%(CONFIG['CTD']['FILENAME']+'.gz'), 'app': PROGRAM, 'app_version': __version__, 'url': 'http://ctdbase.org/', 'comments': "Only disease associations with direct evidence are loaded into TCRD."} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'disease', 'where_clause': "dtype = 'CTD'"})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

def load_eRAM(args, dba, logger, logfile):
  s = shelve.open(CONFIG['eRAM']['SHELF_FILE'])
  dis_ct = len(s['disease_names'])
  if not args['--quiet']:
    print "Processing {} disease names in CTD shelf file {}".format(dis_ct, CONFIG['eRAM']['SHELF_FILE'])
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=dis_ct).start() 
  ct = 0
  pmark = {}
  skip_ct = 0
  dnerr1_ct = 0
  dnerr2_ct = 0
  notfnd = set()
  dis_ct = 0
  dba_err_ct = 0
  for dname in s['disease_names']:
    ct += 1
    try:
      dname = str(dname)
    except:
      dnerr2_ct += 1
      logger.warn("UnicodeEncodeError for disease name '{}'".format(dname.encode('ascii', 'ignore')))
      continue
    if dname not in s:
      dnerr_ct += 1
      logger.warn("Disease name '{}' not in shelf".format(dname))
      continue
    if 'currated_genes' not in s[dname]:
      skip_ct += 1
      continue
    for cg in s[dname]['currated_genes']:
      sym = cg['sym']
      geneid = cg['geneid']
      k = "%s|%s"%(sym,geneid)
      if k in notfnd:
        continue
      targets = dba.find_targets({'sym': sym})
      if not targets:
        targets = dba.find_targets({'geneid': geneid})
      if not targets:
        notfnd.add(k)
        logger.warn("No target found for {}".format(k))
        continue
      for t in targets:
        p = t['components']['protein'][0]
        pmark[t['id']] = True
        for doid in s[dname]['doids']:
          rv = dba.ins_disease( {'protein_id': p['id'], 'dtype': 'eRAM', 'name': dname,
                                 'did': doid, 'source': cg['sources']} )
          if not rv:
            dba_err_ct += 1
            continue
          dis_ct += 1
    pbar.update(ct)
  pbar.finish()
  print "{} lines processed.".format(ct)
  print "Loaded {} new disease rows for {} proteins".format(dis_ct, len(pmark))
  if skip_ct > 0:
    print "  Skipped {} diseases with no currated genes. See logfile {} for details.".format(skip_ct, logfile)
  if dnerr1_ct > 0:
    print "  {} disease names not found in shelf. See logfile {} for details.".format(dnerr1_ct, logfile)
  if dnerr2_ct > 0:
    print "  {} disease names cannot be decoded to strs. See logfile {} for details.".format(dnerr2_ct, logfile)
  if notfnd:
    print "  No target found for {} stringids/symbols. See logfile {} for details.".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'eRAM Disease Associations', 'source': 'Data scraped from eRAM web pages in October 2018.', 'app': PROGRAM, 'app_version': __version__, 'url': 'http://www.unimd.org/eram/', 'comments': ''} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'disease', 'where_clause': "dtype = 'eRAM'"})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)


if __name__ == '__main__':
  print "\n{} (v{}) [{}]:".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)

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

  print "\nWorking on JensenLab DISEASES..."
  download_DISEASES(args)
  start_time = time.time()
  load_DISEASES(args, dba, logger, logfile)
  elapsed = time.time() - start_time
  print "Done with DISEASES. Elapsed time: {}".format(slmf.secs2str(elapsed))

  print "\nWorking on DisGeNET..."
  download_DisGeNET(args)
  start_time = time.time()
  load_DisGeNET(args, dba, logger, logfile)
  elapsed = time.time() - start_time
  print "Done with DisGeNET. Elapsed time: {}".format(slmf.secs2str(elapsed))

  # Monarch
  print "\nWorking on Monarch..."
  start_time = time.time()
  load_Monarch(args, dba, logger, logfile)
  elapsed = time.time() - start_time
  print "Done with Monarch. Elapsed time: {}".format(slmf.secs2str(elapsed))
  
  # ExpressionAtlas
  print "\nWorking on Expression Atlas..."
  start_time = time.time()
  load_ExpressionAtlas(args, dba, logger, logfile)
  elapsed = time.time() - start_time
  print "Done with Expression Atlas. Elapsed time: {}".format(slmf.secs2str(elapsed))
  
  # CTD
  print "\nWorking on CTD..."
  start_time = time.time()
  load_CTD(args, dba, logger, logfile)
  elapsed = time.time() - start_time
  print "Done with CTD. Elapsed time: {}".format(slmf.secs2str(elapsed))
  
  # eRAM
  print "\nWorking on eRAM..."
  start_time = time.time()
  load_eRAM(args, dba, logger, logfile)
  elapsed = time.time() - start_time
  print "Done with eRAM. Elapsed time: {}".format(slmf.secs2str(elapsed))
  
  print "\n{}: Done.\n".format(PROGRAM)
