#!/usr/bin/env python
# Time-stamp: <2017-01-05 16:35:23 smathias>
"""Load chembl_activity data in TCRD via ChEMBL MySQL database.

Usage:
    load-ChEMBL.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-ChEMBL.py -h | --help

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
__version__   = "2.0.0"

import os,sys,time,re
from docopt import docopt
from TCRD import DBAdaptor
import MySQLdb as mysql
from contextlib import closing
import csv
import copy
import cPickle as pickle
import logging
import string
import urllib
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
LOGFILE = './%s.log'%PROGRAM
CHEMBL_DB = 'chembl_22'
DOWNLOAD_DIR = '../data/ChEMBL/'
BASE_URL = 'ftp://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/'
UNIPROT2CHEMBL_FILE = 'chembl_uniprot_mapping.txt'

def download_mappings():
  if os.path.exists(DOWNLOAD_DIR + UNIPROT2CHEMBL_FILE):
    os.remove(DOWNLOAD_DIR + UNIPROT2CHEMBL_FILE)
  start_time = time.time()
  print "\nDownloading ", BASE_URL + UNIPROT2CHEMBL_FILE
  print "         to ", DOWNLOAD_DIR + UNIPROT2CHEMBL_FILE
  urllib.urlretrieve(BASE_URL + UNIPROT2CHEMBL_FILE, DOWNLOAD_DIR + UNIPROT2CHEMBL_FILE)
  elapsed = time.time() - start_time
  print "Done. Elapsed time: %s" % secs2str(elapsed)

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
    print "\nConnected to TCRD database %s (schema ver %s; data ver %s)" % (args['--dbname'], dbi['schema_ver'], dbi['data_ver'])

  start_time = time.time()
  
  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'ChEMBL', 'source': 'ChEMBL MySQL database {}'.format(CHEMBL_DB), 'app': PROGRAM, 'app_version': __version__, 'url': 'https://www.ebi.ac.uk/chembl/'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'chembl_acivity'},
            {'dataset_id': 1, 'table_name': 'tdl_info', 'where_clause': "itype = 'ChEMBL First Reference Year'", 'comment': "Derived from filtered ChEMBL activities."},
            {'dataset_id': 1, 'table_name': 'tdl_info', 'where_clause': "itype = 'ChEMBL Selective Compound'", 'comment': "Derived from filtered ChEMBL activities."} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    if not rv:
      print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
      sys.exit(1)

  # ChEMBL MySQL connection
  f = open('/home/smathias/.dbirc', 'r')
  pw = f.readline().strip()
  chembldb =  mysql.connect(host='localhost', port=3306, db=CHEMBL_DB, user='smathias', passwd=pw)

  # First get mapping of UniProt accestions to ChEMBL IDs
  up2chembl = {}
  f = DOWNLOAD_DIR + UNIPROT2CHEMBL_FILE
  line_ct = wcl(f)
  if not args['--quiet']:
    print "\nProcessing %d input lines in file %s" % (line_ct, f)
  with open(f, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    for row in tsvreader:
      ct += 1
      if row[0].startswith('#'): continue
      if row[0] in up2chembl:
        up2chembl[row[0]].append(row[1])
      else:
        up2chembl[row[0]] = [row[1]]
  print "%d input lines processed." % ct
  #print "Saved %d keys in up2chembl dict" % len(up2chembl.keys())

  upct = len(up2chembl.keys())
  if not args['--quiet']:
    print "\nProcessing %d UniProt to ChEMBL ID(s) mappings" % upct
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=upct).start() 
  ct = 0
  notfnd = []
  fnd_ct = 0
  err_ct = 0
  dba_err_ct = 0
  nic_ct = 0
  nga_ct = 0
  tdl_ct = 0
  ca_ct = 0
  csti_ct = 0
  ccti_ct = 0
  cyti_ct = 0
  t2acts = {}
  c2acts = {}
  for up in up2chembl.keys():
    ct += 1
    pbar.update(ct)
    targets = dba.find_targets({'uniprot': up}, include_annotations=True)
    if not targets:
      notfnd.append(up)
      continue
    t = targets[0]
    tid = t['id']
    logger.info("Loading ChEMBL data for target %d - %s/%s"%(t['id'], t['components']['protein'][0]['sym'], up))
    chembl_acts = []
    for ctid in up2chembl[up]:
      with closing(chembldb.cursor(mysql.cursors.DictCursor)) as curs:
        curs.execute("SELECT acts.molregno, md.pref_name, md.chembl_id, cs.canonical_smiles, acts.pchembl_value, acts.standard_type, cr.compound_name, d.journal, d.year, d.volume, d.issue, d.first_page, d.pubmed_id FROM activities acts, compound_records cr, assays a, target_dictionary t, compound_structures cs, molecule_dictionary md, docs d WHERE acts.record_id = cr.record_id AND cs.molregno = md.molregno AND cs.molregno = acts.molregno AND acts.assay_id = a.assay_id AND a.tid = t.tid AND t.chembl_id = %s AND acts.molregno = md.molregno AND a.assay_type = 'B' AND md.structure_type = 'MOL' AND acts.standard_flag = 1 AND acts.standard_relation = '=' AND t.target_type = 'SINGLE PROTEIN' AND acts.pchembl_value IS NOT NULL AND acts.doc_id = d.doc_id", (ctid,))
        for d in curs:
          if d['year']:
            d['reference'] = "%s, (%d) %s:%s:%s" % (d['journal'], d['year'], d['volume'], d['issue'], d['first_page'] )
          else:
            d['reference'] = "%s, %s:%s:%s" % (d['journal'], d['volume'], d['issue'], d['first_page'] )
          for k in ['journal', 'volume', 'issue', 'first_page']:
            del(d[k])
          chembl_acts.append(d)
    if t['idgfam'] == 'GPCR':
      cutoff =  7.0 # 100nM
    elif t['idgfam'] == 'IC':
      cutoff = 5.0 # 10uM
    elif t['idgfam'] == 'Kinase':
      cutoff = 7.52288 # 30nM
    elif t['idgfam'] == 'NR':
      cutoff =  7.0 # 100nM
    else:
      cutoff = 6.0 # 1uM for non-IDG Family targets
    logger.info("Target %d (%s) filter cutoff: %f " % (tid, t['name'], len(chembl_acts)))
    filtered_acts = [a for a in chembl_acts if a['pchembl_value'] >= cutoff]
    logger.info("%d ChEMBL acts => %d filtered acts" % (len(chembl_acts), len(filtered_acts)))
    #print 
    if not filtered_acts:
     nga_ct += 1
     continue
    logger.info("  Got %d filtered activities"%len(filtered_acts))
    #
    # if we get here, target is Tchem
    #
    # sort all activities by std_val, so best activity is in sorted_by_stdval[-1]
    decorated = [(a['pchembl_value'], a) for a in filtered_acts]
    decorated.sort()
    sorted_by_stdval = [a for (key, a) in decorated]
    # sort filtered activities by reference year, so oldest activity is in sorted_by_year[0]
    decorated = [(a['year'], a) for a in filtered_acts if 'year' in a]
    decorated.sort()
    sorted_by_year = [a for (key, a) in decorated]
    
    # Save chembl_activities
    # The best activity for a given target will be the one with MAX(chembl_activity.id)
    for a in sorted_by_stdval:
      try:
        rv = dba.ins_chembl_activity( {'target_id': tid, 'cmpd_chemblid': a['chembl_id'], 'cmpd_name_in_ref': a['compound_name'], 'smiles': a['canonical_smiles'], 'reference': a['reference'], 'act_value': a['pchembl_value'], 'act_type': a['standard_type'], 'pubmed_id': a['pubmed_id']} )
      except:
        # some names have weird hex characters and cause errors...
        rv = dba.ins_chembl_activity( {'target_id': tid, 'cmpd_chemblid': a['chembl_id'], 'cmpd_name_in_ref': '?', 'smiles': a['canonical_smiles'], 'reference': a['reference'], 'act_value': a['pchembl_value'], 'act_type': a['standard_type'], 'pubmed_id': a['pubmed_id']} )
      if rv:
        ca_ct += 1
      else:
        dba_err_ct += 1
    
    # Save First ChEMBL Reference Year tdl_info, if there is one
    if len(sorted_by_year) > 0:
      oldest = sorted_by_year[0]
      rv = dba.ins_tdl_info( {'target_id': tid, 'itype': 'ChEMBL First Reference Year', 'integer_value': sorted_by_year[0]['year']} )
      if rv:
        cyti_ct += 1
      else:
        dba_err_ct += 1

    # Save mappings for selective compound calculations
    t2acts[tid] = copy.copy(sorted_by_stdval)
    for a in chembl_acts:
      ac = copy.copy(a)
      smi = ac['canonical_smiles']
      del(ac['canonical_smiles'])
      ac['tid'] = tid
      ac['tname'] = t['components']['protein'][0]['name']
      if smi in c2acts:
        c2acts[smi].append(ac)
      else:
        c2acts[smi] = [ac]
  pbar.finish()
  print "%d UniProt accessions processed." % ct
  print "  %d targets not found in ChEMBL" % nic_ct
  print "  %d targets have no good activities in ChEMBL" % nga_ct
  print "Inserted %d new chembl_activity rows" % ca_ct
  print "Inserted %d new ChEMBL First Reference Year tdl_infos" % cyti_ct
  if err_ct > 0:
    print "%d ERRORS" % err_ct
  if dba_err_ct > 0:
    print "WARNING: %d database errors occured. See logfile %s for details." % (dba_err_ct, logfile)
  
  # Selective compound calculations
  print "\nRunning selective compound analysis..."
  #pickle.dump(t2acts, open('T2ChEMBLActs.p', 'wb'))
  #print "%d target to activities mappings saved to pickle T2ChEMBLActs.p" % len(t2acts.keys())
  #pickle.dump(c2acts, open('C2AllChEMBLActs.p', 'wb'))
  #print "%d compound to activity mappings saved to pickle C2AllChEMBLActs.p" % len(c2acts.keys())
  # filter c2acts for compounds with multiple activities
  c2macts = {}
  for c,acts in c2acts.items():
    if len(acts) > 1:
      c2macts[c] = list(acts)
  # then sort the activity lists by pchembl_value
  c2smacts = {}
  for c,acts in c2macts.items():
    decorated = [(a['pchembl_value'], a) for a in acts]
    decorated.sort()
    c2smacts[c] = [a for (key, a) in decorated]
  #pickle.dump(c2smacts, open('C2ChEMBLActs.p', 'wb'))
  #print "%d compound to activities mappings saved to pickle C2ChEMBLActs.p" % len(c2smacts.keys())
  selective = []
  for smi in c2smacts.keys():
    i = 1
    while i <= len(c2smacts[smi])-1:
      if c2smacts[smi][i]['tid'] == c2smacts[smi][i-1]['tid']:
        i += 1
        continue
      diff = c2smacts[smi][i]['pchembl_value'] - c2smacts[smi][i-1]['pchembl_value']
      if diff >= 2:
        selective.append(smi)
        break
      i += 1
  #pickle.dump(selective, open(SC_PFILE, 'wb'))
  #print "%d selective compounds saved to %s" % (len(selective), SC_PFILE)
  print "  Found %d selective compounds" % len(selective)
  cscti_ct = 0
  for tid,acts in t2acts.items():
    for a in acts:
      if a['canonical_smiles'] in selective:
        # Save ChEMBL Selective Compound tdl_info
        val = "%s|%s" % (a['chembl_id'], a['canonical_smiles'])
        rv = dba.ins_tdl_info( {'target_id': tid, 'itype': 'ChEMBL Selective Compound', 'string_value': val} )
        if rv:
          cscti_ct += 1
        else:
          dba_err_ct += 1
        break
  print "Inserted %d new ChEMBL Selective Compound tdl_infos" % cscti_ct
  
  elapsed = time.time() - start_time
  print "\n%s: Done. Elapsed time: %s" % (PROGRAM, secs2str(elapsed))
  print

def wcl(fname):
  with open(fname) as f:
    for i, l in enumerate(f):
      pass
  return i + 1

def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])


if __name__ == '__main__':
  print "\n%s (v%s) [%s]:" % (PROGRAM, __version__, time.strftime("%c"))
  download_mappings()
  main()

