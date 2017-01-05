#!/usr/bin/env python
# Time-stamp: <2016-12-01 12:18:00 smathias>
'''
pickle-IDGFams.py - Create a pickle file containing IDG family sym/geneids/uniprots
'''
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2014-2015, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "1.4.0"

import os,sys,argparse,time
from TCRD import DBAdaptor
import httplib2
import json
import logging
import cPickle as pickle
import pprint
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
DBHOST = 'localhost'
DBPORT = 3306
DBNAME = 'tcrd'

def main():
  argparser = argparse.ArgumentParser(description="Create a pickle file containing IDG family geneids/uniprots")
  group = argparser.add_mutually_exclusive_group()
  group.add_argument("-v", "--verbose", action='count', default=0,
                     help="Set output verbosity level")
  group.add_argument("-q", "--quiet", action="store_true")
  argparser.add_argument('-dh', '--dbhost', help='Database host.', default=DBHOST)
  argparser.add_argument('-db', '--dbname', help='Database name.', default=DBNAME)
  argparser.add_argument('-o', '--outfile', help='Database name.')
  args = argparser.parse_args()

  dba_params = {'dbhost': args.dbhost, 'dbname': args.dbname}
  dba = DBAdaptor(dba_params)
  dbi = dba.get_dbinfo()
  tct = dba.get_target_count(idg=True)
  if not args.quiet:
    print "\n%s (v%s) [%s]:" % (PROGRAM, __version__, time.strftime("%c"))
    print "  Connected to TCRD database %s (schema ver: %s, data ver: %s)" % (args.dbname, dbi['schema_ver'], dbi['data_ver'])
    print "  Dumping TCRD IDG Families for %d targets" % tct
  start_time = time.time()
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=tct).start() 
  idgs = {'GPCR': [], 'oGPCR': [], 'Kinase': [], 'IC': [], 'NR': []}
  ct = 0
  for t in dba.get_targets(idg=True, include_annotations=False):
    ct += 1
    p = t['components']['protein'][0]
    idg = t['idgfam']
    idgs[idg].append( {'sym': p['sym'], 'geneid': p['geneid'], 'uniprot': p['uniprot']} )
    pbar.update(ct)
  pbar.finish()
  
  elapsed = time.time() - start_time
  print "%d TCRD targets processed. Elapsed time: %s" % (ct, secs2str(elapsed))
  print "Saving info for following IDG Family counts to pickle file %s" % args.outfile
  for idgfam in idgs.keys():
    print "  %s: %d" % (idgfam, len(idgs[idgfam]))
  pickle.dump(idgs, open(args.outfile, 'wb'))
  
  print "\n%s: Done.\n" % PROGRAM
  

def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])

if __name__ == '__main__':
    main()
