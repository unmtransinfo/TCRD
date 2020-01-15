#!/usr/bin/env python
# Time-stamp: <2019-10-14 11:58:12 smathias>
"""
Load disease associations into TCRD from DisGeNET TSV file.
Usage:
    load-DisGeNET.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
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
  -d --debug           : turn on debugging output
  -? --help            : print this message and exit 
"""
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2016-2019, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.3.0"

import os,sys,time
from docopt import docopt
from TCRDMP import DBAdaptor
import logging
import urllib
import gzip
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd6logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
DOWNLOAD_DIR = '../data/DisGeNET/'
BASE_URL = 'http://www.disgenet.org/static/disgenet_ap1/files/downloads/'
INPUT_FILE = 'curated_gene_disease_associations.tsv.gz'

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
    
  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'DisGeNET Disease Associations', 'source': 'File %s from %s.'%(INPUT_FILE, BASE_URL), 'app': PROGRAM, 'app_version': __version__, 'url': 'http://www.disgenet.org/web/DisGeNET/menu'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'disease', 'where_clause': "dtype = 'DisGeNET'"})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

  infile = (DOWNLOAD_DIR + INPUT_FILE).replace('.gz', '')
  line_ct = slmf.wcl(infile)
  if not args['--quiet']:
     print "\nProcessing {} lines in file {}".format(line_ct, infile)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  with open(infile, 'rU') as f:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start()
    ct = 0
    k2pids = {}
    pmark = {}
    notfnd = set()
    dis_ct = 0
    dba_err_ct = 0
    for line in f:
      # 0: geneId
      # 1: geneSymbol
      # 2: DSI
      # 3: DPI
      # 4: diseaseId
      # 5: diseaseName
      # 6: diseaseType
      # 7: diseaseClass
      # 8: diseaseSemanticType
      # 9: score
      # 10: EI
      # 11: YearInitial
      # 12: YearFinal
      # 13: NofPmids
      # 14: NofSnps
      # 15: source
      ct += 1
      if line.startswith('#'):
        continue
      if line.startswith('geneId'):
        # header row
        continue
      data = line.split('\t')
      geneid = data[0].strip()
      sym = data[1]
      k = "%s|%s"%(sym,geneid)
      if k in k2pids:
        # we've already found it
        pids = k2pids[k]
      elif k in notfnd:
        # we've already not found it
          continue
      else:
        targets = dba.find_targets({'sym': sym})
        if not targets:
          targets = dba.find_targets({'geneid': geneid})
        if not targets:
          notfnd.add(k)
          logger.warn("No target found for {}".format(k))
          continue
        pids = []
        for t in targets:
          p = t['components']['protein'][0]
          pmark[p['id']] = True
          pids.append(p['id'])
        k2pids[k] = pids # save this mapping so we only lookup each target once
      pmid_ct = data[13].strip()
      snp_ct = data[14].strip()
      if pmid_ct != '0':
        if snp_ct != '0':
          ev = "%s PubMed IDs; %s SNPs"%(pmid_ct, snp_ct)
        else:
          ev = "%s PubMed IDs"%pmid_ct
      else:
        ev = "%s SNPs"%snp_ct
      for pid in pids:
        rv = dba.ins_disease( {'protein_id': pid, 'dtype': 'DisGeNET', 'name': data[5],
                               'did': data[4], 'score': data[9], 'source': data[15].strip(),
                               'evidence': ev} )
        if not rv:
          dba_err_ct += 1
          continue
        dis_ct += 1
      pbar.update(ct)
  pbar.finish()
  print "{} lines processed.".format(ct)
  print "Loaded {} new disease rows for {} proteins.".format(dis_ct, len(pmark))
  if notfnd:
    print "No target found for {} symbols/geneids. See logfile {} for details.".format(len(notfnd), logfile)
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
