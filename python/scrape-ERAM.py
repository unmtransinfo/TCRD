#!/usr/bin/env python
# Time-stamp: <2018-10-03 09:40:58 smathias>
"""Scrape eRAM web pages.

Usage:
    scrape-ERAM.py [--debug | --quiet] [--logfile=<file>] [--loglevel=<int>]
    scrape-ERAM.py -h | --help

Options:
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
__copyright__ = "Copyright 2018, Steve Mathias"
__license__ = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__ = "1.0"

import os,sys,time
from docopt import docopt
import obo
import string
import re
import urllib
import requests
from bs4 import BeautifulSoup
import shelve
from collections import defaultdict
from progressbar import *
import logging
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = 'tcrd5logs/'
LOGFILE = LOGDIR + '%s.log'%PROGRAM
DO_OBO_FILE = '../data/DiseaseOntology/doid.obo'
ERAM_GENE_DIR = '../data/eRAM/eRAM_Gene/'
GENE_FILENAMES = ['eRAM_Curated_Gene.txt', 'eRAM_Inferring_Gene.txt', 'eRAM_Text_Mined_Gene.txt']
ERAM_SHOW_BASE_URL = 'http://www.unimd.org/eram/Show.php?keyword='
ERAM_SEARCH_BASE_URL = 'http://www.unimd.org/eram/Search.php?keyword='
ERAM_SHELF_FILE = '../data/eRAM/eRAM.db'
PRINTABLE = set(string.printable)

def parse_do(f):
  do = {}
  with open(f, 'r') as fh:
    do_parser = obo.Parser(fh)
    for stanza in do_parser:
      do[stanza.tags['id'][0].value] = stanza.tags
  return do

def get_disease_names():
  disease_names = []
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=319).start()
  for i in range(1, 320):
    url = ERAM_SEARCH_BASE_URL + urllib.quote('%%') + '&page={}'.format(i)
    r = None
    attempts = 0
    while attempts <= 5:
      try:
        r = requests.get(url)
        break
      except:
        attempts += 1
        time.sleep(2)
    if not r.status_code or r.status_code != 200:
      print "[ERROR] Bad response for diseases page {}".format(i)
      return None
    soup = BeautifulSoup(r.text, 'html.parser')
    tds = soup.findAll('td', attrs={'width': '20%'})
    dtds = [td for td in tds if td.text == 'Disease']
    for dtd in dtds:
      disease_names.append(dtd.findNext('td').text)
    time.sleep(1)
    pbar.update(i)
  pbar.finish()
  return disease_names

def get_disease_names_files():
  disease_names = set()
  for fn in GENE_FILENAMES:
    ffn = ERAM_GENE_DIR + fn
    with open(ffn, 'r') as ifh:
      for line in ifh:
        if line.startswith('Disease'):
          continue
        data = line.split('\t')
        disease_names.add(data[0])
  return list(disease_names)

def get_eram_disease_page(dname):
  url = ERAM_SHOW_BASE_URL + urllib.quote(dname)
  r = None
  attempts = 0
  while attempts <= 5:
    try:
      r = requests.get(url)
      break
    except:
      attempts += 1
      time.sleep(2)
  if not r.status_code or r.status_code != 200:
    return None
  return r.text

def parse_eram_disease_page(html):
  info = {}
  soup = BeautifulSoup(html, 'html.parser')
  # DOIDs
  doids = []
  for a in soup.findAll('a', href=True):
    if a.text and a.text.startswith('DOID:'):
      doids.append(a.text)
  info['doids'] = doids
  # Comorbidities
  coms = []
  srcsre = re.compile(r'\s+(.*?)<br\/>')
  ths = soup.findAll('th', attrs={'width': '20%'})
  comth = None
  for th in ths:
    if th.text == 'Comorbidity':
      comth = th
      break
  if comth:
    comr = comth.parent
    # Comorbidity row has pairs of links like so:
    # <a href="https://vsearch.nlm.nih.gov/vivisimo/cgi-bin/query-meta?query=pyoderma" target="_blank">C0034212</a>
    # <a href="Show5.php?td=incontinentia pigmenti&amp;tp=pyoderma&amp;tn=C0034212" target="_blank">pyoderma</a>
    # so find all a and iterate through them 2 at a time
    all_as = comr.findAll('a')
    for x, y in zip(*[iter(all_as)]*2):
      cui = x.text
      dis = y.text
      coms.append( {'UMLS CUI': cui, 'Disease': dis} )
    info['comorbidities'] = coms
  # Curated Genes
  cgs = []
  cgth = None
  for th in ths:
    if th.text == 'Curated Gene':
      cgth = th
      break
  if cgth:
    cgr = cgth.parent
    # parse this the same as comorbidities, except we get Gene IDs and symbols
    all_as  = cgr.findAll('a')
    for x, y in zip(*[iter(all_as)]*2):
      geneid = x.text
      sym = y.text
      cgs.append( {'geneid': geneid, 'sym': sym} )
    # Now pull out Sources that go with each gene and add them to the cgs dict
    if cgr.findAll('div'):
      cgdiv = cgr.findAll('div')[-1]
      cgtxts = re.findall(srcsre, str(cgdiv))
      for i, cgtxt in enumerate(cgtxts):
        srcs = filter(lambda x: x in PRINTABLE, cgtxt).split('|')[-1]
        srcs = srcs.replace(';', '|')
        cgs[i]['sources'] = srcs
      info['currated_genes'] = cgs
    else:
      info['currated_genes'] = []
  return info
  
if __name__ == '__main__':
  print "\n{} (v{}) [{}]:".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
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

  start_time = time.time()
  s = shelve.open(ERAM_SHELF_FILE, writeback=True)
  
  #print "\nParsing Disease Ontology file {}".format(DOWNLOAD_DIR + FILENAME)
  #do = parse_do(DO_OBO_FILE)
  #print "  Got {} Disease Ontology terms".format(len(do))

  #dnames = get_unique_disease_names_files()
  #print "\nGot {} unique disease names from download files in {}".format(len(dnames), ERAM_GENE_DIR)
  if 'disease_names' in s:
    dnames = s['disease_names']
    print "\nGot {} eRAM disease names from shelf file {}".format(len(dnames), ERAM_SHELF_FILE)
  else:
    print "\nScraping eRAM for disease names..."
    dnames = get_disease_names()
    print "Got {}".format(len(dnames))
    s['disease_names'] = dnames

  #dnames = ['incontinentia pigmenti', 'gaucher disease']
  print "\nScraping eRAM info for {} diseases...".format(len(dnames))
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=len(dnames)).start()
  ct = 0
  name_err_ct = 0
  for dname in dnames:
    ct += 1
    try:
      dname = str(dname)
    except:
      name_err_ct += 1
      continue
    if dname in s:
      logger.info("Already processed {}".format(dname))
      continue
    logger.info("Processing {}".format(dname))
    html = get_eram_disease_page(dname)
    if not html:
      logger.error("[ERROR] Bad response for disease page {}".format(dname))
      continue
    eram_info = parse_eram_disease_page(html)
    logger.debug("Info:")
    for it in eram_info.keys():
      logger.debug("  {}: {}".format(it, eram_info[it]))
    s[dname] = eram_info
    time.sleep(1)
    pbar.update(ct)
  pbar.finish()
  print "Processed {} diseases. {} name errors.".format(ct, name_err_ct)

  s.close()
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))
