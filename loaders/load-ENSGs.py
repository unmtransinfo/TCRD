#!/usr/bin/env python
# Time-stamp: <2019-01-14 16:40:05 smathias>
"""Load Ensembl Gene IDs into TCRD.

Usage:
    load-ENSGs.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-ENSGs.py -? | --help

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
from lxml import etree, objectify
import csv
from collections import defaultdict
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd6logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
# Download and uncompress XML files for (should already be done from UniProt load):
# https://www.uniprot.org/uniprot/?query=reviewed:yes AND organism:"Homo sapiens (Human) [9606]"
# https://www.uniprot.org/uniprot/?query=organism:"Mus musculus (Mouse) [10090]"
# https://www.uniprot.org/uniprot/?query=organism:"Rattus norvegicus (Rat) [10116]"
# and
# Download and uncompress TSV files:
# ftp://ftp.ensembl.org/pub/current_tsv/homo_sapiens/Homo_sapiens.GRCh38.94.uniprot.tsv.gz
# ftp://ftp.ensembl.org/pub/current_tsv/mus_musculus/Mus_musculus.GRCm38.94.uniprot.tsv.gz
# ftp://ftp.ensembl.org/pub/current_tsv/rattus_norvegicus/Rattus_norvegicus.Rnor_6.0.94.uniprot.tsv.gz
CONFIG = {'human': {'upfile': '../data/UniProt/uniprot-reviewed-human_20190103.xml',
                    'ensfile': '../data/Ensembl/Homo_sapiens.GRCh38.94.uniprot.tsv'},
          'mouse': {'upfile': '../data/UniProt/uniprot-mouse_20190103.xml',
                    'ensfile': '../data/Ensembl/Mus_musculus.GRCm38.94.uniprot.tsv'},
          'rat': {'upfile': '../data/UniProt/uniprot-rat_20190103.xml',
                  'ensfile': '../data/Ensembl/Rattus_norvegicus.Rnor_6.0.94.uniprot.tsv'}}
NS = '{http://uniprot.org/uniprot}'
UP_SRC_FILES = [os.path.basename(d['upfile']) for d in CONFIG.values()]
ENS_SRC_FILES = [os.path.basename(d['ensfile']) for d in CONFIG.values()]

UP2ENSG = {'human': defaultdict(set), 'mouse': defaultdict(set), 'rat': defaultdict(set)}

def parse_up_files(args):
  for sp in UP2ENSG.keys():
    fn = CONFIG[sp]['upfile']
    if not args['--quiet']:
      print "Parsing file {}".format(fn)
    root = objectify.parse(fn).getroot()
    up_ct = len(root.entry)
    if not args['--quiet']:
      print "Processing {} UniProt records".format(up_ct)
    pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
    pbar = ProgressBar(widgets=pbar_widgets, maxval=up_ct).start()
    ct = 0
    for i in range(len(root.entry)):
      ct += 1
      entry = root.entry[i]
      for dbr in entry.dbReference:
        if(dbr.attrib["type"] == "Ensembl"):
          for el in dbr.findall(NS+'property'):
            if el.attrib['type'] == 'gene ID':
              UP2ENSG[sp][entry.accession].add(el.attrib["value"])
              break
          # if dbr.property is not None and len(dbr.property) > 0:
          #   for prop in dbr.property:
          #     if prop.attrib["type"] == "gene ID":
          #       UP2ENSG[sp][entry.accession].add(prop.attrib["value"])
          #       break
      pbar.update(ct)
    pbar.finish()
  if not args['--quiet']:
    mct = sum([len(UP2ENSG[sp]) for sp in UP2ENSG.keys()])
    print "Now have {} UniProt to ENSG mappings.\n".format(mct)

def parse_ens_files(args):
  for sp in UP2ENSG.keys():
    fn = CONFIG[sp]['ensfile']
    line_ct = slmf.wcl(fn)
    if not args['--quiet']:
      print "Processing {} lines in file {}".format(line_ct, fn)
    pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start()
    ct = 0
    with open(fn, 'rU') as tsv:
      tsvreader = csv.reader(tsv, delimiter='\t')
      header = tsvreader.next() # skip header line
      for row in tsvreader:
        # 0: gene_stable_id
        # 1: transcript_stable_id
        # 2: protein_stable_id
        # 3: xref
        # 4: db_name
        # 5: info_type
        # 6: source_identity
        # 7: xref_identity
        # 8: linkage_type
        if row[7] != '100':
          continue
        UP2ENSG[sp][row[3]].add(row[0])
        pbar.update(ct)
    pbar.finish()
  if not args['--quiet']:
    mct = sum([len(UP2ENSG[sp]) for sp in UP2ENSG.keys()])
    print "Now have {} UniProt to ENSG mappings.\n".format(mct)
  
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
    print "Connected to TCRD database {} (schema ver {}; data ver {})".format(args['--dbname'], dbi['schema_ver'], dbi['data_ver'])
    
  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'Ensembl Gene IDs', 'source': 'Files %s from https://www.uniprot.org/uniprot/ and files %s from ftp://ftp.ensembl.org/pub/current_tsv/'%(", ".join(UP_SRC_FILES), ", ".join(ENS_SRC_FILES)), 'app': PROGRAM, 'app_version': __version__} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'xref', 'where_clause': 'xtype = "ENSG"'})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  
  tct = dba.get_target_count(idg=False)
  if not args['--quiet']:
    print "\nProcessing {} TCRD targets".format(tct)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=tct).start() 
  ct = 0
  dba_err_ct = 0
  xref_ct = 0
  pmark = {}
  nf_ct = 0
  for target in dba.get_targets(idg=False):
    ct += 1
    p = target['components']['protein'][0]
    pid = p['id']
    up = p['uniprot']
    if up not in UP2ENSG['human']:
      nf_ct += 1
      logger.warn("UniProt accession {} not in human mapping dict".format(up))
      continue
    pmark[pid] = True
    for ensg in UP2ENSG['human'][up]:
      rv = dba.ins_xref({'protein_id': pid, 'xtype': 'ENSG',
                         'dataset_id': dataset_id, 'value': ensg})
      if rv:
        xref_ct += 1
      else:
        dba_err_ct += 1
    pbar.update(ct)
  pbar.finish()
  if not args['--quiet']:
    print "{} targets processed".format(ct)
  print "  Inserted {} new ENSG xref rows for {} proteins".format(xref_ct, len(pmark))
  if nf_ct > 0:
    print "  No ENSG found for {} UniProt accessions. See logfile {} for details.".format(nf_ct, logfile)
  if dba_err_ct > 0:
    print "WARNING: {} database errors occured. See logfile {} for details.".format(dba_err_ct, logfile)

  nhpct = dba.get_nhprotein_count()
  if not args['--quiet']:
    print "\nProcessing {} TCRD nhproteins".format(nhpct)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=nhpct).start() 
  ct = 0
  dba_err_ct = 0
  xref_ct = 0
  nhp_mark = {}
  nf_ct = 0
  for nhp in dba.get_nhproteins():
    ct += 1
    nhpid = nhp['id']
    up = nhp['uniprot']
    if nhp['species'] == 'Mus musculus':
      sp = 'mouse'
    elif nhp['species'] == '':
      sp = 'rat'
    if up not in UP2ENSG[sp]:
      nf_ct += 1
      logger.warn("UniProt accession {} not in {} mapping dict".format(up, sp))
      continue
    nhp_mark[nhpid] = True
    for ensg in UP2ENSG[sp][up]:
      rv = dba.ins_xref({'nhprotein_id': nhpid, 'xtype': 'ENSG',
                         'dataset_id': dataset_id, 'value': ensg})
      if rv:
        xref_ct += 1
      else:
        dba_err_ct += 1
    pbar.update(ct)
  pbar.finish()
  if not args['--quiet']:
    print "{} nhproteins processed".format(ct)
  print "  Inserted {} new ENSG xref rows for {} nhproteins".format(xref_ct, len(nhp_mark))
  if nf_ct > 0:
    print "  No ENSG found for {} UniProt accessions. See logfile {} for details.".format(nf_ct, logfile)
  if dba_err_ct > 0:
    print "WARNING: {} database errors occured. See logfile {} for details.".format(dba_err_ct, logfile)

if __name__ == '__main__':
  print "\n{} (v{}) [{}]:\n".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  start_time = time.time()
  parse_up_files(args)
  parse_ens_files(args)
  load(args)
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))
