#!/usr/bin/env python
# Time-stamp: <2018-05-31 10:46:07 smathias>
"""
Load disease associations into TCRD from DisGeNET TSV file.
Usage:
    load-CTD-Diseases.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-CTD-Diseases.py -? | --help

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
__version__   = "1.0.0"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import logging
import urllib
import csv
import gzip
import cPickle as pickle
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd5logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
DOWNLOAD_DIR = '../data/CTD/'
BASE_URL = 'http://ctdbase.org/reports/'
INPUT_FILE = 'CTD_genes_diseases.tsv.gz'
OMIM2DOID_PFILE = '../data/OMIM2DOID.p'
MESH2DOID_PFILE = '../data/MeSH2DOID.p'

def download(args):
  gzfn = DOWNLOAD_DIR + INPUT_FILE
  if os.path.exists(gzfn):
    os.remove(gzfn)
  fn = gzfn.replace('.gz', '')
  if os.path.exists(fn):
    os.remove(fn)
  if not args['--quiet']:
    print "\nDownloading", BASE_URL + INPUT_FILE
    print "         to", DOWNLOAD_DIR + INPUT_FILE
  urllib.urlretrieve(BASE_URL + INPUT_FILE, DOWNLOAD_DIR + INPUT_FILE)
  if not args['--quiet']:
    print "Uncompressing", gzfn
  ifh = gzip.open(gzfn, 'rb')
  ofh = open(fn, 'wb')
  ofh.write( ifh.read() )
  ifh.close()
  ofh.close()

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

  omim2doid = pickle.load( open(OMIM2DOID_PFILE, 'r') )
  mesh2doid = pickle.load( open(MESH2DOID_PFILE, 'r') )
  
  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'CTD Disease Associations', 'source': 'File %s from %s.'%(INPUT_FILE, BASE_URL), 'app': PROGRAM, 'app_version': __version__, 'url': 'http://ctdbase.org/', 'comments': "Only disease associations with direct evidence are loaded into TCRD."} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'disease', 'where_clause': "dtype = 'CTD'"})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

  infile = (DOWNLOAD_DIR + INPUT_FILE).replace('.gz', '')
  line_ct = slmf.wcl(infile)
  if not args['--quiet']:
     print "\nProcessing {} lines in file {}".format(line_ct, infile)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  with open(infile, 'rU') as tsv:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    tsvreader = csv.reader(tsv, delimiter='\t')
    ct = 0
    k2tid = {}
    tmark = {}
    notfnd = set()
    skip_ct = 0
    dis_ct = 0
    dba_err_ct = 0
    for row in tsvreader:
      # 0: GeneSymbol
      # 1: GeneID
      # 2: DiseaseName
      # 3: DiseaseID (MeSH or OMIM identifier)
      # 4: DirectEvidence ('|'-delimited list)
      # 5: InferenceChemicalName
      # 6: InferenceScore
      # 7: OmimIDs ('|'-delimited list)
      # 8: PubMedIDs ('|'-delimited list)
      ct += 1
      if row[0].startswith('#'):
        continue
      if not row[4]: # only load associations with direct evidence
        skip_ct += 1
        continue
      sym = row[0]
      geneid = row[1]
      k = "%s|%s"%(sym,geneid)
      if k in k2tid:
        # we've already found it
        tid = k2tid[k]
      elif k in notfnd:
        # we've already not found it
        continue
      else:
        targets = dba.find_targets({'sym': sym})
        if not targets:
          targets = dba.find_targets({'geneid': geneid})
        if not targets:
          notfnd.add(geneid)
          logger.warn("No target found for {}".format(k))
          continue
        tid = targets[0]['id']
        tmark[tid] = True
        k2tid[k] = tid # save this mapping so we only lookup each target once
      # Try to map MeSH and OMIM IDs to DOIDs
      if row[3].startswith('MESH:'):
        mesh = row[3].replace('MESH:', '')
        if mesh in mesh2doid:
          did = mesh2doid[mesh]
        else:
          did = row[3]
      elif row[3].startswith('OMIM:'):
        omim = row[3].replace('OMIM:', '')
        if omim in omim2doid:
          did = omim2doid[omim]
        else:
          did = row[3]
      else:
        did = row[3]
      rv = dba.ins_disease( {'target_id': tid, 'dtype': 'CTD', 'name': row[2],
                             'did': did, 'evidence': row[4]} )
      if not rv:
        dba_err_ct += 1
        continue
      dis_ct += 1
      pbar.update(ct)
  pbar.finish()
  print "{} lines processed.".format(ct)
  print "Loaded {} new disease rows for {} targets.".format(dis_ct, len(tmark))
  if skip_ct > 0:
    print "Skipped {} with no direct evidence.".format(skip_ct)
  if notfnd:
    print "No target found for {} symbols/geneids. See logfile {} for details.".format(len(notfnd), logfile)
    #print "No target found for {} symbols/geneids.".format(len(notfnd))
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

    
if __name__ == '__main__':
  print "\n{} (v{}) [{}]:".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  start_time = time.time()
  download(args)
  load(args)
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))
