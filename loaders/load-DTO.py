#!/usr/bin/env python
# Time-stamp: <2017-01-11 12:20:22 smathias>
"""Load DTO IDs and classifications into TCRD from TSV file.

Usage:
    load-DTO.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
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
  -d --debug DEBUGL    : set debugging output level (0-3) [default: 0]
  -? --help            : print this message and exit 
"""
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2015-2017, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.0.0"

import os,sys,time,re
from docopt import docopt
from TCRD import DBAdaptor
import csv
import json
import logging
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
DTO2UP_FILE = '../data/UMiami/UniPids_DTOids2.csv'
DTO_FILE = '../data/UMiami/dto.json'
SRC_FILES = [os.path.basename(DTO2UP_FILE),
             os.path.basename(DTO_FILE)]
classifications = {}

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
  dataset_id = dba.ins_dataset( {'name': 'Drug Target Ontology', 'source': 'Files %s from Schurer Group'%(", ".join(SRC_FILES)), 'app': PROGRAM, 'app_version': __version__, 'url': 'http://drugtargetontology.org/'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'protein', 'column_name': 'dtoid'},
            {'dataset_id': dataset_id, 'table_name': 'dto'} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    if not rv:
      print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
      sys.exit(1)

  start_time = time.time()
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  line_ct = wcl(DTO2UP_FILE)
  line_ct -= 1
  if not args['--quiet']:
    print "\nProcessing %d input lines in file %s" % (line_ct, DTO2UP_FILE)
  logger.info("Processing %d input lines in file %s" % (line_ct, DTO2UP_FILE))
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
      logger.info("Searching for UniProt: %s" % up)
      targets = dba.find_targets({'uniprot': up})
      if not targets:
        notfnd.append(up)
        logger.warn("No target found for UniProt: %s" % up)        
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
  elapsed = time.time() - start_time
  print "%d input lines processed. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "  Updated %d protein.dtoid values" % upd_ct
  print "%d DTO to UniProt mappings for TCRD targets" % len(dto2up.keys())
  print "%d UniProt to DTO mappings for TCRD targets" % len(up2dto.keys())
  if notfnd:
    print "WARNING: No target found for %d UniProts. See logfile %s for details." % (len(notfnd), logfile)
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)

  # Classifications
  global classifications
  if not args['--quiet']:
    print "\nParsing DTO JSON file %s" % DTO_FILE
  logger.info("Parsing DTO JSON file %s" % DTO_FILE)
  with open(DTO_FILE) as json_file:
    jsondata = json.load(json_file)
    # get the Protein section of DTO:
    dtop = [d for d in jsondata['children'] if d['name'] == 'Protein'][0]
    for fd in dtop['children']:
      fam = "%s~%s" % (fd['id'],fd['name'])
      walk_dto(fam, fd['children'])
  print "Got %d classifications." % len(classifications.keys())

  start_time = time.time()
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  cct = len(classifications.keys())
  if not args['--quiet']:
    print "\nLoading %d classifications" % cct
  logger.info("Processing %d classifications" % cct)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=cct).start()
  ct = 0
  dto_mark = {}
  dba_err_ct = 0
  for classification,inlist in classifications.items():
    ct += 1
    logger.info("Processing '%s' with %d term(s)" % (classification, len(inlist)))
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
      logger.info("Inserting dto (%s, %s, %s)" % (dtoid, dtoname, lpp))
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
  elapsed = time.time() - start_time
  print "%d classifications processed. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "Inserted %d new dto rows" % len(dto_mark.keys())
  if dba_err_ct > 0:
    print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)


def wcl(fname):
  with open(fname) as f:
    for i, l in enumerate(f):
      pass
  return i + 1

def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])

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
  print "\n%s (v%s) [%s]:" % (PROGRAM, __version__, time.strftime("%c"))
  load()
  print "\n%s: Done.\n" % PROGRAM
