#!/usr/bin/env python
# Time-stamp: <2020-07-29 13:40:00 smathias>
"""Load disease associations into TCRD.

Usage:
    load-Phenotypes.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-Phenotypes.py -h | --help

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
import csv
import logging
import urllib
import pronto
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd7logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)

CONFIG = {'OMIM':
          # One must register to get OMIM downloads. This gives a user-specific download link.
          # NB. the phenotypic series file must be added to one's key's entitlements by OMIM staff.
          # To view a list of all the data a key has access to, go to:
          # https://omim.org/downloads/<key>
                  {'DOWNLOAD_DIR': '../data/OMIM/',
                   'BASE_URL': 'https://data.omim.org/downloads/ey9G4kaCTGCQ-q_Yx0XAPg/',
                   'GENEMAP2_FILE': 'genemap2.txt',
                   'TITLES_FILE': 'mimTitles.txt',
                   'PS_FILE': 'phenotypicSeries.txt',
                   'SRC_FILES': "genemap2.txt, mimTitles.txt, phenotypicSeries.txt"},
          'GWAS Catalog':
          # File description is here:
          # http://www.ebi.ac.uk/gwas/docs/fileheaders
          # Get file here:
          # https://www.ebi.ac.uk/gwas/docs/file-downloads
          # or directly via
          # https://www.ebi.ac.uk/gwas/api/search/downloads/alternative
                          {'DOWNLOAD_DIR': '../data/EBI/',
                           'FILENAME': 'gwas_catalog_v1.0.2-associations_e100_r2020-07-14.tsv'},
            
          'IMPC':
          # Download files from ftp://ftp.ebi.ac.uk/pub/databases/impc/release-*.*/csv/
                  {'DOWNLOAD_DIR': '../data/IMPC/',
                   'GENO_PHENO_FILE': 'IMPC_genotype_phenotype.csv',
                   'STAT_RES_FILE': 'IMPC_ALL_statistical_results.csv'},
          'JAX': {'DOWNLOAD_DIR': '../data/JAX/',
                  'BASE_URL': 'http://www.informatics.jax.org/downloads/reports/',
                  'FILENAME': 'HMD_HumanPhenotype.rpt'},
          'RGD':
          # The input file is produced by the Rscript ../R/process-RGD.R
          # Details/explanation of that code are in ../notebooks/RGD.ipynb
                 {'DOWNLOAD_DIR': '../data/RGD/',
                  'QTL_FILE': 'rat_qtls.tsv',
                  'TERMS_FILE': 'rat_terms.tsv'},
          'MPO_OWL_FILE': '../data/MPO/mp.owl'
          }

def download_OMIM():
  for fn in [CONFIG['OMIM']['GENEMAP2_FILE'], CONFIG['OMIM']['TITLES_FILE'], CONFIG['OMIM']['PS_FILE']]:
    if os.path.exists(CONFIG['OMIM']['DOWNLOAD_DIR'] + fn):
      os.rename(CONFIG['OMIM']['DOWNLOAD_DIR'] + fn, CONFIG['OMIM']['DOWNLOAD_DIR'] + fn + '.bak')
    print "Downloading ", CONFIG['OMIM']['BASE_URL'] + fn
    print "         to ", CONFIG['OMIM']['DOWNLOAD_DIR'] + fn
    urllib.urlretrieve(CONFIG['OMIM']['BASE_URL'] + fn, CONFIG['OMIM']['DOWNLOAD_DIR'] + fn)
  print "Done."

def load_OMIM(args, dba, logger, logfile):
  # OMIMs and Phenotypic Series
  fn = CONFIG['OMIM']['DOWNLOAD_DIR'] + CONFIG['OMIM']['TITLES_FILE']
  line_ct = slmf.wcl(fn)
  if not args['--quiet']:
    print 'Processing %d lines from input file %s' % (line_ct, fn)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start()
  with open(fn, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    skip_ct = 0
    omim_ct = 0
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
      if row[0].startswith('#'):
        # The file has commented lines
        skip_ct += 1
        continue
      # The fields are:
      # 0: Prefix ???
      # 1: Mim Number
      # 2: Preferred Title; symbol Alternative Title(s); symbol(s)
      # 3: Included Title(s); symbols
      title = row[2].partition(';')[0]
      rv = dba.ins_omim({'mim': row[1], 'title': title})
      if not rv:
        dba_err_ct += 1
        continue
      omim_ct += 1
      pbar.update(ct)
  pbar.finish()
  print "{} lines processed".format(ct)
  print "Loaded {} new omim rows".format(omim_ct)
  print "  Skipped {} commented lines.".format(skip_ct)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

  fn = CONFIG['OMIM']['DOWNLOAD_DIR'] + CONFIG['OMIM']['PS_FILE']
  line_ct = slmf.wcl(fn)
  if not args['--quiet']:
    print 'Processing %d lines from input file %s' % (line_ct, fn)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start()
  with open(fn, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    skip_ct = 0
    ps_ct = 0
    err_ct = 0
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
      if row[0].startswith('#'):
        # The file has commented lines
        skip_ct += 1
        continue
      # The fields are:
      # 0: Phenotypic Series Number
      # 1: Mim Number
      # 2: Phenotype
      if len(row) ==2:
        init = {'omim_ps_id': row[0], 'title': row[1]}
      elif len(row) == 3:
        init = {'omim_ps_id': row[0], 'mim': row[1], 'title': row[2]}
      else:
        err_ct += 1
        logger.warn("Parsing error for row {}".format(row))
        continue
      rv = dba.ins_omim_ps(init)
      if not rv:
        dba_err_ct += 1
        continue
      ps_ct += 1
      pbar.update(ct)
  pbar.finish()
  print "{} lines processed".format(ct)
  print "Loaded {} new omim_ps rows".format(ps_ct)
  print "  Skipped {} commented lines.".format(skip_ct)
  if err_ct > 0:
    print "WARNING: {} parsing errors occurred. See logfile {} for details.".format(er_ct, logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)
    
  # Phenotypes
  fn = CONFIG['OMIM']['DOWNLOAD_DIR'] + CONFIG['OMIM']['GENEMAP2_FILE']
  line_ct = slmf.wcl(fn)
  if not args['--quiet']:
    print 'Processing %d lines from input file %s' % (line_ct, fn)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start()
  with open(fn, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    pmark = {}
    skip_ct = 0
    notfnd_ct = 0
    prov_ct = 0
    dds_ct = 0
    pt_ct = 0
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
      if row[0].startswith('#'):
        # The file has commented lines
        skip_ct += 1
        continue
      # The fields are:
      # 0: Chromosome
      # 1: Genomic Position Start
      # 2: Genomic Position End
      # 3: Cyto Location
      # 4: Computed Cyto Location
      # 5: MIM Number
      # 6: Gene Symbols
      # 7: Gene Name
      # 8: Approved Symbol
      # 9. Entrez Gene ID
      # 10: Ensembl Gene ID
      # 11: Comments
      # 12: Phenotypes
      # 13: Mouse Gene Symbol/ID
      pts = row[11]
      if pts.startswith('?'):
        prov_ct += 1
        continue
      if '(4)' in pts:
        dds_ct += 1
      trait = "MIM Number: %s" % row[5]
      if pts:
        trait += "; Phenotype: %s" % pts
      if row[8]:
        syms = [row[8]]
      else:
        syms = syms = row[5].split(', ')
      logger.info("Checking for OMIM syms: {}".format(syms))
      for sym in syms:
        targets = dba.find_targets({'sym': sym})
        if not targets and row[9]:
          targets = dba.find_targets({'geneid': int(row[9])})
        if not targets:
          notfnd_ct += 1
          logger.warn("No target found for row {}".format(row))
          continue
      for t in targets:
        p = t['components']['protein'][0]
        rv = dba.ins_phenotype({'protein_id': p['id'], 'ptype': 'OMIM', 'trait': trait})
        if not rv:
          dba_err_ct += 1
          continue
        pmark[p['id']] = True
        pt_ct += 1
      pbar.update(ct)
  pbar.finish()
  print "{} lines processed".format(ct)
  print "Loaded {} OMIM phenotypes for {} proteins".format(pt_ct, len(pmark))
  print "  Skipped {} commented lines.".format(skip_ct)
  print "  Skipped {} provisional phenotype rows.".format(prov_ct)
  if dds_ct > 0:
    print "  Skipped {} deletion/duplication syndrome rows.".format(dds_ct)
  if notfnd_ct > 0:
    print "  No target found for {} good lines. See logfile {} for details.".format(notfnd_ct, logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)
  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'OMIM', 'source': 'Files %s from http:data.omim.org'%(", ".join(CONFIG['OMIM']['SRC_FILES'])), 'app': PROGRAM, 'app_version': __version__, 'url': 'http://omim.org/', 'comments': 'OMIM phenotype associations and Phenotype Series info. Neither provisional associations nor deletion/duplication syndromes are loaded.'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'omim'},
            {'dataset_id': dataset_id, 'table_name': 'omim_ps'},
            {'dataset_id': dataset_id, 'table_name': 'phenotype', 'where_clause': "ptype = 'OMIM'"} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

def load_GWASCatalog(args, dba, logger, logfile):
  fn = CONFIG['GWAS Catalog']['DOWNLOAD_DIR'] + CONFIG['GWAS Catalog']['FILENAME']
  line_ct = slmf.wcl(fn)
  if not args['--quiet']:
    print 'Processing {} lines GWAS Catalog file {}'.format(line_ct, fn)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start()
  outlist = []
  with open(fn, 'rU') as tsvfile:
    tsvreader = csv.reader(tsvfile, delimiter='\t')
    header = tsvreader.next() # skip header line
    ct = 1
    notfnd = set()
    pmark = {}
    gwas_ct = 0
    dba_err_ct = 0
    # 0: DATE ADDED TO CATALOG
    # 1: PUBMEDID
    # 2: FIRST AUTHOR
    # 3: DATE
    # 4: JOURNAL
    # 5: LINK
    # 6: STUDY
    # 7: DISEASE/TRAIT
    # 8: INITIAL SAMPLE SIZE
    # 9: REPLICATION SAMPLE SIZE
    # 10: REGION
    # 11: CHR_ID
    # 12: CHR_POS
    # 13: REPORTED GENE(S)
    # 14: MAPPED_GENE
    # 15: UPSTREAM_GENE_ID
    # 16: DOWNSTREAM_GENE_ID
    # 17: SNP_GENE_IDS
    # 18: UPSTREAM_GENE_DISTANCE
    # 19: DOWNSTREAM_GENE_DISTANCE
    # 20: STRONGEST SNP-RISK ALLELE
    # 21: SNPS
    # 22: MERGED
    # 23: SNP_ID_CURRENT
    # 24: CONTEXT
    # 25: INTERGENIC
    # 26: RISK ALLELE FREQUENCY
    # 27: P-VALUE
    # 28: PVALUE_MLOG
    # 29: P-VALUE (TEXT)
    # 30: OR or BETA
    # 31: 95% CI (TEXT)
    # 32: PLATFORM [SNPS PASSING QC]
    # 33: CNV
    # 34: MAPPED_TRAIT
    # 35: MAPPED_TRAIT_URI
    # 36: STUDY ACCESSION
    # 37: GENOTYPING TECHNOLOGY
    symregex = re.compile(r' ?[-,;] ?')
    for row in tsvreader:
      ct += 1
      if len(row) < 14: continue
      symstr = row[14]
      if symstr == 'NR': continue
      symlist = symregex.split(symstr)
      for sym in symlist:
        if sym in notfnd:
          continue
        targets = dba.find_targets({'sym': sym})
        if not targets:
          notfnd.add(sym)
          logger.warn("No target found for symbol {}".format(sym))
          continue
        for t in targets:
          p = t['components']['protein'][0]
          try:
            pval = float(row[27])
          except:
            pval = None
          try:
            orbeta = float(row[30])
          except:
            orbeta = None
          if row[25]:
            ig = int(row[25])
          else:
            ig = None
          rv = dba.ins_gwas({'protein_id': p['id'], 'disease_trait': row[7], 'snps': row[21],
                             'pmid': row[1], 'study': row[6], 'context': row[24], 'intergenic': ig,
                             'p_value': pval, 'or_beta': orbeta, 'cnv': row[33],
                             'mapped_trait': row[34], 'mapped_trait_uri': row[35]})
          if not rv:
            dba_err_ct += 1
            continue
          pmark[p['id']] = True
          gwas_ct += 1
      pbar.update(ct)
  pbar.finish()
  print "{} lines processed.".format(ct)
  print "Inserted {} new gwas rows for {} proteins".format(gwas_ct, len(pmark))
  if notfnd:
    print "  No target found for {} symbols. See logfile {} for details.".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)
  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'GWAS Catalog', 'source': 'File %s from http://www.ebi.ac.uk/gwas/docs/file-downloads'%os.path.basename(CONFIG['GWAS Catalog']['FILENAME']), 'app': PROGRAM, 'app_version': __version__, 'url': 'https://www.ebi.ac.uk/gwas/home'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'gwas'})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

def load_IMPC(args, dba, logger, logfile):
  fn = CONFIG['IMPC']['DOWNLOAD_DIR'] + CONFIG['IMPC']['GENO_PHENO_FILE']
  line_ct = slmf.wcl(fn)
  if not args['--quiet']:
    print "Processing {} lines from input file {}".format(line_ct, fn)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  with open(fn, 'rU') as csvfile:
    csvreader = csv.reader(csvfile)
    header = csvreader.next() # skip header line
    ct = 1
    pt_ct = 0
    pmark = {}
    sym2nhps = {}
    notfnd = set()
    skip_ct = 0
    dba_err_ct = 0
    # 0: marker_accession_id
    # 1: marker_symbol
    # 2: phenotyping_center
    # 3: colony_id
    # 4: sex
    # 5: zygosity
    # 6: allele_accession_id
    # 7: allele_symbol
    # 8: allele_name
    # 9: strain_accession_id
    # 10: strain_name
    # 11: project_name
    # 12: project_fullname
    # 13: pipeline_name
    # 14: pipeline_stable_id
    # 15: procedure_stable_id
    # 16: procedure_name
    # 17: parameter_stable_id
    # 18: parameter_name
    # 19: top_level_mp_term_id
    # 20: top_level_mp_term_name
    # 21: mp_term_id
    # 22: mp_term_name
    # 23: p_value
    # 24: percentage_change
    # 25: effect_size
    # 26: statistical_method
    # 27: resource_name
    for row in csvreader:
      ct += 1
      sym = row[1]
      if not row[21] and not row[22]:
        # skip data with neither a term_id or term_name (IMPC has some of these)
        skip_ct += 1
        continue
      if sym in sym2nhps:
        # we've already found it
        nhpids = sym2nhps[sym]
      elif sym in notfnd:
        # we've already not found it
        continue
      else:
        nhps = dba.find_nhproteins({'sym': sym}, species = 'Mus musculus')
        if not nhps:
          notfnd.add(sym)
          logger.warn("No nhprotein found for symbol {}".format(sym))
          continue
        nhpids = []
        for nhp in nhps:
          nhpids.append(nhp['id'])
        sym2nhps[sym] = nhpids # save this mapping so we only lookup each nhprotein once
      pval = None
      if row[23] and row[23] != '':
        try:
          pval = float(row[23])
        except:
          logger.warn("Problem converting p_value {} for row {}".format(row[23], ct))
      for nhpid in nhpids:
        rv = dba.ins_phenotype({'nhprotein_id': nhpid, 'ptype': 'IMPC', 'top_level_term_id': row[19], 'top_level_term_name': row[20], 'term_id': row[21], 'term_name': row[22], 'p_value': pval, 'percentage_change': row[24], 'effect_size': row[25], 'procedure_name': row[16], 'parameter_name': row[18], 'statistical_method': row[26], 'sex': row[4], 'gp_assoc': 1})
        if rv:
          pmark[nhpid] = True
          pt_ct += 1
        else:
          dba_err_ct += 1
      pbar.update(ct)
  pbar.finish()
  print "{} lines processed.".format(ct)
  print "Loaded {} IMPC phenotypes for {} nhproteins".format(pt_ct, len(pmark.keys()))
  if notfnd:
    print "No nhprotein found for {} gene symbols. See logfile {} for details.".format(len(notfnd), logfile)
  if skip_ct > 0:
    print "Skipped {} lines with no term_id or term_name.".format(skip_ct)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

  fn = CONFIG['IMPC']['DOWNLOAD_DIR'] + CONFIG['IMPC']['STAT_RES_FILE']
  line_ct = slmf.wcl(fn)
  if not args['--quiet']:
    print "Processing {} lines from input file {}".format(line_ct, fn)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  with open(fn, 'rU') as csvfile:
    csvreader = csv.reader(csvfile)
    header = csvreader.next() # skip header line
    ct = 1
    pt_ct = 0
    pmark = {}
    sym2nhps = {}
    notfnd = set()
    skip_ct = 0
    pv_ct = 0
    dba_err_ct = 0
    # 0: phenotyping_center
    # 1: intercept_estimate
    # 2: procedure_id
    # 3: mutant_biological_model_id
    # 4: rotated_residuals_test
    # 5: weight_effect_p_value
    # 6: male_mutant_count
    # 7: pipeline_stable_key
    # 8: female_ko_effect_p_value
    # 9: pipeline_stable_id
    # 10: parameter_stable_key
    # 11: data_type
    # 12: parameter_stable_id
    # 13: interaction_significant
    # 14: strain_accession_id
    # 15: control_selection_method
    # 16: parameter_name
    # 17: allele_name
    # 18: phenotyping_center_id
    # 19: weight_effect_stderr_estimate
    # 20: weight_effect_parameter_estimate
    # 21: procedure_stable_id
    # 22: status
    # 23: sex_effect_parameter_estimate
    # 24: female_ko_effect_stderr_estimate
    # 25: female_percentage_change
    # 26: group_2_residuals_normality_test
    # 27: marker_accession_id
    # 28: mp_term_name
    # 29: group_1_residuals_normality_test
    # 30: genotype_effect_p_value
    # 31: dependent_variable
    # 32: resource_name
    # 33: project_id
    # 34: procedure_name
    # 35: doc_id
    # 36: top_level_mp_term_id
    # 37: allele_accession_id
    # 38: blups_test
    # 39: null_test_p_value
    # 40: p_value
    # 41: marker_symbol
    # 42: control_biological_model_id
    # 43: pipeline_name
    # 44: sex
    # 45: interaction_effect_p_value
    # 46: colony_id
    # 47: project_name
    # 48: female_ko_parameter_estimate
    # 49: female_mutant_count
    # 50: organisation_id
    # 51: external_db_id
    # 52: female_control_count
    # 53: intermediate_mp_term_id
    # 54: db_id
    # 55: male_ko_effect_p_value
    # 56: top_level_mp_term_name
    # 57: metadata_group
    # 58: sex_effect_stderr_estimate
    # 59: zygosity
    # 60: male_percentage_change
    # 61: sex_effect_p_value
    # 62: mp_term_id
    # 63: male_ko_effect_stderr_estimate
    # 64: additional_information
    # 65: statistical_method
    # 66: _version_
    # 67: intercept_estimate_stderr_estimate
    # 68: male_control_count
    # 69: intermediate_mp_term_name
    # 70: strain_name
    # 71: classification_tag
    # 72: effect_size
    # 73: procedure_stable_key
    # 74: allele_symbol
    # 75: resource_id
    # 76: group_2_genotype
    # 77: variance_significant
    # 78: pipeline_id
    # 79: group_1_genotype
    # 80: male_ko_parameter_estimate
    # 81: genotype_effect_parameter_estimate
    # 82: categories
    # 83: parameter_id
    # 84: batch_significant
    # 85: genotype_effect_stderr_estimate
    # 86: resource_fullname
    for row in csvreader:
      ct += 1
      sym = row[41]
      if not row[62] and not row[28]:
        # skip lines with neither a term_id or term_name
        skip_ct += 1
        continue
      if sym in sym2nhps:
        # we've already found it
        nhpids = sym2nhps[sym]
      elif sym in notfnd:
        # we've already not found it
        continue
      else:
        nhps = dba.find_nhproteins({'sym': sym}, species = 'Mus musculus')
        if not nhps:
          notfnd.add(sym)
          logger.warn("No nhprotein found for symbol {}".format(sym))
          continue
        nhpids = []
        for nhp in nhps:
          nhpids.append(nhp['id'])
        sym2nhps[sym] = nhpids # save this mapping so we only lookup each nhprotein once
      pval = None
      if row[40] and row[40] != '':
        try:
          pval = float(row[40])
        except:
          logger.warn("Problem converting p_value {} for row {}".format(row[40], ct))
      for nhpid in nhpids:
        rv = dba.ins_phenotype({'nhprotein_id': nhpid, 'ptype': 'IMPC', 'top_level_term_id': row[36], 'top_level_term_name': row[56], 'term_id': row[62], 'term_name': row[28], 'p_value': pval, 'effect_size': row[72], 'procedure_name': row[34], 'parameter_name': row[16], 'statistical_method': row[65], 'sex': row[44], 'gp_assoc': 0})
        if rv:
          pmark[nhpid] = True
          pt_ct += 1
        else:
          dba_err_ct += 1
      pbar.update(ct)
  pbar.finish()
  print "{} lines processed.".format(ct)
  print "Loaded {} IMPC phenotypes for {} nhproteins".format(pt_ct, len(pmark))
  if notfnd:
    print "  No nhprotein found for {} gene symbols. See logfile {} for details.".format(len(notfnd), logfile)
  if skip_ct > 0:
    print "  Skipped {} lines with no term_id/term_name or no p-value.".format(skip_ct)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)
  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'IMPC Phenotypes', 'source': "Files %s and %s from ftp://ftp.ebi.ac.uk/pub/databases/impc/release-11.0/csv/"%(CONFIG['IMPC']['GENO_PHENO_FILE'], CONFIG['IMPC']['STAT_RES_FILE']), 'app': PROGRAM, 'app_version': __version__} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'phenotype', 'where_clause': "ptype = 'IMPC'"} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

def download_JAX(args):
  fn = CONFIG['JAX']['DOWNLOAD_DIR'] + CONFIG['JAX']['FILENAME']
  if os.path.exists(fn):
    os.remove(fn)
  if not args['--quiet']:
    print "Downloading ", CONFIG['JAX']['BASE_URL'] + CONFIG['JAX']['FILENAME']
    print "         to ", fn
  urllib.urlretrieve(CONFIG['JAX']['BASE_URL'] + CONFIG['JAX']['FILENAME'], fn)
  if not args['--quiet']:
    print "Done."

def parse_mp_owl(f):
  mpo = {}
  mpont = pronto.Ontology(f)
  for term in mpont:
    if not term.id.startswith('MP:'):
      continue
    mpid = term.id
    name = term.name
    init = {'name': name}
    if term.parents:
      init['parent_id'] = term.parents[0].id
    if term.desc:
      init['def'] = term.desc
    mpo[mpid] = init
  return mpo

def load_JAX(args, dba, logger, logfile):
  fn = CONFIG['MPO_OWL_FILE']
  if not args['--quiet']:
    print "Parsing Mammalian Phenotype Ontology file {}".format(fn)
  mpo = parse_mp_owl(fn)
  if not args['--quiet']:
    print "Got {} MP terms".format(len(mpo))

  fn = CONFIG['JAX']['DOWNLOAD_DIR'] + CONFIG['JAX']['FILENAME']
  line_ct = slmf.wcl(fn)
  if not args['--quiet']:
    print "Processing {} lines from JAX file {}".format(line_ct, fn)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start()
  with open(fn, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    pt_ct = 0
    skip_ct = 0
    pmark = {}
    notfnd = set()
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
      if not row[6] or row[6] == '':
        skip_ct += 1
        continue
      sym = row[0]
      geneid = row[1]
      k = "%s|%s"%(sym,geneid)
      if k in notfnd:
        continue
      targets = dba.find_targets({'sym': sym}, idg = False)
      if not targets:
        targets = dba.find_targets({'geneid': geneid}, idg = False)
      if not targets:
        notfnd.add(k)
        logger.warn("No target found for {}".format(k))
        continue
      for t in targets:
        pid = t['components']['protein'][0]['id']
        pmark[pid] = True
        for mpid in row[6].split():
          rv = dba.ins_phenotype({'protein_id': pid, 'ptype': 'JAX/MGI Human Ortholog Phenotype', 'term_id': mpid, 'term_name': mpo[mpid]['name']})
          if rv:
            pt_ct += 1
          else:
            dba_err_ct += 1
      pbar.update(ct)
  pbar.finish()
  print "{} lines processed.".format(ct)
  print "Loaded {} new phenotype rows for {} proteins".format(pt_ct, len(pmark))
  print "  Skipped {} lines with no MP terms".format(skip_ct)
  if notfnd:
    print "  No target found for {} gene symbols/ids. See logfile {} for details.".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)
  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'JAX/MGI Mouse/Human Orthology Phenotypes', 'source': 'File %s from ftp.informatics.jax.org'%CONFIG['JAX']['FILENAME'], 'app': PROGRAM, 'app_version': __version__, 'url': 'http://www.informatics.jax.org/'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'phenotype', 'where_clause': "ptype = 'JAX/MGI Human Ortholog Phenotype'"} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

def load_RGD(args, dba, logger, logfile):
  fn = CONFIG['RGD']['DOWNLOAD_DIR'] + CONFIG['RGD']['QTL_FILE']
  line_ct = slmf.wcl(fn)
  if not args['--quiet']:
    print "Processing {} lines in processed RGD file {}".format(line_ct, fn)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  ct = 0
  dba_err_ct = 0
  nhpmark = {}
  qtl_ct = 0
  with open(fn, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    header = tsvreader.next() # skip header line
    ct += 1
    for row in tsvreader:
      ct += 1
      # 0 "GENE_RGD_ID"
      # 1 "nhprotein_id"
      # 2 "QTL_RGD_ID"
      # 3 "QTL_SYMBOL"
      # 4 "QTL_NAME"
      # 5 "LOD"
      # 6 "P_VALUE"
      # 7 "TRAIT_NAME"
      # 8 "MEASUREMENT_TYPE"
      # 9 "ASSOCIATED_DISEASES"
      # 10 "PHENOTYPES"
      init = {'nhprotein_id': row[1], 'rgdid': row[0], 'qtl_rgdid': row[2], 
              'qtl_symbol': row[3], 'qtl_name': row[4]}
      if row[5] and row[5] != 'None':
        init['lod'] = row[5]
      if row[6] and row[6] != 'None':
        init['p_value'] = row[6]
      if row[7] and row[7] != 'None':
        init['trait_name'] = row[7]
      if row[8] and row[8] != 'None':
        init['measurement_type'] = row[8]
      if row[9] and row[9] != 'None':
        init['associated_disease'] = row[9]
      if row[10] and row[10] != 'None':
        init['phenotype'] = row[10]
      rv = dba.ins_rat_qtl(init)
      if not rv:
        dba_err_ct += 1
        continue
      qtl_ct += 1
      nhpmark[row[1]] = True
      pbar.update(ct)
  pbar.finish()
  print "Processed {} lines".format(ct)
  print "Inserted {} new rat_qtl rows for {} nhproteins.".format(qtl_ct, len(nhpmark))
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

  fn = CONFIG['RGD']['DOWNLOAD_DIR'] + CONFIG['RGD']['TERMS_FILE']
  line_ct = slmf.wcl(fn)
  if not args['--quiet']:
    print "Processing {} lines in processed RGD file {}".format(line_ct, fn)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  ct = 0
  dba_err_ct = 0
  term_ct = 0
  with open(fn, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    header = tsvreader.next() # skip header line
    ct += 1
    for row in tsvreader:
      ct += 1
      # 0 "RGD_ID"
      # 1 "OBJECT_SYMBOL"
      # 2 "TERM_ACC_ID"
      # 3 "TERM_NAME"
      # 4 "QUALIFIER"
      # 5 "EVIDENCE"
      # 6 "ONTOLOGY"
      init = {'rgdid': row[0], 'term_id': row[2], 'qtl_symbol': row[3], 'qtl_name': row[4]}
      if row[1] and row[1] != 'None':
        init['obj_symbol'] = row[1]
      if row[3] and row[3] != 'None':
        init['term_name'] = row[3]
      if row[4] and row[4] != 'None':
        init['qualifier'] = row[4]
      if row[5] and row[5] != 'None':
        init['evidence'] = row[5]
      if row[6] and row[6] != 'None':
        init['ontology'] = row[6]
      rv = dba.ins_rat_term(init)
      if not rv:
        dba_err_ct += 1
        continue
      term_ct += 1
      pbar.update(ct)
  pbar.finish()
  print "Processed {} lines".format(ct)
  print "Inserted {} new rat_term rows.".format(term_ct)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)
  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'RGD', 'source': 'Files %s and %s produced by UNM KMC group from files from ftp://ftp.rgd.mcw.edu/pub/data_release/'.format(CONFIG['RGD']['QTL_FILE'], CONFIG['RGD']['TERMS_FILE']), 'app': PROGRAM, 'app_version': __version__} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  provs = [{'dataset_id': dataset_id, 'table_name': 'rat_term'}, {'dataset_id': dataset_id, 'table_name': 'rat_qtl'}]
  for prov in provs:
    rv = dba.ins_provenance(prov)
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

  print "\nWorking on OMIM..."
  download_OMIM()
  start_time = time.time()
  load_OMIM(args, dba, logger, logfile)
  elapsed = time.time() - start_time
  print "Done with OMIM. Elapsed time: {}".format(slmf.secs2str(elapsed))

  print "\nWorking on GWAS Catalog..."
  start_time = time.time()
  load_GWASCatalog(args, dba, logger, logfile)
  elapsed = time.time() - start_time
  print "Done with GWAS Catalog. Elapsed time: {}".format(slmf.secs2str(elapsed))
  
  print "\nWorking on IMPC..."
  start_time = time.time()
  load_IMPC(args, dba, logger, logfile)
  elapsed = time.time() - start_time
  print "Done with IMPC. Elapsed time: {}".format(slmf.secs2str(elapsed))
  
  print "\nWorking on JAX..."
  download_JAX(args)
  start_time = time.time()
  load_JAX(args, dba, logger, logfile)
  elapsed = time.time() - start_time
  print "Done with JAX. Elapsed time: {}".format(slmf.secs2str(elapsed))
  
  print "\nWorking on RGD..."
  start_time = time.time()
  load_RGD(args, dba, logger, logfile)
  elapsed = time.time() - start_time
  print "Done with RGD. Elapsed time: {}".format(slmf.secs2str(elapsed))
    
  print "\n{}: Done.\n".format(PROGRAM)







