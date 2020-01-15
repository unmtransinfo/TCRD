#!/usr/bin/env python3
# Time-stamp: <2019-01-16 17:04:14 smathias>
"""Process Disease Ontology OBO OWL file and generate TSV for loading into TCRD.

Usage:
    process-DO.py [--debug | --quiet] 
    process-DO.py -h | --help

Options:
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
from owlready2 import *
from requests import get
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
DOWNLOAD_DIR = '../data/DiseaseOntology/'
BASE_URL = 'http://purl.obolibrary.org/obo/'
FILENAME = 'doid.owl'

def download(args):
  url = BASE_URL + FILENAME
  fn = DOWNLOAD_DIR + FILENAME
  if os.path.exists(fn):
    os.remove(fn)
  if not args['--quiet']:
    print("\nDownloading ", url)
    print("         to ", fn)
  response = get(url)
  if response.status_code != 200:
    return
  with open(fn, "wb") as ofh:
    ofh.write(response.content)
  if not args['--quiet']:
    print("Done.")

def main(args):
  fn = DOWNLOAD_DIR + FILENAME
  if not args['--quiet']:
    print("\nLoading Disease Ontology from file {}".format(fn))
  onto = get_ontology(fn)
  onto.load()
  class_list = list(onto.classes())


  
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  if not args['--quiet']:
    print "\nLoading {} Disease Ontology terms".format(len(do))
  pbar = ProgressBar(widgets=pbar_widgets, maxval=len(do)).start()
  ct = 0
  do_ct = 0
  skip_ct = 0
  obs_ct = 0
  dba_err_ct = 0
  for doid,dod in do.items():
    ct += 1
    if not doid.startswith('DOID:'):
      skip_ct += 1
      continue
    if 'is_obsolete' in dod:
      obs_ct += 1
      continue
    init = {'id': doid, 'name': dod['name'][0].value}
    if 'def' in dod:
      init['def'] = dod['def'][0].value
    if 'is_a' in dod:
      init['parents'] = []
      for parent in dod['is_a']:
        init['parents'].append(parent.value)
    rv = dba.ins_do(init)
    if rv:
      do_ct += 1
    else:
      dba_err_ct += 1
    pbar.update(ct)
  pbar.finish()
  print "{} terms processed.".format(ct)
  print "  Inserted {} new do rows".format(do_ct)
  print "  Skipped {} non-DOID terms".format(skip_ct)
  print "  Skipped {} obsolete terms".format(obs_ct)
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
