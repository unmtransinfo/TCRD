#!/usr/bin/env python
# Time-stamp: <2019-08-21 12:52:19 smathias>
"""Load PathwayCommons pathway links into TCRD from TSV file.

Usage:
    load-PathwayCommons.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
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
  -d --debug           : turn on debugging output
  -? --help            : print this message and exit 
"""
__author__ = "Steve Mathias"
__email__ = "smathias@salud.unm.edu"
__org__ = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2016-2019, Steve Mathias"
__license__ = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__ = "3.0.0"

import os,sys,time,re
from docopt import docopt
from TCRD import DBAdaptor
import csv
import urllib
import gzip
import logging
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd6logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
DOWNLOAD_DIR = '../data/PathwayCommons/'
BASE_URL = 'http://www.pathwaycommons.org/archives/PC2/v11/'
PATHWAYS_FILE = 'PathwayCommons11.All.uniprot.gmt.gz'
PCAPP_BASE_URL = 'http://apps.pathwaycommons.org/pathways?uri='

def download(args):
  gzfn = DOWNLOAD_DIR + PATHWAYS_FILE
  if os.path.exists(gzfn):
    os.remove(gzfn)
  fn = gzfn.replace('.gz', '')
  if os.path.exists(fn):
    os.remove(fn)
  if not args['--quiet']:
    print "\nDownloading ", BASE_URL + PATHWAYS_FILE
    print "         to ", DOWNLOAD_DIR + PATHWAYS_FILE
  urllib.urlretrieve(BASE_URL + PATHWAYS_FILE, DOWNLOAD_DIR + PATHWAYS_FILE)
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
  dataset_id = dba.ins_dataset( {'name': 'Pathway Commons', 'source': 'File %s'%BASE_URL+PATHWAYS_FILE, 'app': PROGRAM, 'app_version': __version__, 'url': 'http://www.pathwaycommons.org/'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'pathway', 'where_clause': "pwtype LIKE 'PathwayCommons %s'"})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)
    
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  infile = (DOWNLOAD_DIR + PATHWAYS_FILE).replace('.gz', '')
  line_ct = slmf.wcl(infile)
  if not args['--quiet']:
    print "\nProcessing {} records from PathwayCommons file {}".format(line_ct, infile)
  with open(infile, 'rU') as tsv:
    tsvreader = csv.reader(tsv, delimiter='\t')
    # Example line:
    # http://identifiers.org/kegg.pathway/hsa00010    name: Glycolysis / Gluconeogenesis; datasource: kegg; organism: 9606; idtype: uniprot  A8K7J7  B4DDQ8  B4DNK4  E9PCR7  P04406  P06744  P07205  P07738  P09467 P09622   P09972  P10515  P11177  P14550  P30838  P35557  P51648  P60174  Q01813  Q16822  Q53Y25  Q6FHV6 Q6IRT1   Q6ZMR3  Q8IUN7  Q96C23  Q9BRR6  Q9NQR9  Q9NR19
    # However, note that pathway commons URLs in file give 404.
    # E.g. URL from this line:
    # http://pathwaycommons.org/pc2/Pathway_0136871cbdf9a3ecc09529f1878171df  name: VEGFR1 specific signals; datasource: pid; organism: 9606; idtype: uniprot    O14786  O15530  O60462  P05771  P07900  P15692  P16333  P17252  P17612  P17948  P19174  P20936     P22681  P27361  P27986  P28482  P29474  P31749  P42336  P49763  P49765  P62158  P98077  Q03135  Q06124  Q16665  Q9Y5K6
    # needs to be converted to:
    # http://apps.pathwaycommons.org/pathways?uri=http%3A%2F%2Fpathwaycommons.org%2Fpc2%2FPathway_0136871cbdf9a3ecc09529f1878171df
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start()
    ct = 0
    skip_ct = 0
    up2pid = {}
    pmark = set()
    notfnd = set()
    pw_ct = 0
    dba_err_ct = 0
    for row in tsvreader:
      ct += 1
      src = re.search(r'datasource: (\w+)', row[1]).groups()[0]
      if src in ['kegg', 'wikipathways', 'reactome']:
        skip_ct += 1
        continue
      pwtype = 'PathwayCommons: ' + src
      name = re.search(r'name: (.+?);', row[1]).groups()[0]
      url = PCAPP_BASE_URL + urllib.quote(row[0], safe='')
      ups = row[2:]
      for up in ups:
        if up in up2pid:
          pid = up2pid[up]
        elif up in notfnd:
          continue
        else:
          targets = dba.find_targets({'uniprot': up})
          if not targets:
            notfnd.add(up)
            continue
          t = targets[0]
          pid = t['components']['protein'][0]['id']
          up2pid[up] = pid
        rv = dba.ins_pathway({'protein_id': pid, 'pwtype': pwtype, 'name': name, 'url': url})
        if rv:
          pw_ct += 1
          pmark.add(pid)
        else:
          dba_err_ct += 1
      pbar.update(ct)
  pbar.finish()
  for up in notfnd:
    logger.warn("No target found for {}".format(up))
  print "Processed {} Pathway Commons records.".format(ct)
  print "  Inserted {} new pathway rows for {} proteins.".format(pw_ct, len(pmark))
  print "  Skipped {} records from 'kegg', 'wikipathways', 'reactome'".format(skip_ct)
  if notfnd:
    print "  No target found for {} UniProt accessions. See logfile {} for details.".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)


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
