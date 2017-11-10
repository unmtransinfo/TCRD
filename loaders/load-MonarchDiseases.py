#!/usr/bin/env python
# Time-stamp: <2017-11-10 13:24:10 smathias>
"""Load Monarch disease association data in TCRD from UMiami MySQL database on AWS.

Usage:
    load-MonarchDiseases.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-MonarchDiseases.py -h | --help

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
__copyright__ = "Copyright 2017, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "1.0.0"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import MySQLdb as mysql
from contextlib import closing
import logging
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
LOGFILE = './%s.log'%PROGRAM
#
MONARCH_DB_HOST = '127.0.0.1'
MONARCH_DB_PORT = 63334
MONARCH_DB_NAME = 'monarch2'
MONARCH_DB_USER = 'Jeremy'
MONARCH_DB_PW = 'pTSqdqEIsHCuxH21'
SQLq = "SELECT * FROM `gene-disease` WHERE subject_taxon = 'NCBITaxon:9606' AND (S2O IS NOT NULL OR O2S IS NOT NULL)"

def load():
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
  dataset_id = dba.ins_dataset( {'name': 'Monarch Disease Associations', 'source': 'UMiami Monarch MySQL database {} on AWS server.'.format(MONARCH_DB_NAME), 'app': PROGRAM, 'app_version': __version__, 'comments': "Monarch database contact: John Turner <jpt55@med.miami.edu>"} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'disease', 'where_clause': "dtype = 'Monarch'", 'comment': ""} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    if not rv:
      print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
      sys.exit(1)

  # Monarch MySQL connection
  # SSH tunnel must be in place for this to work:
  # ssh -i SteveSSH.pem -f -N -T -M -4 -L 63334:localhost:3306 steve@184.73.24.43
  monarchdb =  mysql.connect(host=MONARCH_DB_HOST, port=MONARCH_DB_PORT, db=MONARCH_DB_NAME,
                             user=MONARCH_DB_USER, passwd=MONARCH_DB_PW)
  if not monarchdb:
    print "ERROR connecting to Monarch database. Exiting."
    sys.exit(1)

  if not args['--quiet']:
    print "\nConnecting to UMiami Monarch database."
  monarch_g2ds = []
  with closing(monarchdb.cursor(mysql.cursors.DictCursor)) as curs:
    curs.execute(SQLq)
    for d in curs:
      monarch_g2ds.append(d)
    if not args['--quiet']:
      print "  Got {} gene-disease records from Monarch database.".format(len(monarch_g2ds))
  
  start_time = time.time()
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  gdct = len(monarch_g2ds)
  if not args['--quiet']:
    print "\nLoading %d Monarch diseases" % gdct
    logger.info("Loading %d Monarch diseases" % gdct)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=gdct).start()  
  ct = 0
  dis_ct = 0
  tmark = {}
  notfnd = set()
  dba_err_ct = 0
  for d in monarch_g2ds:
    ct += 1
    sym = d['subject_label']
    geneid = int(d['subject'].replace('NCBIGene:', ''))
    ev = "%s: %s" % (d['evidence'], d['evidence_label'])
    targets = dba.find_targets({'sym': sym})
    if not targets:
      targets = dba.find_targets({'geneid': geneid})
    if not targets:
      k = "%s|%s"%(sym,geneid)
      notfnd.add(k)
      continue
    for t in targets:
      tmark[t['id']] = True
      rv = dba.ins_disease( {'target_id': t['id'], 'dtype': 'Monarch', 'name': d['object_label'],
                             'did': d['object'], 'evidence': ev, 'O2S': d['O2S'], 'S2O': d['S2O']} )
      if not rv:
        dba_err_ct += 1
        continue
      dis_ct += 1
    pbar.update(ct)
  pbar.finish()
  elapsed = time.time() - start_time
  print "%d records processed. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "  %d targets have Monarch disease association(s)" % len(tmark.keys())
  print "  Inserted %d new disease rows" % dis_ct
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)
    

def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])

if __name__ == '__main__':
  print "\n%s (v%s) [%s]:" % (PROGRAM, __version__, time.strftime("%c"))
  load()
  print "\n%s: Done.\n" % PROGRAM
