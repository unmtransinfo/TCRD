#!/usr/bin/env python
# Time-stamp: <2019-12-18 11:33:42 smathias>
"""Download ClinVar variant_summary.txt and process for loading into TCRD.

Usage:
    process-ClinVar.py [--debug=<int> | --quiet]
    process-ClinVar.py -? | --help

Options:
  -q --quiet           : set output verbosity to minimal level
  -d --debug DEBUGL    : set debugging output level (0-3) [default: 0]
  -? --help            : print this message and exit 
"""
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2018-2019, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "1.0.0"

import os,sys,time
from docopt import docopt
import urllib
import numpy as np
import pandas as pd
import gzip
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
DOWNLOAD_DIR = '../data/ClinVar/'
BASE_URL = 'ftp://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/'
FILENAME = 'variant_summary.txt.gz'
OUTFILE = 'ClinVar_Phenotypes.csv'

def download(args):
  gzfn = DOWNLOAD_DIR + FILENAME
  if os.path.exists(gzfn):
    os.remove(gzfn)
  fn = gzfn.replace('.gz', '')
  if os.path.exists(fn):
    os.remove(fn)
  start_time = time.time()
  if not args['--quiet']:
    print "Downloading ", BASE_URL + FILENAME
    print "         to ", gzfn
  urllib.urlretrieve(BASE_URL + FILENAME, gzfn)
  if not args['--quiet']:
    print "Uncompressing", gzfn
  ifh = gzip.open(gzfn, 'rb')
  ofh = open(fn, 'wb')
  ofh.write( ifh.read() )
  ifh.close()
  ofh.close()
  if not args['--quiet']:
    elapsed = time.time() - start_time
    print "Done. Elapsed time: %s" % slmf.secs2str(elapsed)

def process(args):
  varfile = "%s/%s" % (DOWNLOAD_DIR, FILENAME)
  varfile = varfile.replace('.gz', '')
  df = pd.read_csv(varfile, sep='\t')
  if not args['--quiet']:
    print "\nProcessing %d rows from variant file %s" % (df.shape[0], varfile)
  # filter for the rows we want
  # ie. with good review status
  df = df.loc[df['ReviewStatus'].isin(['reviewed by expert panel', 'criteria provided, multiple submitters, no conflicts'])]
  # filter for columns we want
  df = df[['GeneSymbol', 'GeneID', 'PhenotypeList', 'PhenotypeIDS']]
  if not args['--quiet']:
    print "  Got %d unique rows with good review status" % df.shape[0]
  
  if not args['--quiet']:
    print "\nBuilding gene-phenotype mappings" % 
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=df2.shape[0]).start()
  s2p = list()
  for i,idx in enumerate(df.index):
    sym = df.ix[idx, 'GeneSymbol']
    geneid = df.ix[idx, 'GeneID']
    pt_names = df.ix[idx, 'PhenotypeList'].split(';')
    pt_ids = df.ix[idx, 'PhenotypeIDS'].split(';')
    for i,name in enumerate(pt_names):
      if name in ['not provided', 'not specified']:
        continue
      ids = pt_ids[i].replace(',', '|')
      s2p.append([sym, geneid, name, ids])
    pbar.update(i+1)
  pbar.finish()
  tmp_df = pd.DataFrame(s2p,
                        columns=['GeneSymbol', 'GeneID', 'Phenotype', 'PhenotypeID'])
  sym2pts = tmp_df.drop_duplicates()
  if not args['--quiet']:
    print "  Got %d unique mappings" % sym2pts.shape[0]
    
  if not args['--quiet']:
    print "\nWriting %d gene-phenotype mappings to file %s" % (sym2pts.shape[0], OUTFILE)
  sym2pts.to_csv(OUTFILE)
    
if __name__ == '__main__':
  print "\n%s (v%s) [%s]:\n" % (PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  debug = int(args['--debug'])
  if debug:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  #download(args)
  process(args)
  print "\n%s: Done.\n" % PROGRAM
