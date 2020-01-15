#!/usr/bin/env python
# Time-stamp: <2019-08-21 09:36:26 smathias>
"""Load protein data from UniProt.org into TCRD via the web.

Usage:
    load-UniProtXRefs.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-UniProtXRefs.py -? | --help

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
__copyright__ = "Copyright 2019, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "1.0.0"

import os,sys,time
from docopt import docopt
from TCRDMP import DBAdaptor
import logging
import obo
from lxml import etree, objectify
from progressbar import *
import slm_tcrd_functions as slmf
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd6logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)

# Download and uncompress XML files for:
# https://www.uniprot.org/uniprot/?query=reviewed:yes AND organism:"Homo sapiens (Human) [9606]"
UP_HUMAN_FILE = '../data/UniProt/uniprot-reviewed-human_20190103.xml'
XREF_TYPE = 'RefSeq'

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

  # DBAdaptor uses same logger as load()
  dba_params = {'dbhost': args['--dbhost'], 'dbname': args['--dbname'], 'logger_name': __name__}
  dba = DBAdaptor(dba_params)
  dbi = dba.get_dbinfo()
  logger.info("Connected to TCRD database {} (schema ver {}; data ver {})".format(args['--dbname'], dbi['schema_ver'], dbi['data_ver']))
  if not args['--quiet']:
    print "\nConnected to TCRD database {} (schema ver {}; data ver {})".format(args['--dbname'], dbi['schema_ver'], dbi['data_ver'])

  start_time = time.time()
  dataset_id = 1
    
  print "\nParsing file {}".format(UP_HUMAN_FILE)
  root = objectify.parse(UP_HUMAN_FILE).getroot()
  up_ct = len(root.entry)
  print "Loading {} xrefs for {} UniProt records in file {}".format(XREF_TYPE, up_ct, UP_HUMAN_FILE)
  logger.info("Loading {} xrefs for {} UniProt records in file {}".format(XREF_TYPE, up_ct, UP_HUMAN_FILE))
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=up_ct).start()
  ct = 0
  xref_ct = 0
  skip_ct = 0
  pmark = {}
  xml_err_ct = 0
  dba_err_ct = 0
  for i in range(len(root.entry)):
    ct += 1
    entry = root.entry[i]
    logger.info("Processing entry {}".format(entry.accession))
    protein = entry2xrefs(entry, dataset_id)
    if not protein:
      xml_err_ct += 1
      logger.error("XML Error for %s" % entry.accession)
      continue
    up = protein['uniprot']
    targets = dba.find_targets({'uniprot': up}, False)
    if not targets:
      notfnd.add(up)
      continue
    t = targets[0]
    pid = t['components']['protein'][0]['id']
    if not 'xrefs' in protein:
      skip_ct += 1
      continue
    for xref in protein['xrefs']:
      xref['protein_id'] = pid
      rv = dba.ins_xref(xref)
      if not rv:
        dba_err_ct += 1
        continue
      xref_ct += 1
      pmark[pid] = True
    pbar.update(ct)
  pbar.finish()
  print "Processed {} UniProt records. Elapsed time: {}".format(ct, slmf.secs2str(elapsed))
  print "  Loaded {} {} xrefs for {} proteins.".format(xref_ct, XREF_TYPE, len(pmark))
  if skip_ct:
    print "  Skipped {} entries with no {} xrefs.".format(skip_ct, XREF_TYPE)
  if notfnd:
    print "WARNING: No target found for {} UniProt accessions. See logfile {} for details.".format(len(notfnd), logfile)
  if xml_err_ct > 0:
    print "WARNING: {} XML parsing errors occurred. See logfile {} for details.".format(xml_err_ct, logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

  
def entry2xrefs(entry, dataset_id):
  protein = {'uniprot': entry.accession} # returns first accession
  xrefs = []
  for dbr in entry.dbReference:
    if dbr.attrib['type'] == 'RefSeq':
      xrefs.append( {'xtype': dbr.attrib['type'], 'dataset_id': dataset_id,
                     'value': dbr.attrib['id']} )
  protein['xrefs'] = xrefs
  return protein


if __name__ == '__main__':
  print "\n%s (v%s) [%s]:" % (PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if int(args['--debug']):
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  start_time = time.time()
  load(args)
  elapsed = time.time() - start_time
  print "\n%s: Done. Total elapsed time: %s\n" % (PROGRAM, slmf.secs2str(elapsed))
