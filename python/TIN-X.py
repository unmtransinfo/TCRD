#!/usr/bin/env python
# Time-stamp: <2019-08-22 10:54:04 smathias>
"""Generate TIN-X scores and PubMed ID rankings from Jensen lab's protein and disease mentions TSV files.

Usage:
    TIN-X.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    TIN-X.py -? | --help

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
__copyright__ = "Copyright 2016-2019, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "3.0.0"

import os,sys,time
from docopt import docopt
from TCRDMP import DBAdaptor
import logging
import urllib
import obo
from progressbar import *
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
VER = '6' # CHANGE THIS!!!
LOGDIR = '../loaders/tcrd%slogs/'%VER
LOGFILE = LOGDIR + '%s.log'%PROGRAM

DO_BASE_URL = 'https://raw.githubusercontent.com/DiseaseOntology/HumanDiseaseOntology/master/src/ontology/'
DO_DOWNLOAD_DIR = '../data/DiseaseOntology/'
DO_OBO = 'doid.obo'
JL_BASE_URL = 'http://download.jensenlab.org/'
JL_DOWNLOAD_DIR = '../data/JensenLab/'
DISEASE_FILE = 'disease_textmining_mentions.tsv'
PROTEIN_FILE = 'human_textmining_mentions.tsv'
# Output CSV files:
PROTEIN_NOVELTY_FILE = '../data/TIN-X/TCRDv%s/ProteinNovelty.csv'%VER
DISEASE_NOVELTY_FILE = '../data/TIN-X/TCRDv%s/DiseaseNovelty.csv'%VER
PMID_RANKING_FILE = '../data/TIN-X/TCRDv%s/PMIDRanking.csv'%VER
IMPORTANCE_FILE = '../data/TIN-X/TCRDv%s/Importance.csv'%VER

def download_mentions(args):
  print
  for f in [DISEASE_FILE, PROTEIN_FILE]:
    if os.path.exists(JL_DOWNLOAD_DIR + f):
      os.remove(JL_DOWNLOAD_DIR + f)
    if not args['--quiet']:
      print "Downloading", JL_BASE_URL + f
      print "         to", JL_DOWNLOAD_DIR + f
    urllib.urlretrieve(JL_BASE_URL + f, JL_DOWNLOAD_DIR + f)

def download_do(args):
  print
  if os.path.exists(DO_DOWNLOAD_DIR + DO_OBO):
    os.remove(DO_DOWNLOAD_DIR + DO_OBO)
  if not args['--quiet']:
    print "Downloading", DO_BASE_URL + DO_OBO
    print "         to", DO_DOWNLOAD_DIR + DO_OBO
  urllib.urlretrieve(DO_BASE_URL + DO_OBO, DO_DOWNLOAD_DIR + DO_OBO)

def tinx(args):
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

  # The results of parsing the input mentions files will be the following dictionaries:
  pid2pmids = {}  # 'TCRD.protein.id,UniProt' => set of all PMIDs that mention the protein
                  # Including the UniProt accession in the key is just for convenience when
                  # checking the output. It is not used for anything.
  doid2pmids = {} # DOID => set of all PMIDs that mention the disease
  pmid_disease_ct = {} # PMID => count of diseases mentioned in a given paper 
  pmid_protein_ct = {} # PMID => count of proteins mentioned in a given paper 

  # First parse the Disease Ontology OBO file to get DO names and defs
  dofile = DO_DOWNLOAD_DIR + DO_OBO
  print "\nParsing Disease Ontology file {}".format(dofile)
  do_parser = obo.Parser(open(dofile))
  do = {}
  for stanza in do_parser:
    do[stanza.tags['id'][0].value] = stanza.tags
  print "  Got {} Disease Ontology terms".format(len(do))

  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]

  fn = JL_DOWNLOAD_DIR+PROTEIN_FILE
  line_ct = slmf.wcl(fn)
  if not args['--quiet']:
    print "\nProcessing {} lines in protein file {}".format(line_ct, fn)
  with open(fn, 'rU') as tsvf:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    ct = 0
    skip_ct = 0
    notfnd = set()
    for line in tsvf:
      ct += 1
      pbar.update(ct)
      if not line.startswith('ENSP'):
        skip_ct += 1
        continue
      data = line.rstrip().split('\t')
      ensp = data[0]
      pmids = set([int(pmid) for pmid in data[1].split()])
      targets = dba.find_targets({'stringid': ensp})
      if not targets:
        # if we don't find a target by stringid, which is the more reliable and
        # prefered way, try by Ensembl xref
        targets = dba.find_targets_by_xref({'xtype': 'Ensembl', 'value': ensp})
      if not targets:
        notfnd.add(ensp)
        continue
      for t in targets:
        p = t['components']['protein'][0]
        k = "%s,%s" % (p['id'], p['uniprot'])
        if k in pid2pmids:
          pid2pmids[k] = pid2pmids[k].union(pmids)
        else:
          pid2pmids[k] = set(pmids)
        for pmid in pmids:
          if pmid in pmid_protein_ct:
            pmid_protein_ct[pmid] += 1.0
          else:
            pmid_protein_ct[pmid] = 1.0
  pbar.finish()
  for ensp in notfnd:
    logger.warn("No target found for {}".format(ensp))
  print "{} lines processed.".format(ct)
  print "  Skipped {} non-ENSP lines".format(skip_ct)
  print "  Saved {} protein to PMIDs mappings".format(len(pid2pmids))
  print "  Saved {} PMID to protein count mappings".format(len(pmid_protein_ct))
  if notfnd:
    print "  No target found for {} ENSPs. See logfile {} for details.".format(len(notfnd), logfile)

  fn = JL_DOWNLOAD_DIR+DISEASE_FILE
  line_ct = slmf.wcl(fn)
  if not args['--quiet']:
    print "\nProcessing {} lines in file {}".format(line_ct, fn)
  with open(fn, 'rU') as tsvf:
    pbar = ProgressBar(widgets=pbar_widgets, maxval=line_ct).start() 
    ct = 0
    skip_ct = 0
    notfnd = set()
    for line in tsvf:
      ct += 1
      pbar.update(ct)
      if not line.startswith('DOID:'):
        skip_ct += 1
        continue
      data = line.rstrip().split('\t')
      doid = data[0]
      pmids = set([int(pmid) for pmid in data[1].split()])
      if doid not in do:
        logger.warn("%s not found in DO" % doid)
        notfnd.add(doid)
        continue
      if doid in doid2pmids:
        doid2pmids[doid] = doid2pmids[doid].union(pmids)
      else:
        doid2pmids[doid] = set(pmids)
      for pmid in pmids:
        if pmid in pmid_disease_ct:
          pmid_disease_ct[pmid] += 1.0
        else:
          pmid_disease_ct[pmid] = 1.0
  pbar.finish()
  print "{} lines processed.".format(ct)
  print "  Skipped {} non-DOID lines".format(skip_ct)
  print "  Saved {} DOID to PMIDs mappings".format(len(doid2pmids))
  print "  Saved {} PMID to disease count mappings".format(len(pmid_disease_ct))
  if notfnd:
    print "WARNNING: No entry found in DO map for {} DOIDs. See logfile {} for details.".format(len(notfnd), logfile)

  if not args['--quiet']:
    print "\nComputing protein novely scores"
  # To calculate novelty scores, each paper (PMID) is assigned a
  # fractional target (FT) score of one divided by the number of targets
  # mentioned in it. The novelty score of a given protein is one divided
  # by the sum of the FT scores for all the papers mentioning that
  # protein.
  ct = 0
  with open(PROTEIN_NOVELTY_FILE, 'wb') as pnovf:
    pnovf.write("Protein ID,UniProt,Novelty\n")
    for k in pid2pmids.keys():
      ct += 1
      ft_score_sum = 0.0
      for pmid in pid2pmids[k]:
        ft_score_sum += 1.0 / pmid_protein_ct[pmid]
      novelty = 1.0 / ft_score_sum
      pnovf.write( "%s,%.8f\n" % (k, novelty) )
  print "  Wrote {} novelty scores to file {}".format(ct, PROTEIN_NOVELTY_FILE)

  if not args['--quiet']:
    print "\nComputing disease novely scores"
  # Exactly as for proteins, but using disease mentions
  ct = 0
  with open(DISEASE_NOVELTY_FILE, 'wb') as dnovf:
    dnovf.write("DOID,Novelty\n")
    for doid in doid2pmids.keys():
      ct += 1
      ft_score_sum = 0.0
      for pmid in doid2pmids[doid]:
        ft_score_sum += 1.0 / pmid_disease_ct[pmid]
      novelty = 1.0 / ft_score_sum
      dnovf.write( "%s,%.8f\n" % (doid, novelty) )
  print "  Wrote {} novelty scores to file {}".format(ct, DISEASE_NOVELTY_FILE)

  if not args['--quiet']:
    print "\nComputing importance scores"
  # To calculate importance scores, each paper is assigned a fractional
  # disease-target (FDT) score of one divided by the product of the
  # number of targets mentioned and the number of diseases
  # mentioned. The importance score for a given disease-target pair is
  # the sum of the FDT scores for all papers mentioning that disease and
  # protein.
  ct = 0
  with open(IMPORTANCE_FILE, 'wb') as impf:
    impf.write("DOID,Protein ID,UniProt,Score\n")
    for k,ppmids in pid2pmids.items():
      for doid,dpmids in doid2pmids.items():
        pd_pmids = ppmids.intersection(dpmids)
        fdt_score_sum = 0.0
        for pmid in pd_pmids:
          fdt_score_sum += 1.0 / ( pmid_protein_ct[pmid] * pmid_disease_ct[pmid] )
        if fdt_score_sum > 0:
          ct += 1
          impf.write( "%s,%s,%.8f\n" % (doid, k, fdt_score_sum) )
  print "  Wrote {} importance scores to file {}".format(ct, IMPORTANCE_FILE)

  if not args['--quiet']:
    print "\nComputing PubMed rankings"
  # PMIDs are ranked for a given disease-target pair based on a score
  # calculated by multiplying the number of targets mentioned and the
  # number of diseases mentioned in that paper. Lower scores have a lower
  # rank (higher priority). If the scores do not discriminate, PMIDs are
  # reverse sorted by value with the assumption that larger PMIDs are
  # newer and of higher priority.
  ct = 0
  with open(PMID_RANKING_FILE, 'wb') as pmrf:
    pmrf.write("DOID,Protein ID,UniProt,PubMed ID,Rank\n")
    for k,ppmids in pid2pmids.items():
      for doid,dpmids in doid2pmids.items():
        pd_pmids = ppmids.intersection(dpmids)
        scores = [] # scores are tuples of (PMID, protein_mentions*disease_mentions)
        for pmid in pd_pmids:
          scores.append( (pmid, pmid_protein_ct[pmid] * pmid_disease_ct[pmid]) )
        if len(scores) > 0:
          scores.sort(cmp_pmids_scores)
          for i,t in enumerate(scores):
            ct += 1
            pmrf.write( "%s,%s,%d,%d\n" % (doid, k, t[0], i) )
  print "  Wrote {} PubMed rankings to file {}".format(ct, PMID_RANKING_FILE)

def cmp_pmids_scores(a, b):
  '''
  a and b are tuples: (PMID, score)
  This sorts first by score ascending and then by PMID descending.
  '''
  if a[1] > b[1]:
    return 1
  elif a[1] < b[1]:
    return -1
  elif a[0] > b[0]:
    return -1
  elif a[1] < b[0]:
    return 1
  else:
    return 0


if __name__ == '__main__':
  print "\n{} (v{}) [{}]:".format(PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if args['--debug']:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  start_time = time.time()
  #download_do(args)
  download_mentions(args)
  tinx(args)
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))
  
