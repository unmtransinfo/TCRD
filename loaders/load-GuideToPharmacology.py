#!/usr/bin/env python
# Time-stamp: <2019-04-09 13:07:09 smathias>
"""Load cmpd_activity data into TCRD from Guide to Pharmacology CSV files.

Usage:
    load-GuideToPharmacology.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-GuideToPharmacology.py -? | --help

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
__copyright__ = "Copyright 2018-2019, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "1.1.0"

import os,sys,time
from docopt import docopt
from TCRDMP import DBAdaptor
import logging
import csv
import urllib
from collections import defaultdict
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd6logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
DOWNLOAD_DIR = '../data/GuideToPharmacology/'
BASE_URL = 'http://www.guidetopharmacology.org/DATA/'
#T_FILE = 'targets_and_families.csv'
L_FILE = 'ligands.csv'
I_FILE = 'interactions.csv'
SRC_FILES = [os.path.basename(L_FILE),
             os.path.basename(I_FILE)]

def download(args):
  for f in [L_FILE, I_FILE]:
    if os.path.exists(DOWNLOAD_DIR + f):
      os.remove(DOWNLOAD_DIR + f)
    if not args['--quiet']:
      print "Downloading ", BASE_URL + f
      print "         to ", DOWNLOAD_DIR + f
    urllib.urlretrieve(BASE_URL + f, DOWNLOAD_DIR + f)

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
  dataset_id = dba.ins_dataset( {'name': 'Guide to Pharmacology', 'source': 'Files %s from %s'%(", ".join(SRC_FILES), BASE_URL), 'app': PROGRAM, 'app_version': __version__, 'url': 'http://www.guidetopharmacology.org/'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'cmpd_activity', 'where_clause': "ctype = 'Guide to Pharmacology'"})
  if not rv:
    print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
    sys.exit(1)

  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]

  fn = DOWNLOAD_DIR+L_FILE
  line_ct = slmf.wcl(fn)
  if not args['--quiet']:
    print "\nProcessing {} lines in input file {}".format(line_ct, fn)
  ligands = {}
  skip_ct = 0
  with open(fn, 'rU') as ifh:
    csvreader = csv.reader(ifh)
    header = csvreader.next() # skip header line
    ct = 1
    for row in csvreader:
      # These are the fields in version 2019.2
      # 0 Ligand id               The GtP ligand identifier
      # 1 Name                    The name of the ligand
      # 2 Species                 (Peptides) The species which endogenously express a particular peptide ligand sequence
      # 3 Type                    The type of chemical
      # 4 Approved                The drug is or has in the past been approved for human clinical use by a regulatory agency
      # 5 Withdrawn               The drug is no longer approved for its original clinical use in one or more countries 
      # 6 Labelled                The ligand has been labelled with a chemical group such as a fluorscent tag or unstable isotope
      # 7 Radioactive             Ligand has been labelled with radioactive isotope
      # 8 PubChem SID             The PubChem Substance identifier assigned when we deposited the ligand in PubChem
      # 9 PubChem CID             Our curated PubChem Compound database link
      # 10 UniProt id              (Peptides) The UniProtKB/SwissProt Accession for peptide sequences
      # 11 IUPAC name              The IUPAC chemical name
      # 12 INN                 The International Non-proprietary Name assigned by the WHO
      # 13 Synonyms                Commonly used synonyms from the literature
      # 14 SMILES                  Specification of the chemical structure in canonical, isomeric SMILES format
      # 15 InChIKey                A hashed version of the full InChI designed for easy web searches of chemical compounds
      # 16 InChI                   A textual identifier for the chemical structure
      ct += 1
      ligand_id = int(row[0])
      ligand_type = row[3]
      if ligand_type == 'Antibody' or ligand_type == 'Peptide':
        skip_ct += 1
        continue
      ligands[ligand_id] = {'name': row[1], 'pubchem_cid': row[9], 'smiles': row[14]}
  if not args['--quiet']:
    print "  Got info for {} ligands".format(len(ligands))
    print "  Skipped {} antibodies/peptides".format(skip_ct)

  # this dict will map uniprot|sym from interactions file to TCRD target(s)
  # so we only have to find target(s) once for each pair.
  k2ts = defaultdict(list)
  fn = DOWNLOAD_DIR+I_FILE
  line_ct = slmf.wcl(fn)
  if not args['--quiet']:
    print "\nProcessing {} lines in input file {}".format(line_ct, fn)
  with open(fn, 'rU') as ifh:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    csvreader = csv.reader(ifh)
    header = csvreader.next() # skip header line
    ct = 1
    tmark = {}
    ca_ct = 0
    ap_ct = 0
    md_ct = 0
    ba_ct = 0
    notfnd = set()
    dba_err_ct = 0
    for row in csvreader:
      # NB. these do NOT match the file descriptions on the site. This is directly from the header
      # 0 target
      # 1 target_id
      # 2 target_gene_symbol
      # 3 target_uniprot
      # 4 target_ensembl_gene_id
      # 5 target_ligand
      # 6 target_ligand_id
      # 7 target_ligand_gene_symbol
      # 8 target_ligand_ensembl_gene_id
      # 9 target_ligand_uniprot
      # 10 target_ligand_pubchem_sid
      # 11 target_species
      # 12 ligand
      # 13 ligand_id
      # 14 ligand_gene_symbol
      # 15 ligand_species
      # 16 ligand_pubchem_sid
      # 17 type
      # 18 action
      # 19 action_comment
      # 20 selectivity
      # 21 endogenous
      # 22 primary_target
      # 23 concentration_range
      # 24 affinity_units
      # 25 affinity_high
      # 26 affinity_median
      # 27 affinity_low
      # 28 original_affinity_units
      # 29 original_affinity_low_nm
      # 30 original_affinity_median_nm
      # 31 original_affinity_high_nm
      # 32 original_affinity_relation
      # 33 assay_description
      # 34 receptor_site
      # 35 ligand_context
      # 36 pubmed_id
      ct += 1
      pbar.update(ct)
      lid = int(row[13])
      if lid not in ligands:
        ap_ct += 1
        continue
      if row[26] == '': # no activity value
        md_ct += 1
        continue
      if '|' in row[3]:
        skip_ct += 1
        continue
      val = "%.8f"%float(row[26])
      act_type = row[28]
      up = row[3]
      sym = row[2]
      k = "%s|%s"%(up,sym)
      if k == '|':
        md_ct += 1
        continue
      if k in k2ts:
        # already found target(s)
        ts = k2ts[k]
      elif k in notfnd:
        # already didn't find target(s)
        continue
      else:
        # lookup target(s)
        targets = dba.find_targets({'uniprot': up})
        if not targets:
          targets = dba.find_targets({'sym': sym})
          if not targets:
            notfnd.add(k)
            logger.warn("No target found for {}".format(k))
            continue
        ts = []
        for t in targets:
          ts.append({'id': t['id'], 'fam': t['fam']})
        k2ts[k] = ts
      if row[36] and row[36] != '':
        pmids = row[36]
      else:
        pmids = None
      if ligands[lid]['pubchem_cid'] == '':
        pccid = None
      else:
        pccid = ligands[lid]['pubchem_cid']
      for t in ts:
        if t['fam'] == 'GPCR':
          cutoff =  7.0 # 100nM
        elif t['fam'] == 'IC':
          cutoff = 5.0 # 10uM
        elif t['fam'] == 'Kinase':
          cutoff = 7.52288 # 30nM
        elif t['fam'] == 'NR':
          cutoff =  7.0 # 100nM
        else:
          cutoff = 6.0 # 1uM for non-IDG Family targets
        if val >= cutoff:
          # target is Tchem, save activity
          tmark[t['id']] = True
          rv = dba.ins_cmpd_activity( {'target_id': t['id'], 'catype': 'Guide to Pharmacology',
                                       'cmpd_id_in_src': lid,
                                       'cmpd_name_in_src': ligands[lid]['name'],
                                       'smiles': ligands[lid]['smiles'], 'act_value': val,
                                       'act_type': act_type, 'pubmed_ids': pmids,
                                       'cmpd_pubchem_cid': pccid} )
          if not rv:
            dba_err_ct += 1
            continue
          ca_ct += 1
        else:
          ba_ct += 1
  pbar.finish()
  print "{} rows processed.".format(ct)
  print "  Inserted {} new cmpd_activity rows for {} targets".format(ca_ct, len(tmark))
  print "  Skipped {} with below cutoff activity values".format(ba_ct)
  print "  Skipped {} activities with multiple targets".format(skip_ct)
  print "  Skipped {} antibody/peptide activities".format(ap_ct)
  print "  Skipped {} activities with missing data".format(md_ct)
  if notfnd:
    print "No target found for {} uniprots/symbols. See logfile {} for details.".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)
  
  
if __name__ == '__main__':
  print "\n{} (v{}) [{}]:\n".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  start_time = time.time()
  download(args)
  load(args)
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))
