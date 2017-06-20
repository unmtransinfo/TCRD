#!/usr/bin/env python
# Time-stamp: <2017-06-19 15:07:46 smathias>
"""
Load Human Cell Atlas expression and compartment data into TCRD from CSV files.

Usage:
    load-HumanCellAtlas.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>] [--pastid=<int>]
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
  -d --debug DEBUGL    : set debugging output level (0-3) [default: 0]
  -? --help            : print this message and exit 
"""
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2017, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "1.0.0"

import os,sys,time
from docopt import docopt
import pandas as pd
import numpy as np
import csv
from TCRD import DBAdaptor
import logging
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = 'tcrd4logs/'
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

def load():
  args = docopt(__doc__, version=__version__)
  debug = int(args['--debug'])
  if debug:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  
  loglevel = int(args['--loglevel'])
  if args['--logfile']:
    logfile = args['--logfile']
  else:
    logfile = LOGFILE
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
    print "\nConnected to TCRD database %s (schema ver %s; data ver %s)" % (args['--dbname'], dbi['schema_ver'], dbi['data_ver'])
  
  # Dataset
  exp_dataset_id = dba.ins_dataset( {'name': 'Human Cell Atlas Expression', 'source': 'File Table S1 from http://science.sciencemag.org/content/suppl/2017/05/10/science.aal3321.DC1', 'app': PROGRAM, 'app_version': __version__, 'url': 'http://science.sciencemag.org/content/356/6340/eaal3321.full', 'comments': 'Qualitative expression values are generated by the loading app.'} )
  if not exp_dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  cpt_dataset_id = dba.ins_dataset( {'name': 'Human Cell Atlas Compartments', 'source': 'File Table S6 from http://science.sciencemag.org/content/suppl/2017/05/10/science.aal3321.DC1', 'app': PROGRAM, 'app_version': __version__, 'url': 'http://science.sciencemag.org/content/356/6340/eaal3321.full'} )
  if not cpt_dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  provs = [ {'dataset_id': exp_dataset_id, 'table_name': 'expression', 'where_clause': "etype = 'HCA RNA'", 'comment': 'TPM and qualitative expression values are derived from file Table S1 from http://science.sciencemag.org/content/suppl/2017/05/10/science.aal3321.DC1'},
            {'dataset_id': cpt_dataset_id, 'table_name': 'compartment', 'where_clause': "ctype = 'Human Cell Atlas'"} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    if not rv:
      print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
      sys.exit(1)

  if not args['--quiet']:
    print "\nCalculating expression level percentiles"
  pctiles = calc_pctiles()
  
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  
  #
  # Expressions
  #
  line_ct = wcl(RNA_FILE)
  if not args['--quiet']:
    print "\nProcessing %d lines from HCA file %s" % (line_ct, RNA_FILE)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  ct = 0
  notfnd = []
  dba_err_ct = 0
  tmark = {}
  exp_ct = 0
  with open(RNA_FILE, 'rU') as csvfile:
    csvreader = csv.reader(csvfile)
    header = csvreader.next()
    for row in csvreader:
      ct += 1
      pbar.update(ct)
      sym = row[1]
      ensg = row[0]
      targets = dba.find_targets({'sym': sym}, False)
      #if not targets:
      #  targets = dba.find_targets_by_xref({'xtype': 'Ensembl', 'value': ensg}, False)
      if not targets:
        k = "%s|%s"%(sym,ensg)
        notfnd.append(k)
        logger.warn("No target found for %s" % k)
        continue
      for t in targets:
        tmark[t['id']] = True
        pid = t['components']['protein'][0]['id']
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
  pbar.finish()
  print "Processed %d HCA lines." % ct
  print "  Inserted %d new expression rows" % exp_ct
  print "  %d proteins have HCA RNA expression data" % len(tmark)
  if notfnd:
    print "  No target found for %d lines. See logfile %s for details." % (len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)
  
  #
  # Compartments
  #
  line_ct = wcl(LOC_FILE)
  if not args['--quiet']:
    print "\nProcessing %d lines from HCA file %s" % (line_ct, LOC_FILE)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  ct = 0
  notfnd = []
  dba_err_ct = 0
  tmark = {}
  cpt_ct = 0
  with open(LOC_FILE, 'rU') as csvfile:
    csvreader = csv.reader(csvfile)
    header = csvreader.next()
    for row in csvreader:
      ct += 1
      pbar.update(ct)
      uniprot = row[2]
      sym = row[1]
      ensg = row[0]
      targets = dba.find_targets({'uniprot': uniprot}, False)
      if not targets:
        targets = dba.find_targets({'sym': sym}, False)
      #if not targets:
      #  targets = dba.find_targets_by_xref({'xtype': 'Ensembl', 'value': ensg}, False)
      if not targets:
        k = "%s|%s"%(sym,ensg)
        notfnd.append(k)
        logger.warn("No target found for %s" % k)
        continue
      t = targets[0]
      tmark[t['id']] = True
      pid = t['components']['protein'][0]['id']
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
  pbar.finish()
  print "Processed %d HCA lines." % ct
  print "  Inserted %d new compartment rows" % cpt_ct
  print "  %d proteins have HCA compartment data" % len(tmark)
  if notfnd:
    print "  No target found for %d lines. See logfile %s for details." % (len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)
      

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

def wcl(fname):
  with open(fname) as f:
    for i, l in enumerate(f):
      pass
  return i + 1

def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])

if __name__ == '__main__':
  print "\n%s (v%s) [%s]:" % (PROGRAM, __version__, time.strftime("%c"))
  start_time = time.time()
  load()
  elapsed = time.time() - start_time
  print "\n%s: Done. Elapsed time: %s\n" % (PROGRAM, secs2str(elapsed))
