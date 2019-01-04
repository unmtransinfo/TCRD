#!/usr/bin/env python
# Time-stamp: <2019-01-04 10:11:05 smathias>
"""Load protein data from UniProt.org into TCRD via the web.

Usage:
    load-UniProt.py [--debug | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-UniProt.py -? | --help

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
  -d --debug           : turn on debugging output
  -? --help            : print this message and exit 
"""
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2014-2019, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "3.0.0"

import os,sys,time,re
from docopt import docopt
from TCRDMP import DBAdaptor
import logging
import obo
from lxml import etree, objectify
from progressbar import *
import slm_tcrd_functions as slmf
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

PROGRAM = os.path.basename(sys.argv[0])
LOGDIR = "./tcrd6logs"
LOGFILE = "%s/%s.log" % (LOGDIR, PROGRAM)

# Download XML files for:
# https://www.uniprot.org/uniprot/?query=reviewed:yes AND organism:"Homo sapiens (Human) [9606]"
# https://www.uniprot.org/uniprot/?query=organism:"Mus musculus (Mouse) [10090]"
# https://www.uniprot.org/uniprot/?query=organism:"Rattus norvegicus (Rat) [10116]"
UP_HUMAN_FILE = '../data/UniProt/uniprot-reviewed-human_20190103.xml'
UP_MOUSE_FILE = '../data/UniProt/uniprot-mouse_20190103.xml'
UP_RAT_FILE = '../data/UniProt/uniprot-rat_20190103.xml'
NS = '{http://uniprot.org/uniprot}'
ECO_OBO_FILE = '../data/eco.obo'

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

  # DBAdaptor uses same logger as load()
  dba_params = {'dbhost': args['--dbhost'], 'dbname': args['--dbname'], 'logger_name': __name__}
  dba = DBAdaptor(dba_params)
  dbi = dba.get_dbinfo()
  logger.info("Connected to TCRD database %s (schema ver %s; data ver %s)", args['--dbname'], dbi['schema_ver'], dbi['data_ver'])
  if not args['--quiet']:
    print "\nConnected to TCRD database %s (schema ver %s; data ver %s)" % (args['--dbname'], dbi['schema_ver'], dbi['data_ver'])

  # Human loaded into target, protein, etc.
  # Datasets and Provenances
  start_time = time.time()
  dataset_id = dba.ins_dataset( {'name': 'UniProt', 'source': 'XML file downloaded from from UniProt query reviewed:yes AND organism:"Homo sapiens (Human) [9606]"', 'app': PROGRAM, 'app_version': __version__, 'url': 'https://www.uniprot.org/uniprot'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset. See logfile %s for details." % logfile
    sys.exit(1)
  provs = [ {'dataset_id': dataset_id, 'table_name': 'target', 'column_name': 'ttype'},
            {'dataset_id': dataset_id, 'table_name': 'target', 'column_name': 'name'},
            {'dataset_id': dataset_id, 'table_name': 'protein'},
            {'dataset_id': dataset_id, 'table_name': 'tdl_info', 'where_clause': "itype = 'UniProt Function'"},
            {'dataset_id': dataset_id, 'table_name': 'goa'},  
            {'dataset_id': dataset_id, 'table_name': 'expression', 'where_clause': "etype = 'UniProt Tissue'"},
            {'dataset_id': dataset_id, 'table_name': 'pathway', 'where_clause': "type = 'uniprot'"},
            {'dataset_id': dataset_id, 'table_name': 'disease', 'where_clause': "dtype = 'uniprot'"},
            {'dataset_id': dataset_id, 'table_name': 'feature'},
            {'dataset_id': dataset_id, 'table_name': 'xref', 'where_clause': "dataset_id = %d"%dataset_id},
            {'dataset_id': dataset_id, 'table_name': 'alias', 'where_clause': "dataset_id = %d"%dataset_id} ]
  for prov in provs:
    rv = dba.ins_provenance(prov)
    if not rv:
      print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
      sys.exit(1)

  # UniProt uses Evidence Ontology ECO IDs, not GO evidence codes, so get a mapping of
  # ECO IDs to GO evidence codes
  eco_map = mk_eco_map()
    
  xtypes = dba.get_xref_types()
  
  print "\nParsing file {}".format(UP_HUMAN_FILE)
  root = objectify.parse(UP_HUMAN_FILE).getroot()
  up_ct = len(root.entry)
  print "Loading data for {} UniProt records".format(up_ct)
  logger.info("Loading data for {} UniProt records in file {}".format(up_ct, UP_HUMAN_FILE))
  pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=up_ct).start()
  ct = 0
  load_ct = 0
  xml_err_ct = 0
  dba_err_ct = 0
  for i in range(len(root.entry)):
    ct += 1
    entry = root.entry[i]
    logger.info("Processing entry {}".format(entry.accession))
    target = entry2target(entry, dataset_id, xtypes, eco_map)
    if not target:
      xml_err_ct += 1
      logger.error("XML Error for %s" % entry.accession)
      continue
    tid = dba.ins_target(target)
    if not tid:
      dba_err_ct += 1
      continue
    logger.debug("Target insert id: %s" % tid)
    load_ct += 1
    pbar.update(ct)
  pbar.finish()
  elapsed = time.time() - start_time
  print "Processed {} UniProt records. Elapsed time: {}".format(ct, slmf.secs2str(elapsed))
  print "  Loaded {} targets/proteins".format(load_ct)
  if xml_err_ct > 0:
    print "WARNING: {} XML parsing errors occurred. See logfile {} for details.".format(xml_err_ct, logfile)
  if dba_err_ct > 0:
    print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

  # Mouse and Rat loaded into nhprotein
  dataset_id = dba.ins_dataset( {'name': 'UniProt Mouse Proteins', 'source': 'XML file downloaded from from UniProt query organism: "Mus musculus (Mouse) [10090]"', 'app': PROGRAM, 'app_version': __version__, 'url': 'https://www.uniprot.org/uniprot'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'nhprotein', 'where_clause': "taxid = 10090"})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)
  # Rat
  dataset_id = dba.ins_dataset( {'name': 'UniProt Rat Proteins', 'source': 'XML file downloaded from from UniProt query organism: "Rattus norvegicus (Rat) [10116]"', 'app': PROGRAM, 'app_version': __version__, 'url': 'https://www.uniprot.org/uniprot'} )
  assert dataset_id, "Error inserting dataset See logfile {} for details.".format(logfile)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'nhprotein', 'where_clause': "taxid = 10116"})
  assert rv, "Error inserting provenance. See logfile {} for details.".format(logfile)

  for ifn in (UP_MOUSE_FILE, UP_RAT_FILE):
    start_time = time.time()
    print "\nParsing file {}".format(ifn)
    root = objectify.parse(ifn).getroot()
    up_ct = len(root.entry)
    print "Loading data for {} UniProt records".format(up_ct)
    logger.info("Loading data for {} UniProt records in file {}".format(up_ct, ifn))
    pbar_widgets = ['Progress: ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
    pbar = ProgressBar(widgets=pbar_widgets, maxval=up_ct).start()
    ct = 0
    nhp_ct = 0
    xml_err_ct = 0
    dba_err_ct = 0
    for i in range(len(root.entry)):
      ct += 1
      entry = root.entry[i]
      logger.info("Processing entry {}".format(entry.accession))
      nhprotein = entry2nhprotein(entry, dataset_id)
      if not nhprotein:
        xml_err_ct += 1
        logger.error("XML Error for {}".format(entry.accession))
        continue
      nhpid = dba.ins_nhprotein(nhprotein)
      if not nhpid:
        dba_err_ct += 1
        continue
      logger.debug("Nhprotein insert id: {}".format(nhpid))
      nhp_ct += 1
      pbar.update(ct)
    pbar.finish()
    elapsed = time.time() - start_time
    print "Processed {} UniProt records. Elapsed time: {}".format(ct, slmf.secs2str(elapsed))
    print "  Loaded {} nhproteins".format(nhp_ct)
    if xml_err_ct > 0:
      print "WARNING: {} XML parsing errors occurred. See logfile {} for details.".format(xml_err_ct, logfile)
    if dba_err_ct > 0:
      print "WARNING: {} DB errors occurred. See logfile {} for details.".format(dba_err_ct, logfile)

def get_entry_by_accession(root, acc):
  """
  This is for debugging in IPython.
  """
  for i in range(len(root.entry)):
    entry = root.entry[i]
    if entry.accession == acc:
      return entry
  return None
                                              
def mk_eco_map():
  """
  Return a mapping of Evidence Ontology ECO IDs to Go Evidence Codes.
  """
  eco = {}
  eco_map = {}
  print "\nParsing Evidence Ontology file {}".format(ECO_OBO_FILE)
  parser = obo.Parser(ECO_OBO_FILE)
  for stanza in parser:
    eco[stanza.tags['id'][0].value] = stanza.tags
  regex = re.compile(r'GOECO:([A-Z]{2,3})')
  for e,d in eco.items():
    if not e.startswith('ECO:'):
      continue
    if 'xref' in d:
      for x in d['xref']:
        m = regex.match(x.value)
        if m:
          eco_map[e] = m.group(1)
  return eco_map

def entry2target(entry, dataset_id, xtypes, e2e):
  """
  Convert an entry element of type lxml.objectify.ObjectifiedElement parsed from a UniProt XML entry and return a target dictionary suitable for passing to TCRD.DBAdaptor.ins_target().
  """
  target = {'name': entry.protein.recommendedName.fullName, 'ttype': 'Single Protein'}
  target['components'] = {}
  target['components']['protein'] = []
  protein = {'uniprot': entry.accession} # returns first accession
  protein['name'] = entry.name
  protein['description'] = entry.protein.recommendedName.fullName
  protein['sym'] = None
  aliases = []
  if entry.find(NS+'gene'):
    if entry.gene.find(NS+'name'):
      for gn in entry.gene.name: # returns all gene.names
        if gn.get('type') == 'primary':
          protein['sym'] = gn
        elif gn.get('type') == 'synonym':
          # HGNC symbol alias
          aliases.append( {'type': 'symbol', 'dataset_id': dataset_id, 'value': gn} )
  protein['seq'] = str(entry.sequence).replace('\n', '')
  protein['up_version'] = entry.sequence.get('version')
  for acc in entry.accession: # returns all accessions
    if acc != protein['uniprot']:
      aliases.append( {'type': 'uniprot', 'dataset_id': dataset_id, 'value': acc} )
  if entry.protein.recommendedName.find(NS+'shortName') != None:
    sn = entry.protein.recommendedName.shortName
    aliases.append( {'type': 'uniprot', 'dataset_id': dataset_id, 'value': sn} )
  protein['aliases'] = aliases
  # TDL Infos, Family, Diseases, Pathways from comments
  tdl_infos = []
  pathways = []
  diseases = []
  if entry.find(NS+'comment'):
    for c in entry.comment:
      if c.get('type') == 'function':
        tdl_infos.append( {'itype': 'UniProt Function',  'string_value': c.getchildren()[0]} )
      if c.get('type') == 'pathway':
        pathways.append( {'pwtype': 'UniProt', 'name': c.getchildren()[0]} )
      if c.get('type') == 'similarity':
        protein['family'] = c.getchildren()[0]
      if c.get('type') == 'disease':
        if not c.find(NS+'disease'):
          continue
        if c.disease.find(NS+'name') == None:
          # some dont have a name, so skip those
          continue
        da = {'dtype': 'UniProt Disease' }
        for el in c.disease.getchildren():
          if el.tag == NS+'name':
            da['name'] = el
          elif el.tag == NS+'description':
            da['description'] = el
          elif el.tag == NS+'dbReference':
            da['did'] = "%s:%s"%(el.attrib['type'], el.attrib['id'])
        if 'evidence' in c.attrib:
          da['evidence'] = c.attrib['evidence']
        diseases.append(da)
  protein['tdl_infos'] = tdl_infos
  protein['diseases'] = diseases
  protein['pathways'] = pathways
  # GeneID, XRefs, GOAs from dbReferences
  xrefs = []
  goas = []
  for dbr in entry.dbReference:
    if dbr.attrib['type'] == 'GeneID':
      # Some UniProt records have multiple Gene IDs
      # In most(?) cases, the first one is the right one
      # So, only take the first one
      if 'geneid' not in protein:
        protein['geneid'] = dbr.attrib['id']
    elif dbr.attrib['type'] in ['InterPro', 'Pfam', 'PROSITE', 'SMART']:
      xtra = None
      if dbr.attrib['type'] in ['InterPro', 'Pfam', 'PROSITE', 'SMART']:
        for el in dbr.findall(NS+'property'):
          if el.attrib['type'] == 'entry name':
            xtra = el.attrib['value']
        xrefs.append( {'xtype': dbr.attrib['type'], 'dataset_id': dataset_id,
                       'value': dbr.attrib['id'], 'xtra': xtra} )
    elif dbr.attrib['type'] == 'GO':
      name = None
      goeco = None
      assigned_by = None
      for el in dbr.findall(NS+'property'):
        if el.attrib['type'] == 'term':
          name = el.attrib['value']
        elif el.attrib['type'] == 'evidence':
          goeco = el.attrib['value']
        elif el.attrib['type'] == 'project':
          assigned_by = el.attrib['value']
      goas.append( {'go_id': dbr.attrib['id'], 'go_term': name,
                    'goeco': goeco, 'evidence': e2e[goeco], 'assigned_by': assigned_by} )
    elif dbr.attrib['type'] == 'Ensembl':
      xrefs.append( {'xtype': 'Ensembl', 'dataset_id': dataset_id, 'value': dbr.attrib['id']} )
      for el in dbr.findall(NS+'property'):
        if el.attrib['type'] == 'protein sequence ID':
          xrefs.append( {'xtype': 'Ensembl', 'dataset_id': dataset_id, 'value': el.attrib['value']} )
        elif el.attrib['type'] == 'gene ID':
          xrefs.append( {'xtype': 'Ensembl', 'dataset_id': dataset_id, 'value': el.attrib['value']} )
    elif dbr.attrib['type'] == 'STRING':
      xrefs.append( {'xtype': 'STRING', 'dataset_id': dataset_id, 'value': dbr.attrib['id']} )
    elif dbr.attrib['type'] == 'DrugBank':
      xtra = None
      for el in dbr.findall(NS+'property'):
        if el.attrib['type'] == 'generic name':
          xtra = el.attrib['value']
      xrefs.append( {'xtype': 'DrugBank', 'dataset_id': dataset_id, 'value': dbr.attrib['id'],
                     'xtra': xtra} )
    else:
      if dbr.attrib['type'] in xtypes:
        xrefs.append( {'xtype': dbr.attrib['type'], 'dataset_id': dataset_id,
                       'value': dbr.attrib['id']} )
  protein['goas'] = goas
  # Keywords
  for kw in entry.keyword:
    xrefs.append( {'xtype': 'UniProt Keyword', 'dataset_id': dataset_id, 'value': kw.attrib['id'],
                   'xtra': kw} )
  protein['xrefs'] = xrefs
  # Expression
  exps = []
  for ref in entry.reference:
    if ref.find(NS+'source'):
      if ref.source.find(NS+'tissue'):
        ex = {'etype': 'UniProt Tissue', 'tissue': ref.source.tissue, 'boolean_value': 1}
        for el in ref.citation.findall(NS+'dbReference'):
          if el.attrib['type'] == 'PubMed':
            ex['pubmed_id'] = el.attrib['id']
        exps.append(ex)
  protein['expressions'] = exps
  # Features
  features = []
  for f in entry.feature:
    init = {'type': f.attrib['type']}
    if 'evidence' in f.attrib:
      init['evidence'] = f.attrib['evidence']
    if 'description' in f.attrib:
      init['description'] = f.attrib['description']
    if 'id' in f.attrib:
      init['srcid'] = f.attrib['id']
    for el in f.location.getchildren():
      if el.tag == NS+'position':
        init['position'] = el.attrib['position']
      else:
        if el.tag == NS+'begin':
          if 'position' in el.attrib:
            init['begin'] = el.attrib['position']
        if el.tag == NS+'end':
          if 'position' in el.attrib:
            init['end'] = el.attrib['position']
    features.append(init)
  protein['features'] = features
  
  target['components']['protein'].append(protein)

  return target

def entry2nhprotein(entry, dataset_id):
  """
  Convert an entry element of type lxml.objectify.ObjectifiedElement parsed from a UniProt XML entry and return a dictionary suitable for passing to TCRD.DBAdaptor.ins_nhprotein().
  """
  nhprotein = {'uniprot': entry.accession, 'name': entry.name,
               'taxid': entry.organism.dbReference.attrib['id']}
  # description
  if entry.protein.find(NS+'recommendedName'):
    nhprotein['description'] = entry.protein.recommendedName.fullName
  elif entry.protein.find(NS+'submittedName'):
    nhprotein['description'] = entry.protein.submittedName.fullName
  # sym
  if entry.find(NS+'gene'):
    if entry.gene.find(NS+'name'):
       if entry.gene.name.get('type') == 'primary':
         nhprotein['sym'] = entry.gene.name
  # species
  for name in entry.organism.name:
    if name.attrib["type"] == "scientific":
      nhprotein['species'] = name.text
  # geneid
  for dbr in entry.dbReference:
    if dbr.attrib['type'] == 'GeneID':
      nhprotein['geneid'] = dbr.attrib['id']
  # # Ensembl Gene ID
  # xrefs = []
  # for dbr in entry.dbReference:
  #   if(dbr.attrib["type"] == "Ensembl"):
  #     if dbr.property is not None and len(dbr.property) > 0:
  #       for prop in dbr.property:
  #         if prop.attrib["type"] == "gene ID":
  #           nhprotein['xrefs'].append({'xtype': 'ENSG', 'dataset_id': dataset_id, 'value': prop.attrib["value"]})
  #           break
  # nhprotein['xrefs'] = xrefs
  
  return nhprotein
  

if __name__ == '__main__':
  print "\n%s (v%s) [%s]:" % (PROGRAM, __version__, time.strftime("%c"))
  args = docopt(__doc__, version=__version__)
  if int(args['--debug']):
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
  start_time = time.time()
  load(args)
  elapsed = time.time() - start_time
  print "\n%s: Done. Total elapsed time: %s\n" % (PROGRAM, slmf.secs2str(elapsed))
