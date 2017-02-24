#!/usr/bin/env python2
#############################################################################
# <DocumentSummary>
#   <Id>1159535</Id>
#   <ProteinTargetList>
#     <ProteinTarget>
#       <Name>ERAP1 protein [Homo sapiens]</Name>
#       <GI>21315078</GI>
#       <GeneSymbol>ERAP1</GeneSymbol>
#       <CddId>189008</CddId>
#       <CddName>M1_APN_2</CddName>
#       <CddDescription>Peptidase M1 Aminopeptidase N family incudes tricorn interacting factor F3</CddDescription>
#     </ProteinTarget>
#   </ProteinTargetList>
# </DocumentSummary>
#############################################################################
### Jeremy Yang
###  9 Feb 2017
#############################################################################
#
import sys,os,re,argparse,codecs

from xml.etree import ElementTree #newer
from xml.parsers import expat


#############################################################################
if __name__=='__main__':

  parser = argparse.ArgumentParser(
        description='eUtils PubChem Assay XML2CSV')
  ops = ['assaytargets']
  parser.add_argument("op",choices=ops,help='operation')
  parser.add_argument("--i",dest="ifile",help="input (XML)")
  parser.add_argument("--o",dest="ofile",help="output (CSV)")
  parser.add_argument("-v","--verbose", action="count")

  args = parser.parse_args()

  fin=codecs.open(args.ifile,"r","UTF-8","replace")

  if args.ofile:
    fout=codecs.open(args.ofile,"w","UTF-8","replace")
  else:
    fout=codecs.getwriter('utf8')(sys.stdout,errors="replace")

  fout.write('aid,tgt_gi,tgt_sym,tgt_species,tgt_name\n') #Python2
  #print('aid,tgt_gi,tgt_sym,tgt_species,tgt_name'.decode('utf-8'), file = fout)
  n_docsum=0; n_pt=0;
  for event, elem in ElementTree.iterparse(fin):
    if elem.tag=='DocumentSummary': docsum=elem
    else: continue
    n_docsum+=1

    aid=docsum.findtext('Id')
    pts = docsum.findall('ProteinTargetList/ProteinTarget')
    for pt in pts:
      name = pt.findtext('Name')
      species = re.sub(r'^.*\[(.*)\].*$', r'\1', name)
      name = re.sub(r'\s*\[.*\].*$', '', name)
      gi = pt.findtext('GI')
      sym = pt.findtext('GeneSymbol')
      fout.write('%s,%s,%s,%s,"%s"\n'%(aid,gi,sym,species,name)) #Python2
      #print(('%s,%s,%s,"%s","%s"'%(aid,gi,sym,species,name)).decode('utf-8'), file = fout)
      n_pt+=1

  fin.close()

  print >>sys.stderr, 'n_docsum: %d'%n_docsum
  print >>sys.stderr, 'n_pt: %d'%n_pt
