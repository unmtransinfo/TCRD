#!/usr/local/bin/python
"""Load all shortest path distances from KEGG Pathways into TCRD.

Usage:
    load-KEGGDistances.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
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
  -d --debug           : turn on debugging output
  -? --help            : print this message and exit
"""
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2016-2019, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "3.0.0"

import os,sys,time,re
from docopt import docopt
import KEGG_Graph as kg
import networkx as nx
from TCRDMP import DBAdaptor
import logging
import csv
from collections import defaultdict
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd6logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
KGML_DIR = '../data/KEGG/pathways'

def calc_and_load(args):
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
  dataset_id = dba.ins_dataset( {'name': 'KEGG Distances', 'source': 'IDG-KMC generated data by Steve Mathias at UNM.', 'app': PROGRAM, 'app_version': __version__, 'comments': 'Directed graphs are produced from KEGG pathway KGML files and all shortest path lengths are then calculated and stored.'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'kegg_distance'})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

  kgmls = get_kgmls(KGML_DIR)

  if not args['--quiet']:
    print "\nProcessing {} KGML files in {}".format(len(kgmls), KGML_DIR)
    logger.info("Processing {} KGML files in {}".format(len(kgmls), KGML_DIR))
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=len(kgmls)).start()
  # All pathways shortest path lengths
  # (node1, node2) => distance
  all_pws_spls = {}
  ct = 0
  err_ct = 0
  for kgml in kgmls:
    logger.info("  Working on {}".format(kgml))
    ct += 1
    try:
      dig = kg.kgml_file_to_digraph(kgml)
    except:
      err_ct += 1
      logger.error("Error parsing file: {}".format(kgml))
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
    logger.info("  {} has {} non-zero shortest path lengths".format(kgml, dct))
    pbar.update(ct)
  pbar.finish()
  logger.info("Got {} total unique non-zero shortest path lengths".format(len(all_pws_spls)))
  if not args['--quiet']:
    print "  Got {} total unique non-zero shortest path lengths".format(len(all_pws_spls))
  if err_ct > 0:
    print "WARNNING: {} parsing errors occurred. See logfile {} for details.".format(err_ct, logfile)

  logger.info("Processing {} KEGG Distances".format(len(all_pws_spls)))
  if not args['--quiet']:
    print "\nProcessing {} KEGG Distances".format(len(all_pws_spls))
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
        logger.warn("No target found for KEGG Gene ID {}".format(geneid1))
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
        logger.warn("No target found for KEGG Gene ID {}".format(geneid2))
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
  print "{} KEGG Distances processed.".format(ct)
  print "  Inserted {} new kegg_distance rows".format(kd_ct)
  if skip_ct > 0:
    print "  {} KEGG IDs not found in TCRD - Skipped {} rows. See logfile {} for details.".format(len(notfnd), skip_ct, logfile)
  if dba_err_ct > 0:
    print "WARNNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

def get_kgmls( path_to_dir ):
  filenames = os.listdir(path_to_dir)
  return [ "%s/%s"%(path_to_dir,filename) for filename in filenames if filename.endswith('kgml') ]


if __name__ == '__main__':
  print "\n{} (v{}) [{}]:".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  start_time = time.time()
  calc_and_load(args)
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))
