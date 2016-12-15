#!/usr/bin/env python
# Time-stamp: <2016-11-30 10:04:32 smathias>
"""Load NCBI gi xrefs into TCRD from UniProt ID Mapping file.

Usage:
    load-GIs.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-GIs.py -? | --help

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
import logging
import csv
import urllib
import gzip
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
DBHOST = 'localhost'
DBPORT = 3306
DBNAME = 'tcrdev'
LOGFILE = './%s.log'%PROGRAM
DOWNLOAD_DIR = '../data/UniProt/'
BASE_URL = 'ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/idmapping/by_organism/'
FILENAME = 'HUMAN_9606_idmapping_selected.tab.gz'

def download():
  gzfn = DOWNLOAD_DIR + FILENAME
  if os.path.exists(gzfn):
    os.remove(gzfn)
  fn = gzfn.replace('.gz', '')
  if os.path.exists(fn):
    os.remove(fn)
  start_time = time.time()
  print "\nDownloading ", BASE_URL + FILENAME
  print "         to ", gzfn
  urllib.urlretrieve(BASE_URL + FILENAME, gzfn)
  print "Uncompressing", gzfn
  ifh = gzip.open(gzfn, 'rb')
  ofh = open(fn, 'wb')
  ofh.write( ifh.read() )
  ifh.close()
  ofh.close()
  elapsed = time.time() - start_time
  print "Done. Elapsed time: %s" % secs2str(elapsed)

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
    print "\n%s (v%s) [%s]:" % (PROGRAM, __version__, time.strftime("%c"))
    print "\nConnected to TCRD database %s (schema ver %s; data ver %s)" % (args['--dbname'], dbi['schema_ver'], dbi['data_ver'])

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'NCBI GI Numbers', 'source': 'UniProt ID Mapping file %s'%(BASE_URL+FILENAME), 'app': PROGRAM, 'app_version': __version__, 'url': 'http://www.uniprot.org/'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)

  start_time = time.time()
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  infile = (DOWNLOAD_DIR + FILENAME).replace('.gz', '')
  line_ct = wcl(infile)
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
    print "\nProcessing %d rows in file %s" % (line_ct, infile)
  with open(infile, 'rU') as tsv:
    ct = 0
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
      if not data[4]:
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

  elapsed = time.time() - start_time
  if not args['--quiet']:
    print "\n%d rows processed. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "%d targets annotated with GI xref(s)" % len(tmark.keys())
  print "  Skipped %d rows" % skip_ct
  print "  Inserted %d new GI xref rows" % xref_ct

def wcl(fname):
  with open(fname) as f:
    for i, l in enumerate(f):
      pass
  return i + 1

def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])

if __name__ == '__main__':
  print "\n%s (v%s) [%s]:" % (PROGRAM, __version__, time.strftime("%c"))
  download()
  load()
  print "\n%s: Done.\n" % PROGRAM
