#!/usr/local/bin/python
"""Load all shortest path distances from KEGG Pathways into TCRD.

Usage:
    load-KEGGDistances.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-KEGGDistances.py -? | --help

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
__copyright__ = "Copyright 2016-2017, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.0.0"

import os,sys,time,re
from docopt import docopt
import KEGG_Graph as kg
import networkx as nx
from TCRD import DBAdaptor
import logging
import csv
from collections import defaultdict
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
KGML_DIR = '../data/KEGG/pathways'

def calc_and_load():
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
    print "Connected to TCRD database %s (schema ver %s; data ver %s)" % (args['--dbname'], dbi['schema_ver'], dbi['data_ver'])

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'KEGG Distances', 'source': 'IDG-KMC generated data by Steve Mathias at UNM.', 'app': PROGRAM, 'app_version': __version__, 'comments': 'Directed graphs are produced from KEGG pathway KGML files and all shortest path lengths are then calculated and stored.'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'kegg_distance'})
  if not rv:
    print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
    sys.exit(1)

  kgmls = get_kgmls(KGML_DIR)

  if not args['--quiet']:
    print "\nProcessing %d KGML files in %s" % (len(kgmls), KGML_DIR)
    logger.info("Processing %d KGML files in %s" % (len(kgmls), KGML_DIR))
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=len(kgmls)).start()
  # All pathways shortest path lengths
  # (node1, node2) => distance
  all_pws_spls = {}
  ct = 0
  err_ct = 0
  for kgml in kgmls:
    logger.info("  Working on %s" % kgml)
    ct += 1
    try:
      dig = kg.kgml_file_to_digraph(kgml)
    except:
      err_ct += 1
      logger.error("Error parsing file: %s" % kgml)
      continue
    aspls = nx.all_pairs_shortest_path_length(dig)
    dct = 0
    for source in aspls:
      for target in aspls[source]:
        if source == target: continue
        st = (source, target)
        if st in all_pws_spls:
          if aspls[source][target] < all_pws_spls[st]:
            all_pws_spls[st] = aspls[source][target]
            dct += 1
        else:
          all_pws_spls[st] = aspls[source][target]
          dct += 1
    logger.info("  %s has %d non-zero shortest path lengths" % (kgml, dct))
    pbar.update(ct)
  pbar.finish()
  logger.info("Got %d total unique non-zero shortest path lengths" % len(all_pws_spls))
  if not args['--quiet']:
    print "  Got %d total unique non-zero shortest path lengths" % len(all_pws_spls)
  if err_ct > 0:
    print "WARNNING: %d parsing errors occurred. See logfile %s for details." % (err_ct, logfile)

  logger.info("Processing %d KEGG Distances" % len(all_pws_spls))
  if not args['--quiet']:
    print "\nProcessing %d KEGG Distances" % len(all_pws_spls)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=len(all_pws_spls)).start()
  gid2pids = defaultdict(list) # So we only find each target once,
                               # save protein.geneid => protein.id(s)
  notfnd = set()
  ct = 0
  skip_ct = 0
  kd_ct = 0
  dba_err_ct = 0
  for st,dist in all_pws_spls.items():
    ct += 1
    geneid1 = re.sub(r'^hsa:', '', st[0])
    geneid2 = re.sub(r'^hsa:', '', st[1])
    if geneid1 in gid2pids:
      pids1 = gid2pids[geneid1]
    elif geneid1 in notfnd:
      skip_ct += 1
      continue
    else:
      targets = dba.find_targets({'geneid': geneid1})
      if not targets:
        skip_ct += 1
        notfnd.add(geneid1) # add to notfnd so we don't try looking it up again
        logger.warn("No target found for KEGG Gene ID %s" % geneid1)
        continue
      pids1 = []
      for t in targets:
        pid = t['components']['protein'][0]['id']
        pids1.append(pid)
        gid2pids[geneid1].append(pid)
    if geneid2 in gid2pids:
      pids2 = gid2pids[geneid2]
    elif geneid2 in notfnd:
      skip_ct += 1
      continue
    else:
      targets = dba.find_targets({'geneid': geneid2})
      if not targets:
        skip_ct += 1
        notfnd.add(geneid2) # add to notfnd so we don't try looking it up again
        logger.warn("No target found for KEGG Gene ID %s" % geneid2)
        continue
      pids2 = []
      for t in targets:
        pid = t['components']['protein'][0]['id']
        pids2.append(pid)
        gid2pids[geneid2].append(pid)
    for pid1 in pids1:
      for pid2 in pids2:
        rv = dba.ins_kegg_distance({'pid1': pid1, 'pid2': pid2, 'distance': dist})
        if rv:
          kd_ct += 1
        else:
          dba_err_ct += 1
    pbar.update(ct)
  pbar.finish()
  print "%d KEGG Distances processed." % ct
  print "  Inserted %d new kegg_distance rows" % kd_ct
  if skip_ct > 0:
    print "  %d KEGG IDs not found in TCRD - Skipped %d rows. See logfile %s for details." % (len(notfnd), skip_ct, logfile)
  if dba_err_ct > 0:
    print "WARNNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)


def get_kgmls( path_to_dir ):
  filenames = os.listdir(path_to_dir)
  return [ "%s/%s"%(path_to_dir,filename) for filename in filenames if filename.endswith('kgml') ]

def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])

if __name__ == '__main__':
  print "\n%s (v%s) [%s]:\n" % (PROGRAM, __version__, time.strftime("%c"))
  start_time = time.time()
  calc_and_load()
  elapsed = time.time() - start_time
  print "\n%s: Done. Elapsed time: %s\n" % (PROGRAM, secs2str(elapsed))

