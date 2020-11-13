#!/usr/bin/env python
# Time-stamp: <2020-05-04 14:29:50 smathias>
"""Load NCBI gi xrefs into TCRD from UniProt ID Mapping file.

Usage:
    load-GIs.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-GIs.py -? | --help

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
__copyright__ = "Copyright 2016-2020, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "3.0.0"

import os,sys,time
from docopt import docopt
from TCRD7 import DBAdaptor
import logging
import csv
if sys.version_info[0] < 3:
  # Python 2
  from urllib import urlretrieve
else:
  # Python 3
  from urllib.request import urlretrieve
import gzip
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd7logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
DOWNLOAD_DIR = '../data/UniProt/'
BASE_URL = 'ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/idmapping/by_organism/'
FILENAME = 'HUMAN_9606_idmapping_selected.tab.gz'

def download(args):
  gzfn = DOWNLOAD_DIR + FILENAME
  if os.path.exists(gzfn):
    os.remove(gzfn)
  fn = gzfn.replace('.gz', '')
  if os.path.exists(fn):
    os.remove(fn)
  start_time = time.time()
  if not args['--quiet']:
    print "\nDownloading ", BASE_URL + FILENAME
    print "         to ", gzfn
  urlretrieve(BASE_URL + FILENAME, gzfn)
  print "Uncompressing", gzfn
  ifh = gzip.open(gzfn, 'rb')
  ofh = open(fn, 'wb')
  ofh.write( ifh.read() )
  ifh.close()
  ofh.close()
  if not args['--quiet']:
    elapsed = time.time() - start_time
    print "Done. Elapsed time: {}".format(slmf.secs2str(elapsed))

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

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'NCBI GI Numbers', 'source': 'UniProt ID Mapping file %s'%(BASE_URL+FILENAME), 'app': PROGRAM, 'app_version': __version__, 'url': 'http://www.uniprot.org/'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'xref', 'where_clause': "dataset_id = %d"%dataset_id})
  if not rv:
    print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
    sys.exit(1)

  start_time = time.time()
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  infile = (DOWNLOAD_DIR + FILENAME).replace('.gz', '')
  line_ct = slmf.wcl(infile)
  # ID Mappiing fields
  # 1. UniProtKB-AC
  # 2. UniProtKB-ID
  # 3. GeneID (EntrezGene)
  # 4. RefSeq
  # 5. GI
  # 6. PDB
  # 7. GO
  # 8. UniRef100
  # 9. UniRef90
  # 10. UniRef50
  # 11. UniParc
  # 12. PIR
  # 13. NCBI-taxon
  # 14. MIM
  # 15. UniGene
  # 16. PubMed
  # 17. EMBL
  # 18. EMBL-CDS
  # 19. Ensembl
  # 20. Ensembl_TRS
  # 21. Ensembl_PRO
  # 22. Additional PubMed
  if not args['--quiet']:
    print "\nProcessing {} rows in file {}".format(line_ct, infile)
  with open(infile, 'rU') as tsv:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start()
    ct = 0
    tmark = {}
    xref_ct = 0
    skip_ct = 0
    dba_err_ct = 0
    for line in tsv:
      data = line.split('\t')
      ct += 1
      up = data[0]
      if not data[4]: # no gi
        skip_ct += 1
        continue
      targets = dba.find_targets({'uniprot': up})
      if not targets:
        skip_ct += 1
        continue
      target = targets[0]
      tmark[target['id']] = True
      pid = target['components']['protein'][0]['id']
      for gi in data[4].split('; '):
        rv = dba.ins_xref({'protein_id': pid, 'xtype': 'NCBI GI', 'dataset_id': dataset_id, 'value': gi})
        if rv:
          xref_ct += 1
        else:
          dba_err_ct += 1
      pbar.update(ct)
  pbar.finish()
  print "\n{} rows processed".format(ct)
  print "  Inserted {} new GI xref rows for {} targets".format(xref_ct, len(tmark))
  print "  Skipped {} rows with no GI".format(skip_ct)
  if dba_err_ct > 0:
    print "WARNING: {} database errors occured. See logfile {} for details.".format(dba_err_ct, logfile)

if __name__ == '__main__':
  print "\n{} (v{}) [{}]:".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  download(args)
  start_time = time.time()
  load(args)
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))

