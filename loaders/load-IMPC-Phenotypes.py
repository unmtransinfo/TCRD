#!/usr/bin/env python
# Time-stamp: <2019-02-04 11:20:04 smathias>
"""Load IMPC phenotype data into TCRD from CSV file.

Usage:
    load-IMPC-Phenotypes.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-IMPC-Phenotypes.py -? | --help

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
__copyright__ = "Copyright 2015-2019, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.4.0"

import os,sys,time
from docopt import docopt
from TCRDMP import DBAdaptor
import logging
import csv
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd6logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
# Get from ftp://ftp.ebi.ac.uk/pub/databases/impc/release-*.*/csv/
# ftp://ftp.ebi.ac.uk/pub/databases/impc/release-9.2/csv/IMPC_genotype_phenotype.csv.gz
GENO_PHENO_FILE = '../data/IMPC/IMPC_genotype_phenotype.csv'
# ftp://ftp.ebi.ac.uk/pub/databases/impc/release-9.2/csv/IMPC_ALL_statistical_results.csv.gz
STAT_RES_FILE = '../data/IMPC/IMPC_ALL_statistical_results.csv'

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
  dataset_id = dba.ins_dataset( {'name': 'IMPC Phenotypes', 'source': "Files %s and %s from ftp://ftp.ebi.ac.uk/pub/databases/impc/release-9.2/csv/"%(GENO_PHENO_FILE, STAT_RES_FILE), 'app': PROGRAM, 'app_version': __version__} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'phenotype', 'where_clause': "ptype = 'IMPC'"} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)
  
  line_ct = slmf.wcl(GENO_PHENO_FILE)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  if not args['--quiet']:
    print "\nProcessing {} lines from input file {}".format(line_ct, GENO_PHENO_FILE)
  with open(GENO_PHENO_FILE, 'rU') as csvfile:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    csvreader = csv.reader(csvfile)
    header = csvreader.next() # skip header line
    ct = 0
    pt_ct = 0
    pmark = {}
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
      if sym in notfnd:
        continue
      if not row[21] and not row[22]:
        # skip data with neither a term_id or term_name (IMPC has some of these)
        skip_ct += 1
        continue
      nhps = dba.find_nhproteins({'sym': sym}, species = 'Mus musculus')
      if not nhps:
        notfnd.add(sym)
        logger.warn("No nhprotein found for symbol {}".format(sym))
        continue
      pval = None
      if row[23] and row[23] != '':
        try:
          pval = float(row[23])
        except:
          logger.warn("Problem converting p_value {} for row {}".format(row[23], ct))
      for nhp in nhps:
        rv = dba.ins_phenotype({'nhprotein_id': nhp['id'], 'ptype': 'IMPC', 'top_level_term_id': row[19], 'top_level_term_name': row[20], 'term_id': row[21], 'term_name': row[22], 'p_value': pval, 'percentage_change': row[24], 'effect_size': row[25], 'procedure_name': row[16], 'parameter_name': row[18], 'statistical_method': row[26], 'sex': row[4], 'gp_assoc': 1})
        if rv:
          pmark[nhp['id']] = True
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

  line_ct = slmf.wcl(STAT_RES_FILE)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  if not args['--quiet']:
    print "\nProcessing {} lines from input file {}".format(line_ct, STAT_RES_FILE)
  with open(STAT_RES_FILE, 'rU') as csvfile:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    csvreader = csv.reader(csvfile)
    header = csvreader.next() # skip header line
    ct = 0
    pt_ct = 0
    pmark = {}
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
      if sym in notfnd:
        continue
      if not row[62] and not row[28]:
        # skip lines with neither a term_id or term_name
        skip_ct += 1
        continue
      if not row[40]:
        # skip lines with no p-value
        skip_ct += 1
        continue
      pval = None
      if row[40] and row[40] != '':
        try:
          pval = float(row[40])
        except:
          logger.warn("Problem converting p_value {} for row {}".format(row[40], ct))
      if not pval:
        skip_ct += 1
        continue
      if pval > 0.05:
        pv_ct += 1
        continue
      nhps = dba.find_nhproteins({'sym': sym}, species = 'Mus musculus')
      if not nhps:
        notfnd.add(sym)
        logger.warn("No nhprotein found for symbol {}".format(sym))
        continue
      for nhp in nhps:
        rv = dba.ins_phenotype({'nhprotein_id': nhp['id'], 'ptype': 'IMPC', 'top_level_term_id': row[36], 'top_level_term_name': row[56], 'term_id': row[62], 'term_name': row[28], 'p_value': pval, 'effect_size': row[72], 'procedure_name': row[34], 'parameter_name': row[16], 'statistical_method': row[65], 'sex': row[44], 'gp_assoc': 0})
        if rv:
          pmark[nhp['id']] = True
          pt_ct += 1
        else:
          dba_err_ct += 1
      pbar.update(ct)
  pbar.finish()
  print "{} lines processed.".format(ct)
  print "Loaded {} IMPC phenotypes for {} nhproteins".format(pt_ct, len(pmark))
  if notfnd:
    print "No nhprotein found for {} gene symbols. See logfile {} for details.".format(len(notfnd), logfile)
  if skip_ct > 0:
    print "Skipped {} lines with no term_id/term_name or no p-value.".format(skip_ct)
  if pv_ct > 0:
    print "Skipped {} lines with p-value > 0.05.".format(pv_ct)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)


if __name__ == '__main__':
  print "\n{} (v{}) [{}]:".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  start_time = time.time()
  load(args)
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))
  
