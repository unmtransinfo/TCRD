#!/usr/bin/env python
'''\
TCRD utility functions

author: Jeremy Yang
11 Dec 2014
'''
#############################################################################
import os,sys,re,time,json,types

import TCRD

TDLS=[ 'Tdark', 'Tbio', 'Tchem', 'Tclin' ]
#
IDGFAM=['GPCR','IC','Kinase','NR','oGPCR']
#
### Keys defined here, values defined (as keys) in TCRD.py.
QTYPE={
	'tid':'TCRD Target ID',
	'genesymb':'sym',
	'uniprot':'uniprot',
	'geneid':'geneid'
	}
TAGS=[
	'id',
	'name',
	#'description',
	'idgfam',
	'tdl',
	'ttype',
	'uri'
	]
PROTEIN_TAGS=[
	'id',
	'name',
	#'description',
	#'comment',
	#'seq',
	'geneid',
	'sym',
	'chr',
	'uniprot',
	'up_version',
	'family'
	]

#############################################################################
def CheckQuery(qtxt):
  try:
    query = json.loads(qtxt)
  except Exception,e:
    return False
  if not query: return False
  elif type(query) is not types.DictType: return False
  elif not query.keys(): return False
  return True

#############################################################################
def HTTPErrorExit(code,msg):
  print 'Status: %d %s'%(code,msg)
  print "Content-type: text/plain\n"
  print 'ERROR: (%d) %s'%(code,msg)
  sys.exit(1)

#############################################################################
def Target2Rows(tgt,expanded):
  '''Convert target to CSV row[s], one per component.'''
  tgt_name = tgt['name'] if tgt.has_key('name') else None     
  proteins = tgt['components']['protein'] if (tgt.has_key('components') and tgt['components'].has_key('protein')) else []
  rows=[]; row=[];
  for tag in TAGS:
    val = tgt[tag] if tgt.has_key(tag) else ''
    row.append(val)
  for protein in proteins:
    row_pro = []
    for tag in PROTEIN_TAGS:
      val = protein[tag] if protein.has_key(tag) else ''     
      row_pro.append(val)
    rows.append(row+row_pro)
  return rows

#############################################################################
def FindTargets(dba,querys,qtype,idgfam_only,expand,fout,verbose):
  n_query=0; n_tgt=0; n_prot=0; n_out=0; tags=[]; tags_protein=[];
  n_notfound=0;
  tags_skip = [ 'components', 'comment', 'description', 'seq' ]

  for query in querys:
    n_query+=1
    q = { QTYPE[qtype.lower()]:query }
    n_tgt_this=0;
    n_prot_this=0;
    try:
      for tgt in dba.find_targets(q,idg=idgfam_only,include_annotations=expand):
        n_tgt_this+=1
        n_tgt+=1

        if verbose>1: print >>sys.stderr, (json.dumps(tgt,indent=2,sort_keys=False))
        if not tags:
          tags=sorted(tgt.keys())
          for tag in tags_skip:
            if tag in tags: tags.remove(tag)
        proteins = tgt['components']['protein'] if (tgt.has_key('components') and tgt['components'].has_key('protein')) else []
        if not tags_protein and len(proteins)>0:
          tags_protein = sorted(proteins[0].keys())
          for tag in tags_skip:
            if tag in tags_protein: tags_protein.remove(tag)

        if tags and tags_protein and n_out==0:
          fout.write(','.join(map(lambda s:'"%s"'%s,['query','i_hit']+tags+map(lambda s:'protein:%s'%s,tags_protein)))+'\n')
        if not (tags and tags_protein):
          continue

        vals = [(tgt[tag] if tgt.has_key(tag) else '') for tag in tags]
        if len(proteins)==0:
          fout.write(','.join(map(lambda s:'"%s"'%s,[query,'1']+vals+['' for tag in tags_protein]))+'\n')
          n_out+=1
        else:
          for protein in proteins:
            n_prot_this+=1
            n_prot+=1
            vals_protein = [(protein[tag] if protein.has_key(tag) else '') for tag in tags_protein]
            fout.write(','.join(map(lambda s:'"%s"'%s,[query,str(n_prot_this)]+vals+vals_protein))+'\n')
            n_out+=1
    except Exception,e:
      print >>sys.stderr, 'ERROR: query[%d]="%s": %s'%(n_query,query,str(e))

    if n_tgt_this==0:
      #fout.write(','.join(map(lambda s:'"%s"'%s,[query,'0']+['' for tag in tags+tags_protein]))+'\n')
      n_notfound+=1

    if verbose>1:
      print >>sys.stderr, '%d. q = %s ; targets found: %d ; proteins found: %d'%(n_query,str(q),n_tgt_this,n_prot_this)

  print >>sys.stderr, 'querys: %d ; notfound: %d ; targets found: %d ; proteins found: %d ; rows out: %d'%(n_query,n_notfound,n_tgt,n_prot,n_out)

#############################################################################
def FindTargetsByXref(dba,querys,qtype,idgfam_only,expand,fout,verbose):
  n_query=0; n_tgt=0; n_prot=0; n_out=0; tags=[]; tags_protein=[];
  n_notfound=0;
  tags_skip = [ 'components', 'comment', 'description', 'seq' ]
  for query in querys:
    n_query+=1
    n_tgt_this=0;
    n_prot_this=0;
    try:
      q = {'xtype':qtype,'value':query}
      for tgt in dba.find_targets_by_xref(q,idg=idgfam_only,include_annotations=expand):
        n_tgt_this+=1
        n_tgt+=1
        if verbose>1 and type(tgt) is types.DictType:
          print >>sys.stderr, (json.dumps(tgt,indent=2,sort_keys=False))
        if not tags:
          tags=sorted(tgt.keys())
          for tag in tags_skip:
            if tag in tags: tags.remove(tag)
        proteins = tgt['components']['protein'] if (tgt.has_key('components') and tgt['components'].has_key('protein')) else []
        if not tags_protein and len(proteins)>0:
          tags_protein = sorted(proteins[0].keys())
          for tag in tags_skip:
            if tag in tags_protein: tags_protein.remove(tag)

        if tags and tags_protein and n_out==0:
          fout.write(','.join(map(lambda s:'"%s"'%s,['query','i_hit']+tags+tags_protein))+'\n')
        if not (tags and tags_protein):
          continue

        vals = [(tgt[tag] if tgt.has_key(tag) else '') for tag in tags]
        if len(proteins)==0:
          fout.write(','.join(map(lambda s:'"%s"'%s,[query,'1']+vals+['' for tag in tags_protein]))+'\n')
          n_out+=1
        else:
          for protein in proteins:
            n_prot_this+=1
            n_prot+=1
            vals_protein = [(protein[tag] if protein.has_key(tag) else '') for tag in tags_protein]
            fout.write(','.join(map(lambda s:'"%s"'%s,[query,str(n_prot_this)]+vals+vals_protein))+'\n')
            n_out+=1
    except Exception,e:
      print >>sys.stderr, 'ERROR: query[%d]="%s": %s'%(n_query,query,str(e))

    if n_tgt_this==0:
      #fout.write(','.join(map(lambda s:'"%s"'%s,[query,'0']+['' for tag in tags+tags_protein]))+'\n')
      n_notfound+=1

    if verbose>1:
      print >>sys.stderr, '%d. q = %s ; targets found: %d ; proteins found: %d'%(n_query,str(q),n_tgt_this,n_prot_this)

  print >>sys.stderr, 'querys: %d ; notfound: %d ; targets found: %d ; proteins found: %d ; rows out: %d'%(n_query,n_notfound,n_tgt,n_prot,n_out)

#############################################################################
