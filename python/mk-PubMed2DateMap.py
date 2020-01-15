#!/usr/bin/env python
"""Map all TCRD GeneRIF PubMed IDs to years.

Usage:
    mk-PubMed2DateMap.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>] [--pastid=<int>]
    mk-PubMed2DateMap.py -h | --help

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
  -d --debug           : turn on debugging output
  -? --help            : print this message and exit 
"""
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2017-2019, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.0.0"

import os,sys,time,re
from docopt import docopt
from TCRDMP import DBAdaptor
import logging
from progressbar import *
import urllib
import requests
from bs4 import BeautifulSoup
import calendar
import cPickle as pickle
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "../loaders/tcrd6logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
EMAIL = 'smathias@salud.unm.edu'
EFETCHURL = "http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?&db=pubmed&retmode=xml&email=%s&tool=%s&id=" % (urllib.quote(EMAIL), urllib.quote(PROGRAM))
PICKLE_FILE = '../data/TCRDv6_PubMed2Date.p'

def main(args):
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
  
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  
  generifs = dba.get_generifs()
  if not args['--quiet']:
    print "\nProcessing {} GeneRIFs".format(len(generifs))
  logger.info("Processing {} GeneRIFs".format(len(generifs)))
  pbar = ProgressBar(widgets=pbar_widgets, maxval=len(generifs)).start()
  yrre = re.compile(r'^(\d{4})')
  ct = 0
  yr_ct = 0
  skip_ct = 0
  net_err_ct = 0
  pubmed2date = {}
  missing_pmids = set()
  for generif in generifs:
    ct += 1
    pbar.update(ct)
    for pmid in generif['pubmed_ids'].split("|"):
      if pmid in pubmed2date:
        continue
      # See if this PubMed is in TCRD...
      pm = dba.get_pubmed(pmid)
      if pm:
        # if so get date from there
        if pm['date']:
          pubmed2date[pmid] = pm['date']
      else:
        # if not, will have to get it via EUtils
        missing_pmids.add(pmid)
  pbar.finish()
  if not args['--quiet']:
    print "{} GeneRIFs processed.".format(ct)
    in_tcrd_ct = len(pubmed2date)
    print "Got date mapping for {} PubMeds in TCRD".format(in_tcrd_ct)

  if not args['--quiet']:
    print "\nGetting {} missing PubMeds from E-Utils".format(len(missing_pmids))
  logger.debug("Getting {} missing PubMeds from E-Utils".format(len(missing_pmids)))
  chunk_ct = 0
  err_ct = 0
  no_date_ct = 0
  pmids = list(missing_pmids)
  for chunk in chunker(pmids, 200):
    chunk_ct += 1
    if not args['--quiet']:
      print "  Processing chunk {}".format(chunk_ct)
    logger.debug("Chunk {}: {}".format(chunk_ct, chunk))
    r = get_pubmed(chunk)
    if not r or r.status_code != 200:
      # try again...
      r = get_pubmed(pmid)
      if not r or r.status_code != 200:
        logger.error("Bad E-Utils response for PubMed ID {}".format(pmid))
        net_err_ct += 1
        continue
    soup = BeautifulSoup(r.text, "xml")
    pmas = soup.find('PubmedArticleSet')
    for pma in pmas.findAll('PubmedArticle'):
      pmid = pma.find('PMID').text
      date = get_pubmed_article_date(pma)
      if date:
        pubmed2date[pmid] = date
      else:
        no_date_ct += 1
  elapsed = time.time() - start_time
  if not args['--quiet']:
    print "{} PubMed IDs processed.".format(ct)
    print "Got date mapping for {} PubMeds not in TCRD".format(len(pubmed2date) - in_tcrd_ct)
    print "No date for {} PubMeds".format(no_date_ct)
  if net_err_ct > 0:
    print "WARNING: {} Network/E-Utils errors occurred. See logfile {} for details.".format(net_err_ct, logfile)
  if not args['--quiet']:
    print "Dumping map to file: {}".format(PICKLE_FILE)
  pickle.dump(pubmed2date, open(PICKLE_FILE, 'wb'))
  
def chunker(l, size):
  return (l[pos:pos+size] for pos in xrange(0, len(l), size))

def get_pubmed(pmids):
  url = EFETCHURL + ','.join(pmids)
  attempts = 0
  r = None
  while attempts <= 5:
    try:
      r = requests.get(url)
      break
    except:
      attempts += 1
      time.sleep(1)
  if r:
    return r
  else:
    return False

def get_pubmed_article_date(pma):
  """
  Parse a BeautifulSoup PubmedArticle and return the publication date of the article.
  """
  article = pma.find('Article')
  journal = article.find('Journal')
  pd = journal.find('PubDate')
  if pd:
    year = pubdate2isostr(pd)
  if year:
    return year
  else:
    return None

# map abbreviated month names to ints
months_rdict = {v: str(i) for i,v in enumerate(calendar.month_abbr)}
mld_regex = re.compile(r'(\d{4}) (\w{3}) (\d\d?)-')

def pubdate2isostr(pubdate):
  """Turn a PubDate XML element into an ISO-type string (ie. YYYY-MM-DD)."""
  if pubdate.find('MedlineDate'):
    mld = pubdate.find('MedlineDate').text
    m = mld_regex.search(mld)
    if not m:
      return None
    month = months_rdict.get(m.groups(1), None)
    if not month:
      return m.groups()[0]
    return "%s-%s-%s" % (m.groups()[0], month, m.groups()[2])
  else:
    year = pubdate.find('Year').text
    if not pubdate.find('Month'):
      return year
    month = pubdate.find('Month').text
    if not month.isdigit():
      month = months_rdict.get(month, None)
      if not month:
        return year
    if pubdate.find('Day'):
      day = pubdate.find('Day').text
      return "%s-%s-%s" % (year, month.zfill(2), day.zfill(2))
    else:
      return "%s-%s" % (year, month.zfill(2))


if __name__ == '__main__':
  print "\n{} (v{}) [{}]:".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  start_time = time.time()
  main(args)
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))

