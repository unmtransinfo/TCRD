#!/usr/bin/env python
# Time-stamp: <2020-06-29 14:00:21 smathias>
"""Load DTO and DTO IDs and classifications into TCRD from OWL file and CSV files.

Usage:
    load-DTO.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-DTO.py --help

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
__copyright__ = "Copyright 2015-2020, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "4.0.0"

import os,sys,time
from docopt import docopt
from TCRD7 import DBAdaptor
import csv
import pronto
import logging
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = 'tcrd7logs/'
LOGFILE = LOGDIR + '%s.log'%PROGRAM
MAPPING_FILE = '../data/UMiami/DTO2UniProt_DTOv2.csv'
CLASS_FILE = '../data/UMiami/Final_ProteomeClassification_Sep232019.csv'
DTO_OWL_FILE = '../data/UMiami/dto_proteome_classification_only.owl'
SRC_FILES = [os.path.basename(MAPPING_FILE),
             os.path.basename(CLASS_FILE),
             os.path.basename(DTO_OWL_FILE)]

def parse_dto_owl(args, fn):
  if not args['--quiet']:
    print "\nParsing Drug Target Ontology file {}".format(fn)
  dto = []
  dto_ont = pronto.Ontology(fn)
  for term in dto_ont:
    #if not term.id.startswith('DTO:'):
    #  continue
    init = {'dtoid': term.id, 'name': term.name}
    if term.parents:
      init['parent_id'] = term.parents[0].id
    if term.desc:
      defn = term.desc.decode()
      init['def'] = defn.lstrip('[').rstrip(']')
    dto.append(init)
  if not args['--quiet']:
    print "  Got {} DTO terms".format(len(dto))
  return dto

def load_ids_classifications(args, dba, logger, logfile):
  line_ct = slmf.wcl(MAPPING_FILE)
  if not args['--quiet']:
    print "\nProcessing {} lines in file {}".format(line_ct, MAPPING_FILE)
  logger.info("Processing {} input lines in file {}".format(line_ct, MAPPING_FILE))
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  up2dto = {}
  up2pid = {}
  ct = 0
  with open(MAPPING_FILE, 'rU') as csvfile:
    csvreader = csv.reader(csvfile)
    header = csvreader.next() # skip header line
    ct += 1
    upd_ct = 0
    notfnd = set()
    dba_err_ct = 0
    for row in csvreader:
      ct += 1
      dtoid = row[0]
      up = row[1]
      logger.info("Searching for UniProt: {}".format(up))
      targets = dba.find_targets({'uniprot': up})
      if not targets:
        notfnd.add(up)
        continue
      t = targets[0]
      pid = t['components']['protein'][0]['id']
      rv = dba.upd_protein(pid, 'dtoid', dtoid)
      if rv:
        upd_ct += 1
        up2dto[up] = dtoid
        up2pid[up] = pid
      else:
        dba_err_ct += 1
      pbar.update(ct)
  pbar.finish()
  for up in notfnd:
    logger.warn("No target found for UniProt: {}".format(up))
  print "{} lines processed.".format(ct)
  print "  Updated {} protein.dtoid values".format(upd_ct)
  print "Got {} UniProt to DTO mappings for TCRD targets".format(len(up2dto))
  print "Got {} UniProt to Protein ID mappings for TCRD targets".format(len(up2pid))
  if notfnd:
    print "WARNING: No target found for {} UniProts. See logfile {} for details.".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

  # Classifications
  line_ct = slmf.wcl(CLASS_FILE)
  if not args['--quiet']:
    print "\nProcessing {} lines in file {}".format(line_ct, CLASS_FILE)
  logger.info("Processing {} input lines in file {}".format(line_ct, CLASS_FILE))
  pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
  ct = 0
  dto_mark = {}
  with open(CLASS_FILE) as csvfile:
    csvreader = csv.reader(csvfile)
    header = csvreader.next() # skip header line
    ct += 1
    upd_ct = 0
    notfnd = set()
    dba_err_ct = 0
    for row in csvreader:
      ct += 1
      up = row[0]
      dto_class = row[1]
      if up not in up2pid:
        notfnd.add(up)
        continue
      pid = up2pid[up]
      rv = dba.upd_protein(pid, 'dtoclass', dto_class)
      if rv:
        upd_ct += 1
      else:
        dba_err_ct += 1
    pbar.update(ct)
  pbar.finish()
  for up in notfnd:
    logger.warn("UniProt {} not in map.".format(up))
  print "{} lines processed.".format(ct)
  print "  Updated {} protein.dtoclass values".format(upd_ct)
  if notfnd:
    print "WARNING: Got {} unmapped UniProts. See logfile {} for details.".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

def load_dto(args, dba, logfile, dto):
  if not args['--quiet']:
    print "Loading {} Drug Target Ontology terms".format(len(dto))
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=len(dto)).start()
  ct = 0
  dto_ct = 0
  dba_err_ct = 0
  for dtod in dto:
    ct += 1
    rv = dba.ins_dto(dtod)
    if rv:
      dto_ct += 1
    else:
      dba_err_ct += 1
    pbar.update(ct)
  pbar.finish()
  print "{} terms processed.".format(ct)
  print "  Inserted {} new dto rows".format(dto_ct)
  if dba_err_ct > 0:
    print "WARNNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

    
if __name__ == '__main__':
  print "\n%s (v%s) [%s]:\n" % (PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  debug = int(args['--debug'])
  if debug:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)

  if args['--logfile']:
    logfile =  args['--logfile']
  else:
    logfile = LOGFILE
  loglevel = int(args['--loglevel'])
  logger = logging.getLogger(__name__)
  logger.setLevel(loglevel)
  if not args['--debug']:
    logger.propagate = False # turns off console logging
  fh = logging.FileHandler(LOGFILE)
  fmtr = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
  fh.setFormatter(fmtr)
  logger.addHandler(fh)

  dba_params = {'dbhost': args['--dbhost'], 'dbname': args['--dbname'], 'logger_name': __name__}
  dba = DBAdaptor(dba_params)
  dbi = dba.get_dbinfo()
  logger.info("Connected to TCRD database {} (schema ver {}; data ver {})".format(args['--dbname'], dbi['schema_ver'], dbi['data_ver']))
  if not args['--quiet']:
    print "Connected to TCRD database {} (schema ver {}; data ver {})".format(args['--dbname'], dbi['schema_ver'], dbi['data_ver'])

  load_ids_classifications(args, dba, logger, logfile)
  dto = parse_dto_owl(args, DTO_OWL_FILE)
  load_dto(args, dba, logfile, dto)

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'Drug Target Ontology', 'source': 'Files %s from Schurer Group at UMiami'%(", ".join(SRC_FILES)), 'app': PROGRAM, 'app_version': __version__, 'url': 'http://drugtargetontology.org/'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'protein', 'column_name': 'dtoid'},
            {'dataset_id': dataset_id, 'table_name': 'protein', 'column_name': 'dtoclass'},
            {'dataset_id': dataset_id, 'table_name': 'dto'} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)
  
  print "\n%s: Done.\n" % PROGRAM
