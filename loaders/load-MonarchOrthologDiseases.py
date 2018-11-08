#!/usr/bin/env python
# Time-stamp: <2018-05-17 11:17:05 smathias>
"""Load Monarch ortholog disease association data in TCRD from UMiami MySQL database on AWS.

Usage:
    load-MonarchOrthologDiseases.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-MonarchOrthologDiseases.py -h | --help

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
__copyright__ = "Copyright 2018, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "1.1.0"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import MySQLdb as mysql
from contextlib import closing
import string
import logging
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = 'tcrd5logs/'
LOGFILE = LOGDIR + '%s.log'%PROGRAM
# Monarch MySQL connection parameters
# SSH tunnel must be in place for this to work:
# ssh -i SteveSSH.pem -f -N -T -M -4 -L 63334:localhost:3306 steve@184.73.24.43
MONARCH_DB_HOST = '127.0.0.1'
MONARCH_DB_PORT = 63334
MONARCH_DB_NAME = 'monarch2'
MONARCH_DB_USER = 'Jeremy'
MONARCH_DB_PW = 'pTSqdqEIsHCuxH21'
SQLq = "SELECT * FROM tcrdmatches_full WHERE object LIKE 'OMIM%' OR object LIKE 'DOID%';"

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
  # the following maps Monarch's tcrdmatches_full.subject to TCRD's ortholog.id
  # ie. 'MGI:1347010' => 156650
  ortho2id = dba.get_orthologs_dbid2id()
  if not args['--quiet']:
    print "\nGot {} orthologs from TCRD".format(len(ortho2id))
  
  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'Monarch Ortholog Disease Associations', 'source': 'UMiami Monarch MySQL database {} on AWS server.'.format(MONARCH_DB_NAME), 'app': PROGRAM, 'app_version': __version__, 'comments': "Monarch database contact: John Turner <jpt55@med.miami.edu>"} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'ortho_disease', 'comment': ""} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

  if not args['--quiet']:
    print "\nConnecting to UMiami Monarch database."
  monarchdb =  mysql.connect(host=MONARCH_DB_HOST, port=MONARCH_DB_PORT, db=MONARCH_DB_NAME,
                             user=MONARCH_DB_USER, passwd=MONARCH_DB_PW)
  assert monarchdb, "ERROR connecting to Monarch database."
  monarch_odas = []
  with closing(monarchdb.cursor(mysql.cursors.DictCursor)) as curs:
    curs.execute(SQLq)
    for d in curs:
      monarch_odas.append(d)
  if not args['--quiet']:
    print "  Got {} ortholog disease records from Monarch database.".format(len(monarch_odas))
  
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]

  oda_ct = len(monarch_odas)
  if not args['--quiet']:
    print "\nLoading {} Monarch ortholog diseases".format(oda_ct)
    logger.info("Loading {} Monarch ortholog diseases".format(oda_ct))
  pbar = ProgressBar(widgets=pbar_widgets, maxval=oda_ct).start()  
  ct = 0
  od_ct = 0
  tmark = {}
  ortho_notfnd = set()
  notfnd = set()
  dba_err_ct = 0
  for d in monarch_odas:
    ct += 1
    if d['subject'] in ortho2id:
      ortho_id = ortho2id[d['subject']]
    else:
      ortho_notfnd.add(d['subject'])
      logger.warn("Ortholog dbid {} not found in TCRD".format(d['subject']))
      continue
    # some names have unprintable characters...
    name = filter(lambda x: x in string.printable, d['object_label'])
    geneid = int(d['geneID'])
    targets = dba.find_targets({'geneid': geneid})
    if not targets:
      sym = d['subject_label'].upper() # upcase mouse symbol
      targets = dba.find_targets({'sym': sym})
    if not targets:
      k = "%s|%s"%(geneid,sym)
      notfnd.add(k)
      logger.warn("Target not found in TCRD for {}".format(k))
      continue
    for t in targets:
      tmark[t['id']] = True
      rv = dba.ins_ortholog_disease( {'target_id': t['id'], 'protein_id': t['id'],
                                      'did': d['object'], 'name': name,
                                      'ortholog_id': ortho_id, 'score': d['score'] } )
      if not rv:
        dba_err_ct += 1
        continue
      od_ct += 1
    pbar.update(ct)
  pbar.finish()
  print "{} records processed.".format(ct)
  print "  Inserted {} new ortholog_disease rows for {} targets".format(od_ct, len(tmark))
  if notfnd:
    print "WARNING: {} targets not found in TCRD. See logfile {} for details.".format(len(notfnd), logfile)
  if ortho_notfnd:
    print "WARNING: {} orthologs not found in TCRD. See logfile {} for details.".format(len(ortho_notfnd), logfile)
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
