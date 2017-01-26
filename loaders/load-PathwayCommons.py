#!/usr/bin/env python
# Time-stamp: <2017-01-12 08:57:51 smathias>
"""Load PathwayCommons pathway links into TCRD from TSV file.

Usage:
    load-PathwayCommons.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-PathwayCommons.py -? | --help

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
__author__ = "Steve Mathias"
__email__ = "smathias@salud.unm.edu"
__org__ = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2016-2017, Steve Mathias"
__license__ = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__ = "2.0.0"

import os,sys,time,re
from docopt import docopt
from TCRD import DBAdaptor
import csv
import urllib
import gzip
import logging
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
LOGFILE = "%s.log" % PROGRAM
DOWNLOAD_DIR = '../data/PathwayCommons/'
BASE_URL = 'http://www.pathwaycommons.org/archives/PC2/current/'
PATHWAYS_FILE = 'PathwayCommons.8.All.GSEA.uniprot.gmt.gz'

def download():
  gzfn = DOWNLOAD_DIR + PATHWAYS_FILE
  if os.path.exists(gzfn):
    os.remove(gzfn)
  fn = gzfn.replace('.gz', '')
  if os.path.exists(fn):
    os.remove(fn)
  print "Downloading ", BASE_URL + PATHWAYS_FILE
  print "         to ", DOWNLOAD_DIR + PATHWAYS_FILE
  urllib.urlretrieve(BASE_URL + PATHWAYS_FILE, DOWNLOAD_DIR + PATHWAYS_FILE)
  print "Uncompressing", gzfn
  ifh = gzip.open(gzfn, 'rb')
  ofh = open(fn, 'wb')
  ofh.write( ifh.read() )
  ifh.close()
  ofh.close()
  
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

  dba_params = {'dbhost': args['--dbhost'], 'dbname': args['--dbname'], 'logger_name': __name__}
  dba = DBAdaptor(dba_params)
  dbi = dba.get_dbinfo()
  logger.info("Connected to TCRD database %s (schema ver %s; data ver %s)", args['--dbname'], dbi['schema_ver'], dbi['data_ver'])
  if not args['--quiet']:
    print "\nConnected to TCRD database %s (schema ver %s; data ver %s)" % (args['--dbname'], dbi['schema_ver'], dbi['data_ver'])

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'Pathway Commons', 'source': 'File %s'%BASE_URL+PATHWAYS_FILE, 'app': PROGRAM, 'app_version': __version__, 'url': 'http://www.pathwaycommons.org/'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'pathway', 'where_clause': "pwtype LIKE 'PathwayCommons %s'"})
  if not rv:
    print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
    sys.exit(1)
    
  start_time = time.time()
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  infile = (DOWNLOAD_DIR + PATHWAYS_FILE).replace('.gz', '')
  line_ct = wcl(infile)
  if not args['--quiet']:
    print "\nProcessing %d input lines from PathwayCommons file %s" % (line_ct, infile)
  with open(infile, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    # Example line:
    # 9606: Apoptosis signaling pathway       datasource: panther; organism: 9606; id type: uniprot   O00220   O00329  O14727 ...
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start()
    ct = 0
    skip_ct = 0
    up_mark = {}
    notfnd = {}
    pw_ct = 0
    dba_err_ct = 0
    pwtypes = set()
    for row in tsvreader:
      ct += 1
      src = re.search(r'^datasource: (\w+)', row[1]).groups()[0]
      if src in ['kegg', 'wikipathways', 'reactome']:
        skip_ct += 1
        continue
      pwname = row[0].replace('9606: ', '')
      pwtype = 'PathwayCommons: ' + src
      pwtypes.add(pwtype)
      ups = row[2:]
      for up in ups:
        up_mark[up] = True
        targets = dba.find_targets({'uniprot': up})
        if not targets:
          notfnd[up] = True
          continue
        for t in targets:
          pid = t['components']['protein'][0]['id']
          rv = dba.ins_pathway({'protein_id': pid, 'pwtype': pwtype, 'name': pwname})
          if rv:
            pw_ct += 1
          else:
            dba_err_ct += 1
      pbar.update(ct)
  pbar.finish()
  elapsed = time.time() - start_time
  print "Processed %d Reactome Pathways. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "  Inserted %d pathway rows" % pw_ct
  print "  Skipped %d rows from 'kegg', 'wikipathways', 'reactome'" % skip_ct
  #print "PWTypes:\n%s\n" % "\n".join(pwtypes)
  if notfnd:
    print "WARNNING: %d (of %d) UniProt accession(s) did not find a TCRD target." % (len(notfnd), len(up_mark))
  if dba_err_ct > 0:
    print "WARNNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)


def wcl(fname):
  with open(fname) as f:
    for i, l in enumerate(f):
      pass
  return i + 1

def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])

if __name__ == '__main__':
  print "\n%s (v%s) [%s]:\n" % (PROGRAM, __version__, time.strftime("%c"))
  download()
  load()
  print "\n%s: Done.\n" % PROGRAM
