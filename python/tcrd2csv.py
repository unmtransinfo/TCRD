#!/usr/local/bin/python
# Time-stamp: <2018-06-21 10:06:50 smathias>
'''
tcrd2csv.py - Export TCRD target data to a CSV file
'''
__author__ = "Steve Mathias"
__email__ = "smathias@salud.unm.edu"
__org__ = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2014-2017, Steve Mathias"
__license__ = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__ = "2.0.1"

import sys
reload(sys)
sys.setdefaultencoding('utf8')
import os,argparse,re
from TCRD import DBAdaptor
import csv
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
DBNAME = 'tcrd'
OUTFILE = 'TCRD.csv'

def main():
  argparser = argparse.ArgumentParser(description="Export TCRD target data to a CSV file")
  argparser.add_argument("-o", "--outfile", help='Output file [path/]name', default=OUTFILE)
  argparser.add_argument('-db', '--dbname', help='MySQL database name', default=DBNAME)
  argparser.add_argument("-i", "--idg", help="Export only IDG Family tagets", action="store_true", default=False)
  argparser.add_argument("-f", "--family", help="Export only GPCR|Kinase|IC|NR targets. Only valid with --idg")
  argparser.add_argument("-e", "--expand", help="Export expanded (a LOT of data) CSV version", action="store_true", default=False)
  args = argparser.parse_args()
  if args.family and not args.idg:
    argparser.print_help()
    sys.exit()
  
  dba = DBAdaptor({'dbname': args.dbname})
  dbi = dba.get_dbinfo()
  print "\n%s (v%s) [%s]:" % (PROGRAM, __version__, time.strftime("%c"))
  print "\nConnected to TCRD database %s (schema ver %s, data ver %s)\n" % (dbi['dbname'], dbi['schema_ver'], dbi['data_ver'])

  pbar_widgets = ['Progress: ', Percentage(), ' ', Bar(marker='#',left='[',right=']'), ' ', ETA()]

  header = ['TCRD ID', 'DTO ID', 'DTO Family', 'DTO Family Ext.', 'TDL', 'Name', 'Description', 'HGNC Sym', 'NCBI Gene ID', 'UniProt', 'STRING ID', 'IDG Phase 2']
  if args.expand:
    header = header + ['Chr', 'UniProt Family', 'PANTHER Class(es)', 'DTO Classification', 'GeneRIF Count', 'NCBI Gene PubMed Count', 'JensenLab PubMed Score', 'PubTator Score', 'Ab Count', 'Monoclonal Ab Count', 'TIN-X Novelty Score', 'L1000 ID', 'ChEMBL Activity Count', 'ChEMBL Selective Compound', 'ChEMBL First Reference Year', 'DrugCentral Activity Count', 'PDB Count', 'PDBs', 'GO Annotation Count', 'Experimental MF/BP Leaf Term GOA(s)', 'OMIM Confirmed Phenotype(s)','GWAS Phenotype Count', 'GWAS Phenotype(s)', 'IMPC Phenotype Count', 'IMPC Phenotype(s)', 'JAX/MGI Human Ortholog Phenotype Count', 'JAX/MGI Human Ortholog Phenotype(s)', 'Pathway Count', 'Pathways', 'Disease Count', 'Top 5 Diseases', 'EBI Patent Count', 'Is Transcription Factor', 'TMHMM Prediction', 'Drugable Epigenome Class(es)', 'GTEx Tissue Specificity Index', 'HPA Protein Tissue Specificity Index', 'HPA RNA Tissue Specificity Index', 'HPM Gene Tissue Specificity Index', 'HPM Protein Tissue Specificity Index']

  if args.idg:
    if args.family:
      tct = dba.get_target_count(family=args.family)
      print "Exporting CSV for %d targets from TCRD to file %s" % (tct, args.outfile)
    else:
      tct = dba.get_target_count(idg=True)
      print "Exporting CSV for %d IDG Family targets from TCRD to file %s" % (tct, args.outfile)
  else:
    tct = dba.get_target_count(idg=False)
    print "Exporting CSV for all %d targets from TCRD to file %s" % (tct, args.outfile)

  pbar = ProgressBar(widgets=pbar_widgets, maxval=tct).start()
  with open(args.outfile, 'wb') as csvout:
    csvwriter = csv.writer(csvout, quotechar='"', quoting=csv.QUOTE_MINIMAL)
    csvwriter.writerow(header)
    ct = 0
    if args.idg:
      if args.family:
        for t in dba.get_targets(family=args.family, include_annotations=args.expand):
          ct += 1
          if args.expand:
            csvwriter.writerow( target2csv_exp(t) )
          else:
            csvwriter.writerow( target2csv(t) )
          pbar.update(ct)
      else:
        for t in dba.get_targets(idg=True, include_annotations=args.expand):
          ct += 1
          if args.expand:
            csvwriter.writerow( target2csv_exp(t) )
          else:
            csvwriter.writerow( target2csv_exp(t) )
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
  tid = t['id']
  p = t['components']['protein'][0]
  if not t['fam']: t['fam'] = ''
  if not t['famext']: t['famext'] = ''
  if not p['dtoid']: p['dtoid'] = ''
  if t['idg2']:
    idg2 = 1
  else:
    idg2 = 0
  csv = [ t['id'], p['dtoid'], t['fam'], t['famext'], t['tdl'], p['name'], p['description'], p['sym'], p['geneid'], p['uniprot'], p['stringid'], idg2 ]
  return csv

def target2csv_exp(t):
  tid = t['id']
  ttdls = {}
  if 'tdl_infos' in t:
    ttdls = t['tdl_infos']
  p = t['components']['protein'][0]
  ptdls = p['tdl_infos']
  if not t['fam']: t['fam'] = ''
  if not t['famext']: t['famext'] = ''
  if not p['dtoid']: p['dtoid'] = ''
  if t['idg2']:
    idg2 = 1
  else:
    idg2 = 0
  csv = [ t['id'], p['dtoid'], t['fam'], t['famext'], t['tdl'], p['name'], p['description'], p['sym'], p['geneid'], p['uniprot'], p['stringid'], idg2, p['chr'], p['family'] ]
  if 'panther_classes' in p:
    pcs = ["%s:%s"%(d['pcid'],d['name']) for d in p['panther_classes']]
    csv.append( '|'.join(pcs) )
  else:
    csv.append('')
  if 'dto_classification' in p:
    csv.append( p['dto_classification'] )
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
  if 'tinx_novelty' in p:
    csv.append( p['tinx_novelty'] )
  else:
    csv.append('')
  if 'L1000 ID' in p['xrefs']:
    csv.append( p['xrefs']['L1000 ID'][0]['value'] )
  else:
    csv.append('')
  # ChEMBL
  if 'chembl_activities' in t:
    csv.append( len(t['chembl_activities']) )
    #best_ca = t['chembl_activities'][0]
    #csv.append("%s|%s"%(best_ca['cmpd_name_in_ref'],best_ca['cmpd_chemblid']))
  else:
    csv.append(0)
    #csv.append('')
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
    #best_da = t['drug_activities'][0]
    #csv.append("%s|%s"%(best_da['cmpd_name_in_ref'],best_da['cmpd_chemblid']))
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
      csv.append( "|".join(omims) )
    else:
      csv.append('')
  else:
    csv.append('')
  if 'phenotypes' in p:
    pts = ["%s|%s(PMID: %d)"%(d['snps'],d['trait'],d['pmid']) for d in p['phenotypes'] if d['ptype'] == 'GWAS Catalog']
    if pts:
      csv.append( len(pts) )
      csv.append( '|'.join(pts) )
    else:
      csv.append('')
      csv.append('')
    pts = ["%s:%s(%s:%s)"%(d['term_id'],d['term_name'],d['statistical_method'],d['effect_size']) for d in p['phenotypes'] if d['ptype'] == 'IMPC']
    if pts:
      csv.append( len(pts) )
      csv.append( '|'.join(pts) )
    else:
      csv.append('')
      csv.append('')
    pts = ["%s:%s"%(d['term_id'],d['term_name']) for d in p['phenotypes'] if d['ptype'] == 'JAX/MGI Human Ortholog Phenotype']
    if pts:
      csv.append( len(pts) )
      csv.append( '|'.join(pts) )
    else:
      csv.append('')
      csv.append('')
  else:
    csv.append('')
    csv.append('')
    csv.append('')
    csv.append('')
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
  if 'diseases' in t:
    diseases = ["%s (ZScore: %s)"%(d['name'],str(d['zscore'])) for d in t['diseases'] if d['dtype'] == 'JensenLab Text Mining']
    csv.append( len(diseases) )
    csv.append( "|".join(diseases[:5]) ) # Only top 5
  else:
    csv.append('')
    csv.append('')
  # # Grant Info
  # if 'grants' in t:
  #   csv.append( len(t['grants']) )
  #   csv.append( "%.2f"%sum([float(d['cost']) for d in t['grants']]) )
  #   csv.append( len([d for d in t['grants'] if d['activity'] == 'R01']) )
  #   csv.append( "%.2f"%sum([float(d['cost']) for d in t['grants'] if d['activity'] == 'R01']) )
  #   csv.append( len([d for d in t['grants'] if int(d['year']) > 2010]) )
  #   csv.append( "%.2f"%sum([float(d['cost']) for d in t['grants'] if int(d['year']) > 2010]) )
  #   csv.append( len([d for d in t['grants'] if (d['activity'] == 'R01' and int(d['year']) > 2010)]) )
  #   csv.append( "%.2f"%sum([float(d['cost']) for d in t['grants'] if (d['activity'] == 'R01' and int(d['year']) > 2010)]) )
  # else:
  #   csv.append('')
  #   csv.append('')
  #   csv.append('')
  #   csv.append('')
  #   csv.append('')
  #   csv.append('')
  #   csv.append('')
  #   csv.append('')
  # Patent Count
  if 'EBI Total Patent Count' in ptdls:
    csv.append( ptdls['EBI Total Patent Count']['value'] )
  else:
    csv.append(0)
  # # MLP Assay Info
  # if 'mlp_assay_infos' in p:
  #   csv.append( len(p['mlp_assay_infos']) )
  #   csv.append( "|".join([d['assay_name'] for d in p['mlp_assay_infos']]) )
  # else:
  #   csv.append(0)
  #   csv.append('')
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
  # Drugable Epigenome Class(es)
  if 'Drugable Epigenome Class' in ptdls:
    csv.append( "|".join([d['value'] for d in ptdls['Drugable Epigenome Class']]) )
  else:
    csv.append('')
  # Tissue specificity
  if 'GTEx Tissue Specificity Index' in ptdls:
    csv.append(ptdls['GTEx Tissue Specificity Index']['value'])
  else:
    csv.append('')
  if 'HPA Protein Tissue Specificity Index' in ptdls:
    csv.append(ptdls['HPA Protein Tissue Specificity Index']['value'])
  else:
    csv.append('')
  if 'HPA RNA Tissue Specificity Index' in ptdls:
    csv.append(ptdls['HPA RNA Tissue Specificity Index']['value'])
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
  
  return csv

if __name__ == '__main__':
  main()

