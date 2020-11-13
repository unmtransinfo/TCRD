#!/usr/bin/env python
# Time-stamp: <2020-06-03 09:54:24 smathias>
"""Load Disease, Mammalian Phenotype, RGD Disease and Uberon Ontologies into TCRD.

Usage:
    load-Ontologies.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-Ontologies.py -h | --help

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

import os,sys,time,re
from docopt import docopt
from TCRD7 import DBAdaptor
import logging
import urllib
import obo
import pronto
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = 'tcrd7logs/'
LOGFILE = LOGDIR + '%s.log'%PROGRAM

def download(args, name):
  cfgd = [d for d in CONFIG if d['name'] == name][0]
  fn = cfgd['DOWNLOAD_DIR'] + cfgd['FILENAME']
  if os.path.exists(fn):
    os.remove(fn)
  url = cfgd['BASE_URL'] + cfgd['FILENAME']
  if not args['--quiet']:
    print "\nDownloading ", url
    print "         to ", fn
  urllib.urlretrieve(url, fn)
  if not args['--quiet']:
    print "Done."

def parse_do_obo(args, fn):
  if not args['--quiet']:
    print "Parsing Disease Ontology file {}".format(fn)
  do_parser = obo.Parser(open(fn))
  raw_do = {}
  for stanza in do_parser:
    if stanza.name != 'Term':
      continue
    raw_do[stanza.tags['id'][0].value] = stanza.tags
  dod = {}
  for doid,d in raw_do.items():
    if not doid.startswith('DOID:'):
      continue
    if 'is_obsolete' in d:
      continue
    init = {'doid': doid, 'name': d['name'][0].value}
    if 'def' in d:
      init['def'] = d['def'][0].value
    if 'is_a' in d:
      init['parents'] = []
      for parent in d['is_a']:
        init['parents'].append(parent.value)
    if 'xref' in d:
      init['xrefs'] = []
      for xref in d['xref']:
        if xref.value.startswith('http'):
          continue
        try:
          (db, val) = xref.value.split(':')
        except:
          pass
        init['xrefs'].append({'db': db, 'value': val})
    dod[doid] = init
  if not args['--quiet']:
    print "  Got {} Disease Ontology terms".format(len(dod))
  return dod

def load_do(args, dba, logger, logfile, dod, cfgd):
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  if not args['--quiet']:
    print "Loading {} Disease Ontology terms".format(len(dod))
  pbar = ProgressBar(widgets=pbar_widgets, maxval=len(dod)).start()
  ct = 0
  do_ct = 0
  dba_err_ct = 0
  for doid,d in dod.items():
    ct += 1
    d['doid'] = doid
    rv = dba.ins_do(d)
    if rv:
      do_ct += 1
    else:
      dba_err_ct += 1
    pbar.update(ct)
  pbar.finish()

  # Dataset
  # data-version field in the header of the OBO file has a relase version:
  # data-version: releases/2016-03-25
  for line in os.popen("head %s"%cfgd['DOWNLOAD_DIR'] + cfgd['FILENAME']):
    if line.startswith("data-version:"):
      ver = line.replace('data-version: ', '')
      break
  dataset_id = dba.ins_dataset( {'name': 'Disease Ontology', 'source': 'File %s, version %s'%(cfgd['BASE_URL']+cfgd['FILENAME'], ver), 'app': PROGRAM, 'app_version': __version__, 'url': 'http://disease-ontology.org/'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'do'})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'do_xref'})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)
  
  print "{} terms processed.".format(ct)
  print "  Inserted {} new do rows".format(do_ct)
  if dba_err_ct > 0:
    print "WARNNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

def parse_mpo_owl(args, fn):
  if not args['--quiet']:
    print "Parsing Mammalian Phenotype Ontology file {}".format(fn)
  mpo = []
  mpont = pronto.Ontology(fn)
  for term in mpont:
    if not term.id.startswith('MP:'):
      continue
    mpid = term.id
    name = term.name
    init = {'mpid': mpid, 'name': name}
    if term.parents:
      init['parent_id'] = term.parents[0].id
    if term.desc:
      if term.desc.startswith('OBSOLETE'):
        continue
      init['def'] = term.desc
    mpo.append(init)
  if not args['--quiet']:
    print "  Got {} Mammalian Phenotype Ontology terms".format(len(mpo))
  return mpo

def load_mpo(args, dba, logger, logfile, mpo, cfgd):
  if not args['--quiet']:
    print "Loading {} Mammalian Phenotype Ontology terms".format(len(mpo))
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=len(mpo)).start()
  ct = 0
  mpo_ct = 0
  dba_err_ct = 0
  for mpd in mpo:
    ct += 1
    rv = dba.ins_mpo(mpd)
    if rv:
      mpo_ct += 1
    else:
      dba_err_ct += 1
    pbar.update(ct)
  pbar.finish()

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'Mammalian Phenotype Ontology', 'source': 'OWL file downloaded from %s'%cfgd['BASE_URL']+cfgd['FILENAME'], 'app': PROGRAM, 'app_version': __version__} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'mpo'})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)
  
  print "{} terms processed.".format(ct)
  print "  Inserted {} new mpo rows".format(mpo_ct)
  if dba_err_ct > 0:
    print "WARNNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

def parse_rdo_obo(args, fn):
  if not args['--quiet']:
    print "Parsing RGD Disease Ontology file {}".format(fn)
  rdo_parser = obo.Parser(open(fn))
  raw_rdo = {}
  for stanza in rdo_parser:
    if stanza.name != 'Term':
      continue
    raw_rdo[stanza.tags['id'][0].value] = stanza.tags
  rdod = {}
  for doid,d in raw_rdo.items():
    if not doid.startswith('DOID:'):
      continue
    if 'is_obsolete' in d:
      continue
    init = {'doid': doid, 'name': d['name'][0].value}
    if 'def' in d:
      init['def'] = d['def'][0].value
    # if 'is_a' in d:
    #   init['parents'] = []
    #   for parent in d['is_a']:
    #     init['parents'].append(parent.value)
    if 'alt_id' in d:
      init['xrefs'] = []
      for aid in d['alt_id']:
        if aid.value.startswith('http'):
          continue
        try:
          (db, val) = aid.value.split(':')
        except:
          pass
        init['xrefs'].append({'db': db, 'value': val})
    if 'xref' in d:
      if 'xrefs' not in init:
        init['xrefs'] = []
      for xref in d['xref']:
        if xref.value.startswith('http'):
          continue
        try:
          (db, val) = xref.value.split(':')
        except:
          pass
        init['xrefs'].append({'db': db, 'value': val})
    rdod[doid] = init
  if not args['--quiet']:
    print "  Got {} RGD Disease Ontology terms".format(len(rdod))
  return rdod

def load_rdo(args, dba, logger, logfile, rdod, cfgd):      
  if not args['--quiet']:
    print "Loading {} RGD Disease Ontology terms".format(len(rdod))
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=len(rdod)).start()
  ct = 0
  rdo_ct = 0
  dba_err_ct = 0
  for doid,d in rdod.items():
    ct += 1
    d['doid'] = doid
    rv = dba.ins_rdo(d)
    if rv:
      rdo_ct += 1
    else:
      dba_err_ct += 1
    pbar.update(ct)
  pbar.finish()

  # Dataset
  # data-version field in the header of the OBO file has a relase version:
  # data-version: 1.28
  f = os.popen("head %s"%cfgd['DOWNLOAD_DIR'] + cfgd['FILENAME'])
  for line in f:
    if line.startswith("data-version:"):
      ver = line.replace('data-version: ', '')
      break
  f.close()
  dataset_id = dba.ins_dataset( {'name': 'RGD Disease Ontology', 'source': 'File %s, version %s'%(cfgd['BASE_URL']+cfgd['FILENAME'], ver), 'app': PROGRAM, 'app_version': __version__} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'rdo'})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'rdo_xref'})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

  print "{} terms processed.".format(ct)
  print "  Inserted {} new rdo rows".format(rdo_ct)
  if dba_err_ct > 0:
    print "WARNNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

def parse_uberon_obo(args, fn):
  if not args['--quiet']:
    print "Parsing Uberon Ontology file {}".format(fn)
  uber_parser = obo.Parser(open(fn))
  raw_uber = {}
  for stanza in uber_parser:
    if stanza.name != 'Term':
      continue
    raw_uber[stanza.tags['id'][0].value] = stanza.tags
  uberd = {}
  for uid,ud in raw_uber.items():
    if 'is_obsolete' in ud:
      continue
    if 'name' not in ud:
      continue
    init = {'uid': uid, 'name': ud['name'][0].value}
    if 'def' in ud:
      init['def'] = ud['def'][0].value
    if 'comment' in ud:
      init['comment'] = ud['comment'][0].value
    if 'is_a' in ud:
      init['parents'] = []
      for parent in ud['is_a']:
        # some parent values have a source ie. 'UBERON:0010134 {source="MA"}'
        # get rid of this for now
        cp = parent.value.split(' ')[0]
        init['parents'].append(cp)
    if 'xref' in ud:
      init['xrefs'] = []
      for xref in ud['xref']:
        if xref.value.startswith('http'):
          continue
        try:
          (db, val) = xref.value.split(':')
        except:
          pass
        if not db.isupper():
          # there are all kinds of xrefs like xref: Wolffian:duct
          # skip these
          continue
        if db.endswith('_RETIRED'):
          continue
        init['xrefs'].append({'db': db, 'value': val})
    uberd[uid] = init
  if not args['--quiet']:
    print "  Got {} Uberon Ontology terms".format(len(uberd))
  return uberd

def load_uberon(args, dba, logger, logfile, uberd, cfgd):
  if not args['--quiet']:
    print "Loading {} Uberon terms".format(len(uberd))
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=len(uberd)).start()
  ct = 0
  uberon_ct = 0
  dba_err_ct = 0
  for uid,ud in uberd.items():
    ct += 1
    ud['uid'] = uid
    rv = dba.ins_uberon(ud)
    if rv:
      uberon_ct += 1
    else:
      dba_err_ct += 1
    pbar.update(ct)
  pbar.finish()

  # Dataset
  # data-version field in the header of the OBO file has a relase version:
  # data-version: releases/2016-03-25
  f = os.popen("head %s"%cfgd['DOWNLOAD_DIR'] + cfgd['FILENAME'])
  for line in f:
    if line.startswith("data-version:"):
      ver = line.replace('data-version: ', '')
      break
  f.close()
  dataset_id = dba.ins_dataset( {'name': 'Uberon Ontology', 'source': 'File %s, version %s'%(cfgd['BASE_URL']+cfgd['FILENAME'], ver), 'app': PROGRAM, 'app_version': __version__, 'url': 'http://uberon.github.io/'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'uberon'} ,
            {'dataset_id': dataset_id, 'table_name': 'uberon_parent'},
            {'dataset_id': dataset_id, 'table_name': 'uberon_xref'} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)
  
  print "{} terms processed.".format(ct)
  print "  Inserted {} new uberon rows".format(uberon_ct)
  if dba_err_ct > 0:
    print "WARNNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)


CONFIG = [ {'name': 'Disease Ontology', 'DOWNLOAD_DIR': '../data/DiseaseOntology/', 
              'BASE_URL': 'http://purl.obolibrary.org/obo/', 'FILENAME': 'doid.obo',
              'parse_function': parse_do_obo, 'load_function': load_do},
           {'name': 'Mammalian Phenotype Ontology', 'DOWNLOAD_DIR': '../data/MPO/', 
            'BASE_URL': 'http://www.informatics.jax.org/downloads/reports/', 'FILENAME': 'mp.owl',
              'parse_function': parse_mpo_owl, 'load_function': load_mpo},
           {'name': 'RGD Disease Ontology', 'DOWNLOAD_DIR': '../data/RGD/', 
            'BASE_URL': 'ftp://ftp.rgd.mcw.edu/pub/ontology/disease/', 'FILENAME': 'RDO.obo',
              'parse_function':parse_rdo_obo, 'load_function': load_rdo },
           {'name': 'Uberon Ontology', 'DOWNLOAD_DIR': '../data/Uberon/', 
            'BASE_URL': 'http://purl.obolibrary.org/obo/uberon/', 'FILENAME': 'ext.obo',
              'parse_function': parse_uberon_obo, 'load_function': load_uberon} ]


if __name__ == '__main__':
  print "\n{} (v{}) [{}]:".format(PROGRAM, __version__, time.strftime("%c"))
  start_time = time.time()
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

  for cfgd in CONFIG:
    name = cfgd['name']
    download(args, name)
    parsed_ont = cfgd['parse_function'](args, cfgd['DOWNLOAD_DIR']+cfgd['FILENAME'])
    cfgd['load_function'](args, dba, logger, logfile, parsed_ont, cfgd)
    
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))
