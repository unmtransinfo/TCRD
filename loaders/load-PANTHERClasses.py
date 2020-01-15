#!/usr/bin/env python
# Time-stamp: <2019-08-28 10:47:24 smathias>
"""Load PANTHER family classes into TCRD from TSV files.

Usage:
    load-PANTHERClasses.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>] [--pastid=<int>]
    load-PANTHERClasses.py -h | --help

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
  -p --pastid PASTID   : TCRD target id to start at (for restarting frozen run)
  -q --quiet           : set output verbosity to minimal level
  -d --debug           : turn on debugging output
  -? --help            : print this message and exit 
"""
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2015-2019, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "3.0.0"

import os,sys,time,re
from docopt import docopt
from TCRDMP import DBAdaptor
import csv
import logging
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd6logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
# ftp://ftp.pantherdb.org//sequence_classifications/current_release/PANTHER_Sequence_Classification_files/PTHR13.1_human
# ftp://ftp.pantherdb.org/sequence_classifications/current_release/PANTHER_Sequence_Classification_files/PTHR14.1_human_
P2PC_FILE = '../data/PANTHER/PTHR14.1_human_'
# http://data.pantherdb.org/PANTHER14.1/ontology/Protein_Class_14.0
CLASS_FILE = '../data/PANTHER/Protein_Class_14.0'
# http://data.pantherdb.org/PANTHER14.1/ontology/Protein_class_relationship
RELN_FILE = '../data/PANTHER/Protein_class_relationship'

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
  dataset_id = dba.ins_dataset( {'name': 'PANTHER protein classes', 'source': 'File %s from ftp://ftp.pantherdb.org//sequence_classifications/current_release/PANTHER_Sequence_Classification_files/, and files %s and %s from http://data.pantherdb.org/PANTHER14.1/ontology/'%(os.path.basename(P2PC_FILE), os.path.basename(CLASS_FILE), os.path.basename(RELN_FILE)), 'app': PROGRAM, 'app_version': __version__, 'url': 'http://www.pantherdb.org/'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'panther_class'},
            {'dataset_id': dataset_id, 'table_name': 'p2pc'} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)
    
  relns = {}
  line_ct = slmf.wcl(RELN_FILE)
  if not args['--quiet']:
    print "\nProcessing {} lines in relationships file {}".format(line_ct, RELN_FILE)
  with open(RELN_FILE, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    for row in tsvreader:
      ct += 1
      pcid = row[0]
      parentid = row[2]
      if pcid in relns:
        relns[pcid].append(parentid)
      else:
        relns[pcid] = [parentid]
  print "{} input lines processed.".format(ct)
  print "  Got {} PANTHER Class relationships".format(len(relns))

  pc2dbid = {}
  line_ct = slmf.wcl(CLASS_FILE)
  if not args['--quiet']:
    print "\nProcessing {} lines in class file {}".format(line_ct, CLASS_FILE)
  with open(CLASS_FILE, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    pc_ct = 0
    pcmark = {}
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
      pc = row[0]
      init = {'pcid': pc, 'name': row[2]}
      if row[3]:
        init['desc'] = row[3]
      if pc in relns:
        init['parent_pcids'] = "|".join(relns[pc])
      # there are duplicates in this file too, so only insert if we haven't
      if pc not in pcmark:
        rv = dba.ins_panther_class(init)
        if rv:
          pc_ct += 1
        else:
          dba_err_ct += 1
        pc2dbid[pc] = rv
        pcmark[pc] = True
  print "{} lines processed.".format(ct)
  print "  Inserted {} new panther_class rows".format(pc_ct)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  line_ct = slmf.wcl(P2PC_FILE)
  regex = re.compile(r'#(PC\d{5})')
  if not args['--quiet']:
    print "\nProcessing {} lines in classification file {}".format(line_ct, P2PC_FILE)
  with open(P2PC_FILE, 'rU') as tsv:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    skip_ct = 02
    pmark = {}
    p2pc_ct = 0
    notfnd = set()
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
      [sp,hgnc,up] = row[0].split('|')
      up = up.replace('UniProtKB=', '')
      hgnc = hgnc.replace('HGNC=', '')
      if not row[8]:
        skip_ct += 1
        continue
      #print "[DEBUG] searching by uniprot", up 
      targets = dba.find_targets({'uniprot': up})
      if not targets:
        #print "[DEBUG] searching by Ensembl xref", ensg 
        targets = dba.find_targets_by_xref({'xtype': 'HGNC', 'value': hgnc})
      if not targets:
        k = "%s|%s"%(up,hgnc)
        notfnd.add(k)
        continue
      t = targets[0]
      pid = t['components']['protein'][0]['id']
      pmark[pid] = True
      #print "[DEBUG] PCs:",  row[8]
      for pc in regex.findall(row[8]):
        #print "[DEBUG]    ", pc
        pcid = pc2dbid[pc]
        rv = dba.ins_p2pc({'protein_id': pid, 'panther_class_id': pcid})
        if rv:
          p2pc_ct += 1
        else:
          dba_err_ct += 1
      pbar.update(ct)
  pbar.finish()
  for k in notfnd:
    logger.warn("No target found for {}".format(k))
  print "{} lines processed.".format(ct)
  print "  Inserted {} new p2pc rows for {} distinct proteins".format(p2pc_ct, len(pmark))
  print "  Skipped {} rows without PCs".format(skip_ct)
  if notfnd:
    print "No target found for {} UniProt/HGNCs. See logfile {} for details.".format(len(notfnd), logfile)
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
