#!/usr/local/bin/python
# Time-stamp: <2019-10-30 10:20:05 smathias>
'''
tcrd2csv.py - Export TCRD target data to a CSV file
'''
__author__ = "Steve Mathias"
__email__ = "smathias@salud.unm.edu"
__org__ = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2014-2018, Steve Mathias"
__license__ = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__ = "2.0.2"

import sys
reload(sys)
sys.setdefaultencoding('utf8')
import os,argparse,re
from TCRDMP import DBAdaptor
import csv
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
DBNAME = 'tcrd'
OUTFILE = 'TCRD.csv'

def main():
  argparser = argparse.ArgumentParser(description="Export TCRD target data to a CSV file")
  argparser.add_argument("-o", "--outfile", help='Output file [path/]name', default=OUTFILE)
  argparser.add_argument('-db', '--dbname', help='MySQL database name', default=DBNAME)
  argparser.add_argument("-i", "--idg", help="Export only IDG-Eligible tagets", action="store_true", default=False)
  argparser.add_argument("-e", "--expand", help="Export expanded (a LOT of data) CSV version", action="store_true", default=False)
  args = argparser.parse_args()
  
  dba = DBAdaptor({'dbname': args.dbname})
  dbi = dba.get_dbinfo()
  print "\n%s (v%s) [%s]:" % (PROGRAM, __version__, time.strftime("%c"))
  print "\nConnected to TCRD database %s (schema ver %s, data ver %s)\n" % (dbi['dbname'], dbi['schema_ver'], dbi['data_ver'])

  if args.idg:
    tct = dba.get_target_count(idg=True)
    print "Exporting CSV for %d IDG-Eligible targets from TCRD to file %s" % (tct, args.outfile)
  else:
    tct = dba.get_target_count(idg=False)
    print "Exporting CSV for all %d targets from TCRD to file %s" % (tct, args.outfile)

  header = ['TCRD ID', 'Name', 'Description', 'HGNC Sym', 'NCBI Gene ID', 'UniProt', 'STRING ID', 'TDL', 'IDG Eligible', 'DTO ID', 'DTO Class']
  if args.expand:
    header = header + ['PANTHER Class(es)', 'GeneRIF Count', 'NCBI Gene PubMed Count', 'JensenLab PubMed Score', 'PubTator Score', 'Ab Count', 'Monoclonal Ab Count', 'Activity Count', 'ChEMBL Selective Compound', 'ChEMBL First Reference Year', 'DrugCentral Activity Count', 'PDB Count', 'PDBs', 'GO Annotation Count', 'Experimental MF/BP Leaf Term GOA(s)', 'OMIM Phenotype Count', 'OMIM Phenotype(s)', 'JAX/MGI Human Ortholog Phenotype Count', 'JAX/MGI Human Ortholog Phenotype(s)', 'IMPC Ortholog Phenotype Count', 'IMPC Ortholog Phenotype(s)', 'GWAS Count', 'GWAS Phenotype(s)', 'Pathway Count', 'Pathways', 'Total Disease Count', 'Top 5 Text-Mining DISEASES', 'eRAM Diseases', 'EBI Patent Count', 'Is Transcription Factor', 'TMHMM Prediction', 'HPA Tissue Specificity Index', 'HPM Gene Tissue Specificity Index', 'HPM Protein Tissue Specificity Index', 'TIN-X Novelty', 'Top 5 TIN-X Importance(s)']
    
  pbar_widgets = ['Progress: ', Percentage(), ' ', Bar(marker='#',left='[',right=']'), ' ', ETA()]
  pbar = ProgressBar(widgets=pbar_widgets, maxval=tct).start()
  with open(args.outfile, 'wb') as csvout:
    csvwriter = csv.writer(csvout, quotechar='"', quoting=csv.QUOTE_MINIMAL)
    csvwriter.writerow(header)
    ct = 0
    if args.idg:
      for t in dba.get_targets(idg=True, include_annotations=args.expand):
        ct += 1
        if args.expand:
          csvwriter.writerow( target2csv_exp(t) )
        else:
          csvwriter.writerow( target2csv(t) )
        pbar.update(ct)
    else:
      for t in dba.get_targets(idg=False, include_annotations=args.expand):
      #for tid in [9]:
      #  t = dba.get_target(tid, True)
        ct += 1
        if args.expand:
          csvwriter.writerow(target2csv_exp(t))
        else:
          csvwriter.writerow(target2csv(t))
        pbar.update(ct)
  pbar.finish()

  print "%d CSV rows exported" % ct
  print "\n%s: Done." % PROGRAM


def target2csv(t):
  p = t['components']['protein'][0]
  if not p['dtoid']: p['dtoid'] = ''
  if not p['dtoclass']: p['dtoclass'] = ''
  if t['idg']:
    idg = 1
  else:
    idg = 0
  csv = [ t['id'], p['name'], p['description'], p['sym'], p['geneid'], p['uniprot'], p['stringid'], t['tdl'], idg, p['dtoid'], p['dtoclass'] ]
  return csv

def target2csv_exp(t):
  #print "[DEBUG] Processing target {}".format(t['id'])
  ttdls = {}
  if 'tdl_infos' in t:
    ttdls = t['tdl_infos']
  p = t['components']['protein'][0]
  ptdls = p['tdl_infos']
  if not p['dtoid']: p['dtoid'] = ''
  if not p['dtoclass']: p['dtoclass'] = ''
  if t['idg']:
    idg = 1
  else:
    idg = 0
  csv = [ t['id'], p['name'], p['description'], p['sym'], p['geneid'], p['uniprot'], p['stringid'], t['tdl'], idg, p['dtoid'], p['dtoclass'] ]
  if 'panther_classes' in p:
    csv.append( '|'.join(["%s:%s"%(d['pcid'],d['name']) for d in p['panther_classes']]) )
  else:
    csv.append('')
  if 'generifs' in p:
    csv.append( len(p['generifs']) )
  else:
    csv.append(0)
  if 'NCBI Gene PubMed Count' in ptdls:
    csv.append( ptdls['NCBI Gene PubMed Count']['value'] )
  else:
    csv.append(0)
  if 'JensenLab PubMed Score' in ptdls:
    csv.append( ptdls['JensenLab PubMed Score']['value'] )
  else:
    csv.append(0)  
  if 'PubTator Score' in ptdls:
    csv.append( ptdls['PubTator Score']['value'] )
  else:
    csv.append(0)
  csv.append( ptdls['Ab Count']['value'] )
  csv.append( ptdls['MAb Count']['value'] )
  # Activities
  if 'cmpd_activities' in t:
    csv.append( len(t['cmpd_activities']) )
  else:
    csv.append(0)
    #csv.append('')
  # ChEMBL
  if 'ChEMBL Selective Compound' in ttdls:
    csv.append( ttdls['ChEMBL Selective Compound']['value'] )
  else:
    csv.append('')
  if 'ChEMBL First Reference Year' in ttdls:
    csv.append( ttdls['ChEMBL First Reference Year']['value'] )
  else:
    csv.append('')
  # DrugCentral
  if 'drug_activities' in t:
    csv.append( len(t['drug_activities']) )
  else:
    csv.append(0)
    #csv.append('')
  # PDB
  if 'PDB' in p['xrefs']:
    pdbs = [d['value'] for d in p['xrefs']['PDB']]
    csv.append( len(pdbs) )
    csv.append( "|".join(pdbs) )
  else:
    csv.append(0)
    csv.append('')
  # GO
  if 'goas' in p:
    csv.append( len(p['goas']) )
  else:
    csv.append(0)
  if 'Experimental MF/BP Leaf Term GOA' in ptdls:
    csv.append( ptdls['Experimental MF/BP Leaf Term GOA']['value'] )
  else:
    csv.append(0)
  # Phenotypes
  if 'phenotypes' in p:
    omims = [d['trait'] for d in p['phenotypes'] if d['ptype'] == 'OMIM']
    if len(omims) > 0:
      csv.append( len(omims) )
      csv.append( "|".join(omims) )
    else:
      csv.append('')
      csv.append('')
    jaxs = ["%s:%s"%(d['term_id'],d['term_name']) for d in p['phenotypes'] if d['ptype'] == 'JAX/MGI Human Ortholog Phenotype']
    if jaxs:
      csv.append( len(jaxs) )
      csv.append( '|'.join(jaxs) )
    else:
      csv.append('')
      csv.append('')
  else:
    csv.append('')
    csv.append('')
    csv.append('')
    csv.append('')
  # IMPC phenotypes
  if 'impcs' in p:
    pts = ["%s:%s"%(d['term_id'],d['term_name']) for d in p['impcs']]
    csv.append( len(pts) )
    csv.append( '|'.join(pts) )
  else:
    csv.append('')
    csv.append('')
  # GWAS
  if 'gwases' in p:
    gwases = ["%s (%s):%s"%(d['disease_trait'],d['mapped_trait_uri'],d['p_value']) for d in p['gwases']]
    csv.append( len(gwases) )
    csv.append( '|'.join(gwases) )
  else:
    csv.append('')
    csv.append('')
  # Pathways
  if 'pathways' in p:
    pathways = ["%s:%s"%(d['pwtype'],d['name']) for d in p['pathways']]
    csv.append( len(pathways) )
    csv.append( "|".join(pathways) )
  else:
    csv.append('')
    csv.append('')
  # Diseases
  if 'diseases' in p:
    uniq = set( [d['name'] for d in p['diseases']] )
    csv.append( len(uniq) )
    # Top text-mining diseases
    tmdiseases = ["%s (ZScore: %s)"%(d['name'],str(d['zscore'])) for d in p['diseases'] if d['dtype'] == 'JensenLab Text Mining']
    if len(tmdiseases) > 0:
      csv.append( "|".join(tmdiseases[:5]) ) # Only top 5
    else:
      csv.append('')
    # eRAM diseases
    erams = [d for d in p['diseases'] if d['dtype'] == 'eRAM']
    if len(erams) > 0:
      csv.append( "|".join(["%s: %s"%(d['did'],d['name']) for d in erams]) )
    else:
      csv.append('')
  else:
    csv.append('')
    csv.append('')
    csv.append('')
  # Patent Count
  if 'EBI Total Patent Count' in ptdls:
    csv.append( ptdls['EBI Total Patent Count']['value'] )
  else:
    csv.append(0)
  # Is TF
  if 'Is Transcription Factor' in ptdls:
    csv.append(1)
  else:
    csv.append(0)
  if 'TMHMM Prediction' in ptdls:
    m = re.search(r'PredHel=(\d)', ptdls['TMHMM Prediction']['value'])
    if m:
      csv.append(m.groups()[0])
    else:
      csv.append(0)
  else:
    csv.append(0)
  # Tissue specificity
  if 'HPA Tissue Specificity Index' in ptdls:
    csv.append(ptdls['HPA Tissue Specificity Index']['value'])
  else:
    csv.append('')
  if 'HPM Gene Tissue Specificity Index' in ptdls:
    csv.append(ptdls['HPM Gene Tissue Specificity Index']['value'])
  else:
    csv.append('')
  if 'HPM Protein Tissue Specificity Index' in ptdls:
    csv.append(ptdls['HPM Protein Tissue Specificity Index']['value'])
  else:
    csv.append('')
  # TIN-X
  if 'tinx_novelty' in p:
    csv.append(p['tinx_novelty'])
  else:
    csv.append('')
  if 'tinx_importances' in p:
    # these come back ordered by score DESC. Only output top 5
    txis = ["%s: %s"%(d['disease'],str(d['score'])) for d in p['tinx_importances'][:5]]
    csv.append( "|".join(txis) )
  else:
    csv.append('')
  
  return csv

if __name__ == '__main__':
  main()

