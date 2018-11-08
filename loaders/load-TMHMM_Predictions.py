#!/usr/bin/env python
# Time-stamp: <2018-06-01 11:25:37 smathias>
"""Load tmhmm prediction tdl_infos into TCRD.

Usage:
    load-TMHMM_Predictions.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>] [--pastid=<int>]
    load-TMHMM_Predictions.py -h | --help

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
__copyright__ = "Copyright 2016-2018, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.1.0"

import os,sys,time,re
from docopt import docopt
from TCRD import DBAdaptor
import subprocess
import logging
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd5logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
TMHMM_BIN = '/home/app/tmhmm/bin/tmhmm'

def run_and_load(args):
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
  dataset_id = dba.ins_dataset( {'name': 'TMHMM Predictions', 'source': 'Results of running TMHMM on protein sequences.', 'app': PROGRAM, 'app_version': __version__,} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'tdl_info', 'where_clause': "itype = 'TMHMM Prediction'"})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

  tct = dba.get_target_count(idg=False)
  print "\nProcessing {} TCRD targets".format(tct)
  pbar_widgets = ['Progress: ', Percentage(), ' ', Bar(marker='#',left='[',right=']'), ' ', ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=tct).start()
  
  regex = re.compile(r'PredHel=(\d+)')
  ct = 0
  ti_ct = 0
  dba_err_ct = 0
  for t in dba.get_targets(idg=False, include_annotations=False):
    ct += 1
    p = t['components']['protein'][0]
    fasta = ">%s|%s %s\n%s\n" % (t['id'], p['name'], p['description'], p['seq'])
    #print "[DEBUG] Fasta:\n%s" % fasta
    fasta_filename = "/tmp/%s.fa"%t['id']
    f = open(fasta_filename, 'w') 
    f.write(fasta)
    f.close()
    cmd = '%s --short --noplot %s' % (TMHMM_BIN, fasta_filename)
    #print "[DEBUG] Cmd: %s" % cmd
    output = ''
    for line in runProcess(cmd.split()):
      output += line
    os.remove(fasta_filename)
    #print "[DEBUG] Output: %s" % output
    pred = regex.findall(output)[0]
    #print "[DEBUG] PredHel: %s" % predhel
    if pred != '0':
      rv = dba.ins_tdl_info({'protein_id': p['id'], 'itype': 'TMHMM Prediction', 'string_value': output})
      if not rv:
        dba_err_ct += 1
        continue
      ti_ct += 1
    pbar.update(ct)
  pbar.finish()
  print "{} targets processed.".format(ct)
  print "  Inserted {} new TMHMM Prediction tdl_info rows".format(ti_ct)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

def runProcess(cmd):    
  p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
  while True:
    retcode = p.poll() #returns None while subprocess is running
    line = p.stdout.readline()
    yield line
    if retcode is not None:
      break


if __name__ == '__main__':
  print "\n{} (v{}) [{}]:".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  start_time = time.time()
  run_and_load(args)
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))
