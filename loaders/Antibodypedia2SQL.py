#!/usr/bin/env python
# Time-stamp: <2016-11-16 16:23:40 smathias>
"""Query Antibodtpedia.com API and write SQL file to insert antibody count and URL tdl_infos into TCRD.

Usage:
    Antibodtpedia2SQL.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    Antibodtpedia2SQL.py | --help

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
import httplib2
import json
import logging
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
DBHOST = 'localhost'
DBPORT = 3306
DBNAME = 'tcrd4'
LOGFILE = './%s.log'%PROGRAM
ABPC_API_URL = 'http://www.antibodypedia.com/tools/antibodies.php?uniprot='
SQL_FILE = '../SQL/InsAbCts_v4.sql'

def main():
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
  
  start_time = time.time()
  http = httplib2.Http(".%s_cache"%PROGRAM)
  f = open(SQL_FILE, 'w')
  tct = dba.get_target_count(idg=False)
  if not args['--quiet']:
    print "\n%s (v%s): Getting Ab Counts and URL for %d TCRD targets" % (PROGRAM, __version__, tct)
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=tct).start() 
  ct = 0
  tiab_ct = 0
  timab_ct = 0
  tiurl_ct = 0
  net_err_ct = 0
  for target in dba.get_targets():
    ct += 1
    tid = target['id']
    pid = target['components']['protein'][0]['id']
    up = target['components']['protein'][0]['uniprot']
    url = ABPC_API_URL + up
    resp = None
    content = ''
    while resp == None:
      try:
        resp, content = http.request(url, 'GET', headers={'Accept': 'application/json'})
      except:
        pass
    time.sleep(1)
    if resp['status'] != '200':
      net_err_ct += 1
      status200s[tid] = {'uniprot': up, 'protein_id': pid}
      continue
    abpd = json.loads(content)
    # Write SQL to insert new Ab Count and MAb Count tdl_infos
    f.write( "INSERT INTO tdl_info (protein_id, itype, integer_value) VALUES (%d, 'Ab Count', %d);\n"%(pid, int(abpd['num_antibodies'])) )
    tiab_ct += 1
    if 'ab_type_monoclonal' in abpd:
      mab_ct = int(abpd['ab_type_monoclonal'])
    else:
      mab_ct = 0
    f.write( "INSERT INTO tdl_info (protein_id, itype, integer_value) VALUES (%d, 'MAb Count', %d);\n"%(pid, mab_ct) )
    timab_ct += 1
    # Write SQL to insert new Antibodypedia URL tdl_infos
    f.write( "INSERT INTO tdl_info (protein_id, itype, string_value) VALUES (%d, 'Antibodypedia.com URL', '%s');\n"%(pid, (abpd['url'])) )
    tiurl_ct += 1
    time.sleep(1)
    pbar.update(ct)
  pbar.finish()

  f.close()
  
  elapsed = time.time() - start_time
  print "%d TCRD targets processed. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "Wrote SQL inserts to file %s:" % SQL_FILE
  print "  %d Ab Count tdl_infos" % tiab_ct
  print "  %d MAb Count tdl_infos" % timab_ct
  print "  %d Antibodypedia URL tdl_infos" % tiurl_ct
  if net_err_ct > 0:
    print "WARNING: status 200 for %d targets:" % net_err_ct
    for tid in status200s.keys():
      print "Target %d (%s): %s" % (tid, status200s[tid]['uniprot'], status200s[tid]['status'])

  print "\n%s: Done.\n" % PROGRAM

def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])

if __name__ == '__main__':
    main()
