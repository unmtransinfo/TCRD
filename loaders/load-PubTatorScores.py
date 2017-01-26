#!/usr/bin/env python
# Time-stamp: <2017-01-12 11:28:54 smathias>
"""Load PubTator PubMed Score tdl_infos in TCRD from TSV file.

Usage:
    load-PubTatorScores.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-PubTatorScores.py -h | --help

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
__copyright__ = "Copyright 2016, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.0.0"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import csv
import logging
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
LOGFILE = "%s.log" % PROGRAM
INFILE = '../data/JensenLab/pubtator_counts.tsv'

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

  # Use logger from this module
  dba_params = {'dbhost': args['--dbhost'], 'dbname': args['--dbname'], 'logger_name': __name__}
  dba = DBAdaptor(dba_params)
  dbi = dba.get_dbinfo()
  logger.info("Connected to TCRD database %s (schema ver %s; data ver %s)", args['--dbname'], dbi['schema_ver'], dbi['data_ver'])
  if not args['--quiet']:
    print "\n%s (v%s) [%s]:" % (PROGRAM, __version__, time.strftime("%c"))
    print "\nConnected to TCRD database %s (schema ver %s; data ver %s)" % (args['--dbname'], dbi['schema_ver'], dbi['data_ver'])
  
  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'PubTator Text-mining Scores', 'source': 'File %s obtained directly from Lars Juhl Jensen'%os.path.basename(INFILE), 'app': PROGRAM, 'app_version': __version__, 'url': 'https://www.ncbi.nlm.nih.gov/CBBresearch/Lu/Demo/PubTator/', 'comments': 'PubTator data was subjected to the same counting scheme used to generate JensenLab PubMed Scores.'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'ptscore'},
            {'dataset_id': dataset_id, 'table_name': 'tdl_info', 'where_clause': "itype = 'PubTator PubMed Score'"} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    if not rv:
      print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
      sys.exit(1)


  start_time = time.time()
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  ptscores = {} # protein.id => sum(all scores)
  pts_ct = 0
  dba_err_ct = 0
  line_ct = wcl(INFILE)
  if not args['--quiet']:
    print "\nProcessing %d input lines in file %s" % (line_ct, INFILE)
  with open(INFILE, 'rU') as tsv:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    geneid2pid = {}
    notfnd = set()
    for row in tsvreader:
      # NCBI Gene ID  year  score
      ct += 1
      pbar.update(ct)
      gidstr = row[0].replace(',', ';')
      geneids = gidstr.split(';')
      for geneid in geneids:
        if not geneid or '(tax:' in geneid:
          continue
        if geneid in geneid2pid:
          # we've already found it
          pids = geneid2pid[geneid]
        elif geneid in notfnd:
          # we've already not found it
          continue
        else:
          targets = dba.find_targets({'geneid': geneid})
          if not targets:
            notfnd.add(geneid)
            continue
          pids = []
          for target in targets:
            pids.append(target['components']['protein'][0]['id'])
            geneid2pid[geneid] = pids # save this mapping so we only lookup each target once
        for pid in pids:
          rv = dba.ins_ptscore({'protein_id': pid, 'year': row[1], 'score': row[2]} )
          if rv:
            pts_ct += 1
          else:
            dba_err_ct += 1
          if pid in ptscores:
            ptscores[pid] += float(row[2])
          else:
            ptscores[pid] = float(row[2])
  pbar.finish()

  elapsed = time.time() - start_time
  print "%d input lines processed. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "  %d targets have PubTator PubMed Scores" % len(ptscores.keys())
  print "  Inserted %d new ptscore rows" % pts_ct
  if notfnd:
    print "No target found for %d NCBI Gene IDs." % len(notfnd)
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)
  
  print "\nLoading %d PubTator Score tdl_infos" % len(ptscores.keys())
  ct = 0
  ti_ct = 0
  dba_err_ct = 0
  for pid,score in ptscores.items():
    ct += 1
    rv = dba.ins_tdl_info({'protein_id': pid, 'itype': 'PubTator Score', 
                           'number_value': score} )
    if rv:
      ti_ct += 1
    else:
      dba_err_ct += 1
  print "  %d processed" % ct
  print "  Inserted %d new PubTator PubMed Score tdl_info rows" % ti_ct
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)

  print "\n%s: Done.\n" % PROGRAM
  

def wcl(fname):
  with open(fname) as f:
    for i, l in enumerate(f):
      pass
  return i + 1

def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])

if __name__ == '__main__':
  main()
