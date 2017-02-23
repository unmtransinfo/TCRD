#!/usr/bin/env python
# Time-stamp: <2017-02-23 10:45:18 smathias>
"""
Load disease associations into TCRD from DisGeNET TSV file.
Usage:
    load-DisGeNET.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-DisGeNET.py -? | --help

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
__copyright__ = "Copyright 2016, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.0.0"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import logging
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
# From http://www.disgenet.org/web/DisGeNET/menu/downloads
INPUT_FILE = '../data/DisGeNET/curated_gene_disease_associations.tsv'

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
  dataset_id = dba.ins_dataset( {'name': 'DisGeNET Disease Associations', 'source': 'File %s .'%os.path.basename(INPUT_FILE), 'app': PROGRAM, 'app_version': __version__, 'url': 'http://www.disgenet.org/web/DisGeNET/menu'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'disease', 'where_clause': "dtype = 'DisGeNET'"})
  if not rv:
    print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
    sys.exit(1)

  start_time = time.time()
  line_ct = wcl(INPUT_FILE)
  if not args['--quiet']:
     print "\nProcessing %d lines in file %s" % (line_ct, INPUT_FILE)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  with open(INPUT_FILE, 'rU') as f:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start()
    ct = 0
    k2tid = {}
    notfnd = set()
    dis_ct = 0
    dba_err_ct = 0
    for line in f:
      ct += 1
      if line.startswith('#'):
        continue
      if line.startswith('diseaseId'):
        continue
      # diseaseId       geneId  score   geneName        description     diseaseName     sourceId
      data = line.split('\t')
      geneid = data[1]
      sym = data[3]
      k = "%s|%s"%(geneid,sym)
      if k in k2tid:
        # we've already found it
        tid = k2tid[k]
      elif k in notfnd:
        # we've already not found it
          continue
      else:
        targets = dba.find_targets({'geneid': geneid}, idg=False)
        if not targets:
          targets = dba.find_targets({'sym': sym}, idg = False)
        if not targets:
          notfnd.add(geneid)
          continue
        tid = targets[0]['id']
        k2tid[k] = tid # save this mapping so we only lookup each target once
      rv = dba.ins_disease( {'target_id': tid, 'dtype': 'DisGeNET', 'name': data[5],
                             'did': data[0], 'score': data[2], 'source': data[6]} )
      if not rv:
        dba_err_ct += 1
        continue
      dis_ct += 1
      pbar.update(ct)
  pbar.finish()
  elapsed = time.time() - start_time
  if not args['--quiet']:
    print "%d lines processed. Elapsed time: %s" % (ct, secs2str(elapsed))
    print "  %d targets have disease association(s)" % len(k2tid)
    print "  Inserted %d new disease rows" % dis_ct
    if dba_err_ct > 0:
      print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)
    if notfnd:
      print "No target found for %d disease association rows." % len(notfnd)
  
  if not args['--quiet']:
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
