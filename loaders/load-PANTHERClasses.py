#!/usr/bin/env python
# Time-stamp: <2017-02-23 12:23:17 smathias>
"""Load PANTHER family classes into TCRD from TSV files.

Usage:
    load-PANTHERClasses.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>] [--pastid=<int>]
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
  -d --debug DEBUGL    : set debugging output level (0-3) [default: 0]
  -? --help            : print this message and exit 
"""
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2015, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.0.0"

import os,sys,time,re
from docopt import docopt
from TCRD import DBAdaptor
import csv
import logging
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
# ftp://ftp.pantherdb.org//sequence_classifications/current_release/PANTHER_Sequence_Classification_files/PTHR10.0_human
P2PC_FILE = '/home/app/TCRD/data/PANTHER/PTHR10.0_human'
# http://pantherdata.usc.edu/PANTHER10.0/ontology/Protein_Class_7.0
CLASS_FILE = '/home/app/TCRD/data/PANTHER/Protein_Class_7.0'
# http://pantherdata.usc.edu/PANTHER10.0/ontology/Protein_class_relationship
RELN_FILE = '/home/app/TCRD/data/PANTHER/Protein_class_relationship'

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
    print "\n%s (v%s) [%s]:" % (PROGRAM, __version__, time.strftime("%c"))
    print "\nConnected to TCRD database %s (schema ver %s; data ver %s)" % (args['--dbname'], dbi['schema_ver'], dbi['data_ver'])

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'PANTHER protein classes', 'source': 'File %s from ftp://ftp.pantherdb.org/sequence_classifications/10.0/PANTHER_Sequence_Classification_files/, and files %s and %s from http://pantherdata.usc.edu/PANTHER10.0/ontology/'%(os.path.basename(P2PC_FILE), os.path.basename(CLASS_FILE), os.path.basename(RELN_FILE)), 'app': PROGRAM, 'app_version': __version__, 'url': 'http://www.pantherdb.org/'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset. See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'panther_class'},
            {'dataset_id': dataset_id, 'table_name': 'p2pc'} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    if not rv:
      print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
      sys.exit(1)
    
  relns = {}
  line_ct = wcl(RELN_FILE)
  if not args['--quiet']:
    print "\nProcessing %d lines in input file %s" % (line_ct, RELN_FILE)
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
  print "%d input lines processed." % ct
  print "  Got %d PANTHER Class relationships" % len(relns)

  start_time = time.time()
  pc2dbid = {}
  line_ct = wcl(CLASS_FILE)
  if not args['--quiet']:
    print "\nProcessing %d lines in input file %s" % (line_ct, CLASS_FILE)
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
  elapsed = time.time() - start_time
  print "%d input lines processed. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "  Inserted %d new panther_class rows" % pc_ct
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)

  start_time = time.time()
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  line_ct = wcl(P2PC_FILE)
  regex = re.compile(r'#(PC\d{5})')
  if not args['--quiet']:
    print "\nProcessing %d lines in input file %s" % (line_ct, P2PC_FILE)
  with open(P2PC_FILE, 'rU') as tsv:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    skip_ct = 0
    pmark = {}
    p2pc_ct = 0
    notfnd = []
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
        notfnd.append("%s|%s"%(up,hgnc))
        #print "[DEBUG] Not found"
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
  elapsed = time.time() - start_time
  print "%d input lines processed. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "  Inserted %d new p2pc rows for %d distinct proteins" % (p2pc_ct, len(pmark))
  print "  Skipped %d rows without PCs" % skip_ct
  if notfnd:
    print "No target found for %d rows:" % len(notfnd)
    with open("tcrd4logs/PNTHR_NotFound.txt", 'wb') as outf:
      for uh in notfnd:
        outf.write("%s\n" % uh)
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)


def wcl(fname):
  with open(fname) as f:
    for i, l in enumerate(f):
      pass
  return i + 1

def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])

if __name__ == '__main__':
  main()
