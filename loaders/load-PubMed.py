#!/usr/bin/env python
"""Load PubMed data into TCRD via EUtils.

Usage:
    load-PubMed.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>] [--pastid=<int>]
    load-PubMed.py -h | --help

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
  -p --pastid PASTID   : TCRD target id to start at (for restarting frozen run)
  -q --quiet           : set output verbosity to minimal level
  -d --debug           : turn on debugging output
  -? --help            : print this message and exit 
"""
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2015-2018, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.1.0"

import os,sys,time,urllib,re
from docopt import docopt
from TCRD import DBAdaptor
import logging
from progressbar import *
import requests
from bs4 import BeautifulSoup
import shelve
from collections import defaultdict
import calendar
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd5logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)
EMAIL = 'smathias@salud.unm.edu'
EFETCHURL = "http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?&db=pubmed&retmode=xml&email=%s&tool=%s&id=" % (urllib.quote(EMAIL), urllib.quote(PROGRAM))
SHELF_FILE = "%s/load-PubMed.db" % LOGDIR

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
  dataset_id = dba.ins_dataset( {'name': 'PubMed', 'source': 'NCBI E-Utils', 'app': PROGRAM, 'app_version': __version__, 'url': 'https://www.ncbi.nlm.nih.gov/pubmed'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'pubmed'})
  if not rv:
    print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
    sys.exit(1)
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'protein2pubmed'})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)
    
  s = shelve.open(SHELF_FILE, writeback=True)
  s['loaded'] = [] # list of target IDs that have been successfully processed
  s['pmids'] = [] # list of stored pubmed ids
  s['p2p_ct'] = 0
  s['errors'] = defaultdict(list)

  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  if args['--pastid']:
    tct = dba.get_target_count(idg=False, past_id=args['--pastid'])
  else:
    tct = dba.get_target_count(idg=False)
  if not args['--quiet']:
    print "\nLoading pubmeds for {} TCRD targets".format(tct)
    logger.info("Loading pubmeds for {} TCRD targets".format(tct))
  pbar = ProgressBar(widgets=pbar_widgets, maxval=tct).start()  
  ct = 0
  dba_err_ct = 0
  if args['--pastid']:
    past_id = args['--pastid']
  else:
    past_id = 0
  for target in dba.get_targets(include_annotations=True, past_id=past_id):
    ct += 1
    logger.info("Processing target {}: {}".format(target['id'], target['name']))
    p = target['components']['protein'][0]
    if 'PubMed' not in p['xrefs']: continue
    pmids = [d['value'] for d in p['xrefs']['PubMed']]
    chunk_ct = 0
    err_ct = 0
    for chunk in chunker(pmids, 200):
      chunk_ct += 1
      r = get_pubmed(chunk)
      if not r or r.status_code != 200:
        # try again...
        r = get_pubmed(chunk)
        if not r or r.status_code != 200:
          logger.error("Bad E-Utils response for target {}, chunk {}".format(target['id'], chunk_ct))
          s['errors'][target['id']].append(chunk_ct)
          err_ct += 1
          continue
      soup = BeautifulSoup(r.text, "xml")
      pmas = soup.find('PubmedArticleSet')
      for pma in pmas.findAll('PubmedArticle'):
        pmid = pma.find('PMID').text
        if pmid not in s['pmids']:
          # only store each pubmed once
          logger.debug("  parsing XML for PMID: %s" % pmid)
          init = parse_pubmed_article(pma)
          rv = dba.ins_pubmed(init)
          if not rv:
            dba_err_ct += 1
            continue
          s['pmids'].append(pmid) # add pubmed id to list of saved ones
        rv = dba.ins_protein2pubmed({'protein_id': p['id'], 'pubmed_id': pmid})
        if not rv:
          dba_err_ct += 1
          continue
        s['p2p_ct'] += 1
      time.sleep(0.5)
    if err_ct == 0:
      s['loaded'].append(target['id'])
    pbar.update(ct)
  pbar.finish()
  print "Processed {} targets.".format(ct)
  print "  Successfully loaded all PubMeds for {} targets".format(len(s['loaded']))
  print "  Inserted {} new pubmed rows".format(len(s['pmids']))
  print "  Inserted {} new protein2pubmed rows".format(s['p2p_ct'])
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)
  if len(s['errors']) > 0:
    print "WARNING: {} Network/E-Utils errors occurred. See logfile {} for details.".format(len(s['errors']), logfile)

  loop = 1
  while len(s['errors']) > 0:
    print "\nRetry loop {}: Trying to load PubMeds for {} proteins".format(loop, len(s['errors']))
    logger.info("Retry loop {}: Trying to load data for {} proteins".format(loop, len(s['errors'])))
    pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
    pbar = ProgressBar(widgets=pbar_widgets, maxval=len(s['errors'])).start()
    ct = 0
    dba_err_ct = 0
    for tid,chunk_cts in s['errors']:
      ct += 1
      target in dba.get_targets(tid, include_annotations=True)
      logger.info("Processing target {}: {}".format(target['id'], target['name']))
      p = target['components']['protein'][0]
      chunk_ct = 0
      err_ct = 0
      for chunk in chunker(pmids, 200):
        chunk_ct += 1
        # only process chunks that are in the errors lists
        if chunk_ct not in chunk_cts:
          continue
        r = get_pubmed(chunk)
        if not r or r.status_code != 200:
          # try again...
          r = get_pubmed(chunk)
          if not r or r.status_code != 200:
            logger.error("Bad E-Utils response for target {}, chunk {}".format(target['id'], chunk_ct))
            err_ct += 1
            continue
        soup = BeautifulSoup(r.text, "xml")
        pmas = soup.find('PubmedArticleSet')
        for pma in pmas.findAll('PubmedArticle'):
          pmid = pma.find('PMID').text
          if pmid not in s['pmids']:
            # only store each pubmed once
            logger.debug("  parsing XML for PMID: %s" % pmid)
            init = parse_pubmed_article(pma)
            rv = dba.ins_pubmed(init)
            if not rv:
              dba_err_ct += 1
              continue
            s['pmids'].append(pmid) # add pubmed id to list of saved ones
          rv = dba.ins_protein2pubmed({'protein_id': p['id'], 'pubmed_id': pmid})
          if not rv:
            dba_err_ct += 1
            continue
          s['p2p_ct'] += 1
        # remove chunk number from this target's error list
        s['errors'][tid].remove(chunk_ct)
        # it this target has no more errors, delete it from errors
        if len(s['errors'][tid]) == 0:
          del(s['errors'][tid])
        time.sleep(0.5)
      if err_ct == 0:
        s['loaded'].append(target['id'])
      pbar.update(ct)
    pbar.finish()
    print "Processed {} targets.".format(ct)
    print "  Successfully loaded all PubMeds for a total {} targets".format(len(s['loaded']))
    print "  Inserted {} new pubmed rows".format(len(s['pmids']))
    print "  Inserted {} new protein2pubmed rows".format(s['p2p_ct'])
    if dba_err_ct > 0:
      print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)
  if len(s['errors']) > 0:
    print "  {} targets remaining for next retry loop.".format(len(s['errors']))
  s.close()

  # Find the set of TIN-X PubMed IDs not already stored in TCRD
  tinx_pmids = [str(pmid) for pmid in dba.get_tinx_pmids()]
  tinx_pmid_ct = len(tinx_pmids)
  pmids =  [str(pmid) for pmid in dba.get_pmids()]
  if not args['--quiet']:
    print "\nChecking for {} TIN-X PubMed IDs in TCRD".format(tinx_pmid_ct)
    logger.info("Checking for {} TIN-X PubMed IDs in TCRD".format(tinx_pmid_ct))
  not_in_tcrd = list(set(tinx_pmids) - set(pmids))
  # for pmid in tinx_pmids:
  #   rv = dba.get_pubmed(pmid)
  #   if not rv:
  #     not_in_tcrd.add(pmid)
  not_in_tcrd_ct = len(not_in_tcrd)
  if not args['--quiet']:
    print "\nProcessing {} TIN-X PubMed IDs not in TCRD".format(not_in_tcrd_ct)
    logger.info("Processing {} TIN-X PubMed IDs".format(not_in_tcrd_ct))
  ct = 0
  pm_ct = 0
  net_err_ct = 0
  dba_err_ct = 0
  chunk_ct = 0
  for chunk in chunker(list(not_in_tcrd), 200):
    chunk_ct += 1
    logger.info("Processing TIN-X PubMed IDs chunk {}".format(chunk_ct))
    r = get_pubmed(chunk)
    if not r or r.status_code != 200:
      # try again...
        r = get_pubmed(chunk)
        if not r or r.status_code != 200:
          logger.error("Bad E-Utils response for chunk {}".format(chunk_ct))
          net_err_ct += 1
          continue
    soup = BeautifulSoup(r.text, "xml")
    pmas = soup.find('PubmedArticleSet')
    for pma in pmas.findAll('PubmedArticle'):
      ct += 1
      logger.debug("  parsing XML for PMID: {}".format(pmid))
      init = parse_pubmed_article(pma)
      rv = dba.ins_pubmed(init)
      if not rv:
        dba_err_ct += 1
        continue
      pm_ct += 1
    time.sleep(0.5)
  print "Processed {} TIN-X PubMed IDs.".format(ct)
  print "  Inserted {} new pubmed rows".format(pm_ct)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)
  if net_err_ct > 0:
    print "WARNING: {} Network/E-Utils errors occurred. See logfile {} for details.".format(net_err_ct, logfile)

def chunker(l, size):
  return (l[pos:pos + size] for pos in xrange(0, len(l), size))

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

def parse_pubmed_article(pma):
  """
  Parse a BeautifulSoup PubmedArticle into a dict suitable to use as an argument
  to TCRC.DBAdaptor.ins_pubmed().
  """
  pmid = pma.find('PMID').text
  article = pma.find('Article')
  title = article.find('ArticleTitle').text
  init = {'id': pmid, 'title': title }
  journal = article.find('Journal')
  pd = journal.find('PubDate')
  if pd:
    init['date'] = pubdate2isostr(pd)
  jt = journal.find('Title')
  if jt:
    init['journal'] = jt.text
  authors = pma.findAll('Author')
  if len(authors) > 0:
    if len(authors) > 5:
      # For papers with more than five authors, the authors field will be
      # formated as: "Mathias SL and 42 more authors."
      a = authors[0]
      # if the first author has no last name, we skip populating the authors field
      if a.find('LastName'):
        astr = "%s" % a.find('LastName').text
        if a.find('ForeName'):
          astr += ", %s" % a.find('ForeName').text
        if a.find('Initials'):
          astr += " %s" % a.find('Initials').text
        init['authors'] = "%s and %d more authors." % (astr, len(authors)-1)
    else:
      # For papers with five or fewer authors, the authors field will have all their names
      auth_strings = []
      last_auth = authors.pop()
      # if the last author has no last name, we skip populating the authors field
      if last_auth.find('LastName'):
        last_auth_str = "%s" % last_auth.find('LastName').text
        if last_auth.find('ForeName'):
          last_auth_str += ", %s" % last_auth.find('ForeName').text
        if last_auth.find('Initials'):
          last_auth_str += " %s" % last_auth.find('Initials').text
        for a in authors:
          if a.find('LastName'): # if authors have no last name, we skip them
            astr = "%s" % a.find('LastName').text
            if a.find('ForeName'):
              astr += ", %s" % a.find('ForeName').text
            if a.find('Initials'):
              astr += " %s" % a.find('Initials').text
            auth_strings.append(astr)
        init['authors'] = "%s and %s." % (", ".join(auth_strings), last_auth_str)
  abstract = article.find('AbstractText')
  if abstract:
    init['abstract'] = abstract.text
  return init


if __name__ == '__main__':
  print "\n{} (v{}) [{}]:".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  start_time = time.time()
  load(args)
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))


# Use this to manually insert errors
# In [26]: t = dba.get_target(18821, include_annotations=True)
# In [27]: p = target['components']['protein'][0]
# In [28]: pmids = [d['value'] for d in p['xrefs']['PubMed']]
# In [29]: len(pmids)
# Out[29]: 1387
# In [34]: url = EFETCHURL + ','.join(pmids[0:200])
# In [35]: r = requests.get(url)
# In [36]: r
# Out[36]: <Response [200]>
# In [43]: parse_insert(r)
# Inserted/Skipped 200 pubmed rows
# ct = 1
# for chunk in chunker(pmids, 200):
#   url = EFETCHURL + ','.join(pmids[0:200])
#   r = requests.get(url)
#   print "Chunk %d: %s" % (ct, r.status_code)
#   parse_insert(r)
# def parse_insert(r):
#   ct = 0
#   soup = BeautifulSoup(r.text, "xml")
#   pmas = soup.find('PubmedArticleSet')
#   for pma in pmas.findAll('PubmedArticle'):
#     pmid = pma.find('PMID').text
#     article = pma.find('Article')
#     title = article.find('ArticleTitle').text
#     init = {'id': pmid, 'protein_id': p['id'], 'title': title }
#     pd = article.find('PubDate')
#     if pd:
#       init['date'] = pubdate2isostr(pd)
#       abstract = article.find('AbstractText')
#     if abstract:
#       init['abstract'] = abstract.text
#     dba.ins_pubmed(init)
#     ct += 1
#   print "Inserted/Skipped %d pubmed rows" % ct

