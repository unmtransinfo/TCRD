#!/usr/bin/env python
# Time-stamp: <2019-08-20 10:36:44 smathias>
"""
Load Human Cell Atlas expression and compartment data into TCRD from CSV files.

Usage:
    load-HumanCellAtlas.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>] [--pastid=<int>]
    load-HumanCellAtlas.py -h | --help

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
__copyright__ = "Copyright 2017-2019, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.0.0"

import os,sys,time
from docopt import docopt
from TCRDMP import DBAdaptor
import pandas as pd
import numpy as np
from collections import defaultdict
import csv
import logging
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = 'tcrd6logs/'
LOGFILE = LOGDIR+'%s.log'%PROGRAM
RNA_FILE = '../data/HCA/aal3321_Thul_SM_table_S1.csv'
LOC_FILE = '../data/HCA/aal3321_Thul_SM_table_S6.csv'
# map column header names to (GO Term, GO ID)
COMPARTMENTS = {'Nucleus': ('Nucleus', 'GO:0005634'),
                'Nucleoplasm': ('Nucleoplasm', 'GO:0005654'),
                'Nuclear bodies': ('Nuclear bodies', 'GO:0016604'),
                'Nuclear speckles': ('Nuclear speckles', 'GO:0016607'),
                'Nuclear membrane': ('Nuclear membrane', 'GO:0031965'),
                'Nucleoli': ('Nucleoli', 'GO:0005730'),
                'Nucleoli (Fibrillar center)': ('Nucleoli fibrillar center', 'GO:0001650'),
                'Cytosol': ('Cytosol', 'GO:0005829'),
                'Cytoplasmic bodies': ('Cytoplasmic bodies', 'GO:0000932'),
                'Rods and Rings': ('Rods & Rings', ''),
                'Lipid droplets': ('Lipid droplets', 'GO:0005811'),
                'Aggresome': ('Aggresome', 'GO:0016235'),
                'Mitochondria': ('Mitochondria', 'GO:0005739'),
                'Microtubules': ('Microtubules', 'GO:0015630'),
                'Microtubule ends': ('Microtubule ends', 'GO:1990752'),
                'Microtubule organizing center': ('Microtubule organizing center', 'GO:0005815'),
                'Centrosome': ('Centrosome', 'GO:0005813'),
                'Mitotic spindle': ('Mitotic spindle', 'GO:0072686'),
                'Cytokinetic bridge': ('Cytokinetic bridge ', 'GO:0045171'),
                'Midbody': ('Midbody', 'GO:0030496'),
                'Midbody ring': ('Midbody ring', 'GO:0070938'),
                'Intermediate filaments': ('Intermediate filaments', 'GO:0045111'),
                'Actin filaments': ('Actin filaments', 'GO:0015629'),
                'Focal Adhesions': ('Focal adhesion sites', 'GO:0005925'),
                'Endoplasmic reticulum': ('Endoplasmic reticulum', 'GO:0005783'),
                'Golgi apparatus': ('Golgi apparatus', 'GO:0005794'),
                'Vesicles': ('Vesicles', 'GO:0043231'),
                'Plasma membrane': ('Plasma membrane', 'GO:0005886'),
                'Cell Junctions': ('Cell Junctions', 'GO:0030054')}

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
  exp_dataset_id = dba.ins_dataset( {'name': 'Human Cell Atlas Expression', 'source': 'File Table S1 from http://science.sciencemag.org/content/suppl/2017/05/10/science.aal3321.DC1', 'app': PROGRAM, 'app_version': __version__, 'url': 'http://science.sciencemag.org/content/356/6340/eaal3321.full', 'comments': 'Qualitative expression values are generated by the loading app.'} )
  assert exp_dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  cpt_dataset_id = dba.ins_dataset( {'name': 'Human Cell Atlas Compartments', 'source': 'File Table S6 from http://science.sciencemag.org/content/suppl/2017/05/10/science.aal3321.DC1', 'app': PROGRAM, 'app_version': __version__, 'url': 'http://science.sciencemag.org/content/356/6340/eaal3321.full'} )
  assert cpt_dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  provs = [ {'dataset_id': exp_dataset_id, 'table_name': 'expression', 'where_clause': "etype = 'HCA RNA'", 'comment': 'TPM and qualitative expression values are derived from file Table S1 from http://science.sciencemag.org/content/suppl/2017/05/10/science.aal3321.DC1'},
            {'dataset_id': cpt_dataset_id, 'table_name': 'compartment', 'where_clause': "ctype = 'Human Cell Atlas'"} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

  if not args['--quiet']:
    print "\nCalculating expression level percentiles"
  pctiles = calc_pctiles()
  
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  
  #
  # Expressions
  #
  line_ct = slmf.wcl(RNA_FILE)
  if not args['--quiet']:
    print "\nProcessing {} lines from HCA file {}".format(line_ct, RNA_FILE)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  ct = 0
  k2pids = defaultdict(list)
  notfnd = set()
  dba_err_ct = 0
  pmark = {}
  exp_ct = 0
  with open(RNA_FILE, 'rU') as csvfile:
    csvreader = csv.reader(csvfile)
    header = csvreader.next()
    for row in csvreader:
      ct += 1
      pbar.update(ct)
      sym = row[1]
      ensg = row[0]
      k = "%s|%s"%(sym,ensg)
      if k in k2pids:
        # we've already found it
        pids = k2pids[k]
      elif k in notfnd:
        # we've already not found it
        continue
      else:
        # look it up
        targets = dba.find_targets({'sym': sym}, False)
        if not targets:
          targets = dba.find_targets_by_xref({'xtype': 'Ensembl', 'value': ensg}, False)
        if not targets:
          notfnd.add(k)
          continue
        pids = []
        for t in targets:
          pids.append(t['components']['protein'][0]['id'])
        k2pids[k] = pids
      for pid in pids:
        cell_lines = [c.replace(' (TPM)', '') for c in header[2:]]
        for (i,cl) in enumerate(cell_lines):
          tpm_idx = i + 2 # add two because row has ENSG and Gene at beginning
          tpm = float(row[tpm_idx])
          qv = calc_qual_value( tpm, pctiles[cl] )
          rv = dba.ins_expression( {'protein_id': pid, 'etype': 'HCA RNA',
                                    'tissue': 'Cell Line '+cl, 
                                    'qual_value': qv, 'number_value': tpm} )
          if not rv:
            dba_err_ct += 1
            continue
          exp_ct += 1
        pmark[pid] = True
  pbar.finish()
  for k in notfnd:
    logger.warn("No target found for {}".format(k))
  print "Processed {} lines.".format(ct)
  print "  Inserted {} new expression rows for {} proteins.".format(exp_ct, len(pmark))
  if notfnd:
    print "  No target found for {} Symbols/ENSGs. See logfile {} for details".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

  #
  # Compartments
  #
  line_ct = slmf.wcl(LOC_FILE)
  if not args['--quiet']:
    print "\nProcessing {} lines from HCA file {}".format(line_ct, LOC_FILE)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  ct = 0
  k2pids = defaultdict(list)
  notfnd = set()
  dba_err_ct = 0
  pmark = {}
  cpt_ct = 0
  with open(LOC_FILE, 'rU') as csvfile:
    csvreader = csv.reader(csvfile)
    header = csvreader.next()
    for row in csvreader:
      ct += 1
      pbar.update(ct)
      uniprot = row[2]
      sym = row[1]
      k = "%s|%s"%(uniprot,sym)
      if k in k2pids:
        # we've already found it
        pids = k2pids[k]
      elif k in notfnd:
        # we've already not found it
        continue
      else:
        # look it up
        targets = dba.find_targets({'uniprot': uniprot}, False)
        if not targets:
          targets = dba.find_targets({'sym': sym}, False)
        if not targets:
          notfnd.add(k)
          continue
        pids = []
        for t in targets:
          pids.append(t['components']['protein'][0]['id'])
        k2pids[k] = pids
      for pid in pids:
        compartments = [c for c in header[3:-5]]
        for (i,c) in enumerate(compartments):
          val_idx = i + 3 # add three because row has ENSG,Gene,Uniprot at beginning
          val = int(row[val_idx])
          if val == 0:
            continue
          rel = row[-5]
          if rel == 'Uncertain':
            continue
          rv = dba.ins_compartment( {'protein_id': pid, 'ctype': 'Human Cell Atlas',
                                     'go_id': COMPARTMENTS[c][1], 
                                     'go_term': COMPARTMENTS[c][0], 'reliability': rel} )
          if not rv:
            dba_err_ct += 1
            continue
          cpt_ct += 1
        pmark[pid] = True
  pbar.finish()
  print "Processed {} lines.".format(ct)
  print "  Inserted {} new compartment rows for {} protein.s".format(cpt_ct, len(pmark))
  if notfnd:
    print "  No target found for {} UniProts/Symbols. See logfile {} for details".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

def calc_qual_value(tpm, pctiles):
  # pctiles here is a tuple of 33rd and 66th percentiles
  if tpm == 0:
    qv = 'Not detected'
  elif tpm <= pctiles[0]:
    qv = 'Low'
  elif tpm <= pctiles[1]:
    qv = 'Medium'
  else:
    qv = 'High'
  return qv

def calc_pctiles():
  pctiles = {}
  df = pd.read_csv(RNA_FILE)
  cell_lines = [c for c in df.columns[2:]]
  for cl in cell_lines:
    a = df[cl].values
    a = np.delete(a, np.where(a == 0))
    cl = cl.replace(' (TPM)', '') 
    pctiles[cl] = (np.percentile(a, 33), np.percentile(a, 66))
  return pctiles


if __name__ == '__main__':
  print "\n{} (v{}) [{}]:".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  start_time = time.time()
  load(args)
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))
