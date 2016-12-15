#!/usr/bin/env python
# Time-stamp: <2016-05-23 09:48:22 smathias>
"""Load data for TIN-X into TCRD from TSV files.

Usage:
    load-TIN-X.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-TIN-X.py -h | --help

Options:
  -h --dbhost DBHOST   : MySQL database host name [default: localhost]
  -n --dbname DBNAME   : MySQL database name [default: tcrd]
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
__version__   = "1.5.0"

import os,sys,time,re
from docopt import docopt
from TCRD import DBAdaptor
import logging
import obo
import csv
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
DBHOST = 'localhost'
DBPORT = 3306
DBNAME = 'tcrdev'
LOGFILE = "%s.log" % PROGRAM

DISEASE_ONTOLOGY_OBO = '/home/app/TCRD/data/DiseaseOntology/doid.obo'
PROTEIN_NOVELTY_FILE = '/home/app/TCRD/data/TIN-X/TCRD3/ProteinNovelty.csv'
DISEASE_NOVELTY_FILE = '/home/app/TCRD/data/TIN-X/TCRD3/DiseaseNovelty.csv'
PMID_RANKING_FILE = '/home/app/TCRD/data/TIN-X/TCRD3/PMIDRanking.csv'
IMPORTANCE_FILE = '/home/app/TCRD/data/TIN-X/TCRD3/Importance.csv'
SRC_FILES = [os.path.basename(PROTEIN_NOVELTY_FILE),
             os.path.basename(DISEASE_NOVELTY_FILE),
             os.path.basename(PMID_RANKING_FILE),
             os.path.basename(IMPORTANCE_FILE)]

def main():
  args = docopt(__doc__, version=__version__)
  dbhost = args['--dbhost']
  dbname = args['--dbname']
  loglevel = int(args['--loglevel'])
  if args['--logfile']:
    logfile = args['--logfile']
  else:
    logfile = "%s.log" % PROGRAM
  debug = int(args['--debug'])
  quiet = args['--quiet']
  if debug:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
    
  logger = logging.getLogger(__name__)
  logger.setLevel(loglevel)
  if not debug:
    logger.propagate = False # turns off console logging when debug is 0
  fh = logging.FileHandler(logfile)
  fmtr = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
  fh.setFormatter(fmtr)
  logger.addHandler(fh)

  dba_params = {'dbhost': dbhost, 'dbname': dbname, 'logger_name': __name__}
  dba = DBAdaptor(dba_params)
  dbi = dba.get_dbinfo()
  logger.info("Connected to TCRD database %s (schema ver %s; data ver %s)", args['--dbname'], dbi['schema_ver'], dbi['data_ver'])
  if not quiet:
    print "\n%s (v%s) [%s]:" % (PROGRAM, __version__, time.strftime("%c"))
    print "\nConnected to TCRD database %s (schema ver %s; data ver %s)" % (args['--dbname'], dbi['schema_ver'], dbi['data_ver'])

  # First parse the Disease Ontology OBO file to get DO names and defs
  print "\nParsing Disease Ontology file %s" % DISEASE_ONTOLOGY_OBO
  do_parser = obo.Parser(open(DISEASE_ONTOLOGY_OBO))
  do = {}
  for stanza in do_parser:
    do[stanza.tags['id'][0].value] = stanza.tags
  print "  Got %d Disease Ontology terms" % len(do.keys())
  
  start_time = time.time()
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  dmap = {}
  line_ct = wcl(DISEASE_NOVELTY_FILE)
  if not quiet:
    print "\nProcessing %d input lines in file %s" % (line_ct, DISEASE_NOVELTY_FILE)
  with open(DISEASE_NOVELTY_FILE, 'rU') as csvfile:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    csvreader = csv.reader(csvfile)
    header = csvreader.next() # skip header line
    # DOID,Novelty
    ct = 0
    dct = 0
    notfnd = set()
    dba_err_ct = 0
    for row in csvreader:
      ct += 1
      pbar.update(ct)
      doid = row[0]
      if doid in do:
        if 'name' in do[doid]:
          dname = do[doid]['name'][0].value
        else:
          continue
        if 'def' in do[doid]:
          ddef = do[doid]['def'][0].value
        else:
          ddef = None
      else:
        logger.warn("%s not in DO map" % row[0])
        notfnd.append(row[0])
        continue
      rv = dba.ins_tinx_disease( {'doid': doid, 'name': dname, 
                                  'summary': ddef, 'score': float(row[1])} )
      if rv:
        dct += 1
        dmap[doid] = rv # map DOID to tinx_disease.id
      else:
        dba_err_ct += 1
  pbar.finish()
  elapsed = time.time() - start_time
  print "%d input lines processed. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "  Inserted %d new tinx_disease rows" % dct
  print "  Saved %d keys in dmap" % len(dmap)
  if len(notfnd) > 0:
    print "WARNNING: No entry found in DO map for %d DOIDs. See logfile %s for details." % (len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)
  
  start_time = time.time()
  line_ct = wcl(PROTEIN_NOVELTY_FILE)
  if not quiet:
    print "\nProcessing %d input lines in file %s" % (line_ct, PROTEIN_NOVELTY_FILE)
  with open(PROTEIN_NOVELTY_FILE, 'rU') as csvfile:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    csvreader = csv.reader(csvfile)
    header = csvreader.next() # skip header line
    # Protein ID,UniProt,Novelty
    ct = 0
    tn_ct = 0
    dba_err_ct = 0
    for row in csvreader:
      ct += 1
      pbar.update(ct)
      pid = row[0]
      rv = dba.ins_tinx_novelty( {'protein_id': pid, 'score': float(row[2])} )
      if rv:
        tn_ct += 1
      else:
        dba_err_ct += 1
  pbar.finish()
  elapsed = time.time() - start_time
  print "%d input lines processed. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "  Inserted %d new tinx_novelty rows" % tn_ct
  if dba_err_ct > 0:
    print "WARNNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)

  start_time = time.time()
  imap = {}
  line_ct = wcl(IMPORTANCE_FILE)
  if not quiet:
    print "\nProcessing %d input lines in file %s" % (line_ct, IMPORTANCE_FILE)
  with open(IMPORTANCE_FILE, 'rU') as csvfile:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    csvreader = csv.reader(csvfile)
    header = csvreader.next() # skip header line
    # DOID,Protein ID,UniProt,Score
    ct = 0
    ti_ct = 0
    skips1 = set()
    dba_err_ct = 0
    for row in csvreader:
      ct += 1
      pbar.update(ct)
      if row[0] not in dmap:
        logger.error("%s not in dmap" % row[0])
        skips1.add(row[0])
        continue
      did = dmap[row[0]]
      pid = row[1]
      rv = dba.ins_tinx_importance( {'protein_id': pid, 'disease_id': did,
                                     'score': float(row[3])} )
      if rv:
        ti_ct += 1
        # map DOID|PID to tinx_importance.id
        k = "%s|%s"%(row[0],row[1])
        imap[k] = rv 
      else:
        dba_err_ct += 1
  pbar.finish()
  elapsed = time.time() - start_time
  print "%d input lines processed. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "  Inserted %d new tinx_importance rows" % ti_ct
  print "  Saved %d keys in imap" % len(imap)
  if len(skips1) > 0:
    print "WARNNING: No disease found in dmap for %d DOIDs. See logfile %s for details." % (len(skips1), logfile)
  if dba_err_ct > 0:
    print "WARNNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)

  start_time = time.time()
  line_ct = wcl(PMID_RANKING_FILE)
  if not quiet:
    print "\nProcessing %d input lines in file %s" % (line_ct, PMID_RANKING_FILE)
  regex = re.compile(r"^DOID:0*")
  with open(PMID_RANKING_FILE, 'rU') as csvfile:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    csvreader = csv.reader(csvfile)
    header = csvreader.next() # skip header line
    # DOID,Protein ID,UniProt,PubMed ID,Rank
    ct = 0
    tar_ct = 0
    skips = set()
    dba_err_ct = 0
    for row in csvreader:
      ct += 1
      pbar.update(ct)
      k = "%s|%s"%(row[0],row[1])
      if k not in imap:
        logger.warn("%s not in imap" % k)
        skips.add(k)
        continue
      iid = imap[k]
      rv = dba.ins_tinx_articlerank( {'importance_id': iid, 'pmid': row[3], 'rank': row[4]} )
      if rv:
        tar_ct += 1
      else:
        dba_err_ct += 1
  pbar.finish()
  elapsed = time.time() - start_time
  print "%d input lines processed. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "  Inserted %d new tinx_articlerank rows" % tar_ct
  if len(skips) > 0:
    print "WARNNING: No importance found in imap for %d keys. See logfile %s for details." % (len(skips), logfile)
  if dba_err_ct > 0:
    print "WARNNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)
  
  # Dataset
  rv = dba.ins_dataset( {'name': 'TIN-X Data', 'source': 'Files %s built from mentions files http://download.jensenlab.org/human_textmining_mentions.tsv and http://download.jensenlab.org/disease_textmining_mentions.tsv on 20160428.'%", ".join(SRC_FILES), 'app': PROGRAM, 'app_version': __version__, 'columns_touched': 'tinx_*.*'} )
  if not rv:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
  
  print "\n%s: Done." % PROGRAM
  print


def wcl(fname):
  with open(fname) as f:
    for i, l in enumerate(f):
      pass
  return i + 1

def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])

if __name__ == '__main__':
    main()
