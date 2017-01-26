#!/usr/bin/env python
# Time-stamp: <2017-01-13 11:26:09 smathias>
"""Load TechDev reporting data into TCRD from CSV files.

Usage:
    load-TechDevInfo.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-TechDevInfo.py -? | --help

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
__copyright__ = "Copyright 2016-2017, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.0.0"

import os,sys,time
from docopt import docopt
from TCRD import DBAdaptor
import csv
import logging
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
INPUTFILES = {1: '../data/TechDev/TechDev1_IDG_20160610_Johnson.csv',
              2: '../data/TechDev/TechDev2_IDG_20160610_Roth.csv',
              3: '../data/TechDev/TechDev3_IDG_20160610_Yeh.csv',
              4: '../data/TechDev/TechDev4_IDG_20160610_McManus.csv',
              5: '../data/TechDev/TechDev5_IDG_20160610_Tomita.csv',
              6: '../data/TechDev/TechDev6_IDG_20160610_Finkbeiner.csv',
              7: '../data/TechDev/TechDev7_IDG_20160610_Qin_Baylor.csv',
              }
PIS = {1: 'Gary Johnson',
       2: 'Bryan Roth',
       3: 'Jing-Ruey Yeh',
       4: 'Michael McManus',
       5: 'Susumu Tomita',
       6: 'Steve Finkbeiner',
       7: 'Jun Qin'}

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
    print "Connected to TCRD database %s (schema ver %s; data ver %s)" % (args['--dbname'], dbi['schema_ver'], dbi['data_ver'])

  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'TechDev Worklist Info', 'source': 'Files from TechDev Groups', 'app': PROGRAM, 'app_version': __version__, 'comments': 'Loading app uses data from spreadsheets submitted by the TechDev groups listing targets being investigated.'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  provs = [ {'dataset_id': dataset_id, 'table_name': 'techdev_contact', 'comment': ""},
            {'dataset_id': dataset_id, 'table_name': 'techdev_info', 'comment': ""} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    if not rv:
      print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
      sys.exit(1)
    
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]

  for tdid,filename in INPUTFILES.items():
    line_ct = wcl(filename)
    if not args['--quiet']:
      print '\nProcessing %d lines from input file: %s' % (line_ct, filename)
    with open(filename, 'rU') as csvfile:
      csvreader = csv.reader(csvfile)
      pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start()
      ct = 0
      contact = {}
      skip_ct = 0
      err_ct = 0
      info_ct = 0
      notfnd = []
      dba_err_ct = 0
      for row in csvreader:
        ct += 1
        if row[0] == 'TechDev ID:':
          techdev_id = int(row[1])
          contact['id'] = techdev_id
          continue
        if row[0] == 'Grant Number:':
          contact['grant_number'] = row[1]
          continue
        if row[0] == 'Submitter name:':
          contact['contact_name'] = row[1]
          continue
        if row[0] == 'Contact email:':
          contact['contact_email'] = row[1]
          continue
        if row[0] == 'Submission date:':
          contact['date'] = row[1]
          continue
        if row[0] == 'tcrd_target_id':
          contact['pi'] = PIS[techdev_id]
          contact_id = dba.ins_techdev_contact(contact)
          if not contact_id:
            logger.error("DBA error inserting techdev_contact.")
            print "Exiting due to DBA error inserting techdev_contact. See logfile %s for details." % logfile
            break
          continue
        if not row[6]:
          skip_ct += 1
          continue
        sym = row[1]
        targets = dba.find_targets({'sym': sym})
        if not targets:
          notfnd.append(sym)
          continue
        t = targets[0]
        pid = t['components']['protein'][0]['id']
        init = {'contact_id': contact_id, 'protein_id': pid}
        if not row[7]:
          err_ct  += 1
          continue
        init['comment'] = row[7]
        if row[8]:
          init['publication_pcmid'] = row[8]
        if row[9]:
          init['publication_pmid'] = row[9]
        if row[11]:
          init['resource_url'] = row[11]
        if row[10]:
          init['data_url'] = row[10]
        rv = dba.ins_techdev_info(init)
        if rv:
          info_ct += 1
        else:
          dba_err_ct += 1
        pbar.update(ct)
    pbar.finish()
    if not args['--quiet']:
      print "%d lines processed." % ct
      print "  Skipped %d lines not under investigation" % skip_ct
      if err_ct > 0:
        print "  WARNING: %d lines did not have a comment!" % err_ct
      if notfnd:
        print "  WARNING: %d symbols did not find a target!"
        for sym in notfnd:
          print "    %s" % sym
      print "  Inserted 1 new techdev_contact row"
      print "  Inserted %d new techdev_info rows" % info_ct
      if dba_err_ct > 0:
        print "WARNING: %d DB errors occurred. See logfile %s for details." % (dba_err_ct, logfile)


def wcl(fname):
  with open(fname) as f:
    for i, l in enumerate(f):
      pass
  return i + 1

def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])

if __name__ == '__main__':
  print "\n%s (v%s) [%s]:\n" % (PROGRAM, __version__, time.strftime("%c"))
  start_time = time.time()
  load()
  elapsed = time.time() - start_time
  print "\n%s: Done. Elapsed time: %s\n" % (PROGRAM, secs2str(elapsed))

