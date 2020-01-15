#!/usr/bin/env python
# Time-stamp: <2019-09-11 10:45:00 smathias>
"""Load DTO IDs and classifications into TCRD from TSV file.

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
__copyright__ = "Copyright 2015-2019, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "3.0.0"

import os,sys,time,re
from docopt import docopt
from TCRDMP import DBAdaptor
import csv
import json
import logging
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = 'tcrd6logs/'
LOGFILE = LOGDIR + '%s.log'%PROGRAM
DTO2UP_FILE = '../data/UMiami/UniPids_DTOids2.csv'
DTO_FILE = '../data/UMiami/dto.json'
SRC_FILES = [os.path.basename(DTO2UP_FILE),
             os.path.basename(DTO_FILE)]
classifications = {}

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
  dataset_id = dba.ins_dataset( {'name': 'Drug Target Ontology', 'source': 'Files %s from Schurer Group'%(", ".join(SRC_FILES)), 'app': PROGRAM, 'app_version': __version__, 'url': 'http://drugtargetontology.org/'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'protein', 'column_name': 'dtoid'},
            {'dataset_id': dataset_id, 'table_name': 'dto'} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  
  line_ct = slmf.wcl(DTO2UP_FILE)
  line_ct -= 1
  if not args['--quiet']:
    print "\nProcessing {} lines in file {}".format(line_ct, DTO2UP_FILE)
  logger.info("Processing {} input lines in file {}".format(line_ct, DTO2UP_FILE))
  dto2up = {}
  up2dto = {}
  with open(DTO2UP_FILE, 'rU') as csvfile:
    csvreader = csv.reader(csvfile)
    header = csvreader.next() # skip header line
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    ct = 0
    upd_ct = 0
    notfnd = []
    dba_err_ct = 0
    for row in csvreader:
      ct += 1
      if row[2].endswith('gene'):
        continue # only use DTO IDs from protein branch
      dtoid = row[0]
      up = row[1]
      logger.info("Searching for UniProt: {}".format(up))
      targets = dba.find_targets({'uniprot': up})
      if not targets:
        notfnd.append(up)
        logger.warn("No target found for UniProt: {}".format(up))        
        continue
      t = targets[0]
      pid = t['components']['protein'][0]['id']
      rv = dba.upd_protein(pid, 'dtoid', dtoid)
      if rv:
        upd_ct += 1
        dto2up[dtoid] = up
        up2dto[up] = dtoid
      else:
        dba_err_ct += 1
      pbar.update(ct)
  pbar.finish()
  print "{} lines processed.".format(ct)
  print "  Updated {} protein.dtoid values".format(upd_ct)
  print "{} DTO to UniProt mappings for TCRD targets".format(len(dto2up))
  print "{} UniProt to DTO mappings for TCRD targets".format(len(up2dto))
  if notfnd:
    print "WARNING: No target found for {} UniProts. See logfile {} for details.".format(len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

  # Classifications
  global classifications
  if not args['--quiet']:
    print "\nParsing DTO JSON file {}".format(DTO_FILE)
  logger.info("Parsing DTO JSON file {}".format(DTO_FILE))
  with open(DTO_FILE) as json_file:
    jsondata = json.load(json_file)
    # get the Protein section of DTO:
    dtop = [d for d in jsondata['children'] if d['name'] == 'Protein'][0]
    for fd in dtop['children']:
      fam = "%s~%s" % (fd['id'],fd['name'])
      walk_dto(fam, fd['children'])
  print "Got {} classifications.".format(len(classifications))

  cct = len(classifications)
  if not args['--quiet']:
    print "\nLoading {} classifications".format(cct)
  logger.info("Processing {} classifications".format(cct))
  pbar = ProgressBar(widgets=pbar_widgets, maxval=cct).start()
  ct = 0
  dto_mark = {}
  dba_err_ct = 0
  for classification,inlist in classifications.items():
    ct += 1
    logger.info("Processing '{}' with {} term(s)".format(classification, len(inlist)))
    # make sure all parent terms in the classification are loaded
    rclass = list(reversed(classification.split("|")))
    for i,idname in enumerate(rclass):
      [dtoid,dtoname] = idname.split("~")
      if i == 0:
        leaf_term_parent_id = dtoid
      if dtoid in dto_mark:
        # term has already been inserted
        continue
      # look up id of parent term, if there is one
      parent_id = None
      if i == len(rclass)-1:
        lpp = ''
      else:
        parent_idname = rclass[i+1]
        [parent_dtoid,parent_dtoname] = parent_idname.split("~")
        lpp = parent_dtoid
      logger.info("Inserting dto ({}, {}, {})".format(dtoid, dtoname, lpp))
      rv = dba.ins_dto({'id': dtoid, 'name': dtoname, 'parent': parent_dtoid})
      if rv:
        dto_mark[dtoid] = True # save so we don't try to insert the same term twice
      else:
        dba_err_ct += 1
    # load leaf terms
    for idname in inlist:
      [dtoid,dtoname] = idname.split("~")
      rv = dba.ins_dto({'id': dtoid, 'name': dtoname, 'parent': leaf_term_parent_id})
      if rv:
        dto_mark[dtoid] = True
      else:
        dba_err_ct += 1
    pbar.update(ct)
  pbar.finish()
  print "{} classifications processed.".format(ct)
  print "Inserted {} new dto rows".format(len(dto_mark))
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

def walk_dto(myclass, l):
  global classifications
  for d in l:
    if d['children']:
      child_class = myclass + '|' + "%s~%s"%(d['id'],d['name'])
      walk_dto(child_class, d['children'])
    else:
      if myclass in classifications:
        classifications[myclass].append("%s~%s" % (d['id'],d['name']))
      else:
        classifications[myclass] = ["%s~%s" % (d['id'],d['name'])]


if __name__ == '__main__':
  print "\n{} (v{}) [{}]:".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  start_time = time.time()
  load(args)
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))
