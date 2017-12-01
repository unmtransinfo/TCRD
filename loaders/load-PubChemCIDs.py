#!/usr/bin/env python
# Time-stamp: <2017-11-16 10:04:38 smathias>
"""Load PubChem CIDs into TCRD from TSV file.

Usage:
    load-PubChemCIDs.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-PubChemCIDs.py -? | --help

Options:
  -h --dbhost DBHOST   : MySQL database host name [default: localhost]
  -n --dbname DBNAME   : MySQL database name [default: tcrevd]
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
__copyright__ = "Copyright 2017, Steve Mathias"
__license__ = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__ = "1.0.1"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import gzip
import urllib
import logging
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
DOWNLOAD_DIR = '../data/ChEMBL/UniChem/'
BASE_URL = 'ftp://ftp.ebi.ac.uk/pub/databases/chembl/UniChem/data/wholeSourceMapping/src_id1/'
# For src onfo, see https://www.ebi.ac.uk/unichem/ucquery/listSources
FILENAME = 'src1src22.txt.gz'

def download(args):
  start_time = time.time()
  gzfn = DOWNLOAD_DIR + FILENAME
  if os.path.exists(gzfn):
    os.remove(gzfn)
  fn = gzfn.replace('.gz', '')
  if os.path.exists(fn):
    os.remove(fn)
  if not args['--quiet']:
    print "\nDownloading ", BASE_URL + FILENAME
    print "         to ", gzfn
  urllib.urlretrieve(BASE_URL + FILENAME, gzfn)
  if not args['--quiet']:
    print "Uncompressing", gzfn
  ifh = gzip.open(gzfn, 'rb')
  ofh = open(fn, 'wb')
  ofh.write( ifh.read() )
  ifh.close()
  ofh.close()
  elapsed = time.time() - start_time
  if not args['--quiet']:
    print "Done. Elapsed time: %s" % secs2str(elapsed)

def load(infile, args, logger):
  # DBAdaptor uses same logger as main()
  dba_params = {'dbhost': args['--dbhost'], 'dbname': args['--dbname'], 'logger_name': __name__}
  dba = DBAdaptor(dba_params)
  dbi = dba.get_dbinfo()
  logger.info("Connected to TCRD database %s (schema ver %s; data ver %s)", args['--dbname'], dbi['schema_ver'], dbi['data_ver'])
  if not args['--quiet']:
    print "\nConnected to TCRD database %s (schema ver %s; data ver %s)" % (args['--dbname'], dbi['schema_ver'], dbi['data_ver'])

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'PubChem CIDs', 'source': 'File %s'%BASE_URL+FILENAME, 'app': PROGRAM, 'app_version': __version__} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'chembl_activity', 'column_name': 'pubchem_cid', 'comment': "Loaded from UniChem file mapping ChEMBL IDs to PubChem CIDs."},
            {'dataset_id': dataset_id, 'table_name': 'drug_activity', 'column_name': 'pubchem_cid', 'comment': "Loaded from UniChem file mapping ChEMBL IDs to PubChem CIDs."} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    if not rv:
      print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
      sys.exit(1)

  line_ct = wcl(infile)
  if not args['--quiet']:
    print "\nProcessing %d lines in file %s" % (line_ct, infile)
  chembl2pc = {}
  with open(infile, 'rU') as tsv:
    ct = 0
    tsv.readline() # skip header line
    for line in tsv:
      data = line.split('\t')
      chembl2pc[data[0]] = int(data[1])
  if not args['--quiet']:
    print "Got %d ChEMBL to PubChem mappings" % len(chembl2pc)
  
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]

  start_time = time.time()
  chembl_activities = dba.get_chembl_activities()
  if not args['--quiet']:
    print "\nLoading PubChem CIDs for %d ChEMBL activities" % len(chembl_activities)
  logger.info("Loading PubChem CIDs for %d ChEMBL activities" % len(chembl_activities))
  pbar = ProgressBar(widgets=pbar_widgets, maxval=len(chembl_activities)).start()
  ct = 0
  pcid_ct = 0
  notfnd = set()
  dba_err_ct = 0
  for ca in chembl_activities:
    ct += 1
    if ca['cmpd_chemblid'] not in chembl2pc:
      notfnd.add(ca['cmpd_chemblid'])
      continue
    pccid = chembl2pc[ca['cmpd_chemblid']]
    rv = dba.do_update({'table': 'chembl_activity', 'id': ca['id'],
                        'col': 'cmpd_pubchem_cid', 'val': pccid})
    if rv:
      pcid_ct += 1
    else:
      dba_err_ct += 1
    pbar.update(ct)
  pbar.finish()
  elapsed = time.time() - start_time
  if not args['--quiet']:
    print "%d ChEMBL activities processed. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "  Inserted %d new PubChem CIDs" % pcid_ct
  if len(notfnd) > 0:
    print "  [WARNING] %d ChEMBL IDs not found" % len(notfnd)
  if dba_err_ct > 0:
    print "WARNNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)
    
  start_time = time.time()
  drug_activities = dba.get_drug_activities()
  if not args['--quiet']:
    print "\nLoading PubChem CIDs for %d drug activities" % len(drug_activities)
  logger.info("Loading PubChem CIDs for %d drug activities" % len(drug_activities))
  pbar = ProgressBar(widgets=pbar_widgets, maxval=len(drug_activities)).start()
  ct = 0
  pcid_ct = 0
  skip_ct = 0
  notfnd = set()
  dba_err_ct = 0
  for da in drug_activities:
    ct += 1
    if not da['cmpd_chemblid']:
      skip_ct += 1
      continue
    if da['cmpd_chemblid'] not in chembl2pc:
      notfnd.add(da['cmpd_chemblid'])
      continue
    pccid = chembl2pc[da['cmpd_chemblid']]
    rv = dba.do_update({'table': 'drug_activity', 'id': da['id'],
                        'col': 'cmpd_pubchem_cid', 'val': pccid})
    if rv:
      pcid_ct += 1
    else:
      dba_err_ct += 1
    pbar.update(ct)
  pbar.finish()
  elapsed = time.time() - start_time
  if not args['--quiet']:
    print "%d drug activities processed. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "  Inserted %d new PubChem CIDs" % pcid_ct
  print "  Skipped %d drug activities with no ChEMBL ID" % skip_ct
  if len(notfnd) > 0:
    print "  [WARNING] %d ChEMBL IDs not found" % len(notfnd)
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
  args = docopt(__doc__, version=__version__)
  if not args['--quiet']:
    print "\n%s (v%s) [%s]:" % (PROGRAM, __version__, time.strftime("%c"))
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
  
  #download(args)
  infile = DOWNLOAD_DIR + FILENAME
  infile = infile.replace('.gz', '')
  load(infile, args, logger)
  
  print "\n%s: Done.\n" % PROGRAM
