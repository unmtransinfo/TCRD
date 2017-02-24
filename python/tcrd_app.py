#!/usr/bin/env python
'''\
TCRD client utility

Jeremy Yang
21 Apr 2015
'''
import os,sys,getopt,re,time,logging,codecs
import json,types

import csv_utils

import TCRD
import tcrd_adaptor_utils

PROG=os.path.basename(sys.argv[0])

#DBHOST='habanero.health.unm.edu'
DBHOST='juniper.health.unm.edu'
DBNAME='tcrd'
#DBNAME='tcrdev'
DBUSER='jjyang'
LOGFILE='/tmp/TCRD-DBA.log'
#
#############################################################################
if __name__=='__main__':

  usage='''
  %(PROG)s - TCRD client utility

operations:
  --info ................... db info
  --tdl_counts ............. target development level counts
  --idgfam_counts .......... IDG protein family counts
  --list_targets ........... list targets, optionally for specified TDL
  --list_xref_types ........ list xref types
  --find_targets ........... find targets for query (symbol, ID, etc.)
  --find_targets_by_xref ... find targets for query (xref)

query:
  --query QRY .............. query
  --qfile QFILE ............ input query file
  --qtype QTYPE ............ %(QTYPE)s

  query types:
    TID .................... TCRD target ID (e.g. 1, 2, 3)
    GENEID ................. NCBI Entrez gene ID (e.g. 7529,10971)
    UNIPROT ................ Uniprot ID (e.g. Q04917,P04439)
    GENESYMB ............... HUGO gene symbol (e.g. GPER1, HLA-A,YWHAG)

parameters:
  --tdl TDL ................ %(TDLS)s
  --idgfam IDGFAM .......... %(IDGFAM)s
  --idgfam_only ............ only return IDGFAM targets

options:
  --o OFILE ................ output file (CSV)
  --dbname DBNAME .......... [%(DBNAME)s]
  --dbhost DBHOST .......... [%(DBHOST)s]
  --dbuser DBUSER .......... [%(DBUSER)s]
  --dbpwfile DBPWFILE ......
  --logfile LOG ............ [%(LOGFILE)s]
  --expand ................. expanded output (server)
  --v[v[v]] ................ verbose [very [very]]
  --h ...................... this help
'''%{'PROG':PROG,'DBNAME':DBNAME,'DBHOST':DBHOST,'DBUSER':DBUSER,
	'IDGFAM':('|'.join(tcrd_adaptor_utils.IDGFAM)),
	'TDLS':('|'.join(tcrd_adaptor_utils.TDLS)),
	'QTYPE':('|'.join(sorted(tcrd_adaptor_utils.QTYPE.keys()))),
	'LOGFILE':LOGFILE}

  def ErrorExit(msg):
    print >>sys.stderr,msg
    sys.exit(1)

  query=None; ofile=None; qfile=None;
  verbose=0; expand=False;
  info=False; test=False;
  tdl_counts=False; idgfam_counts=False;
  idgfam_only=False;
  list_targets=False;
  list_xref_types=False;
  find_targets=False;
  find_targets_by_xref=False;
  tdl=None; idgfam=None;
  query=None; qtype=None;
  opts,pargs = getopt.getopt(sys.argv[1:],'',['h','v','vv','vvv','expand',
	'o=', 'query=', 'qfile=', 'qtype=', 'tdl=', 'idgfam=',
	'info', 'test','tdl_counts','idgfam_counts','idgfam_only',
	'list_targets',
	'list_xref_types',
	'find_targets',
	'find_targets_by_xref',
	'dbname=', 'dbhost=', 'dbuser=', 'dbpw=' ])
  if not opts: ErrorExit(usage)
  for (opt,val) in opts:
    if opt=='--h': ErrorExit(usage)
    elif opt=='--o': ofile=val
    elif opt=='--qfile': qfile=val
    elif opt=='--query': query=val
    elif opt=='--qtype': qtype=val
    elif opt=='--info': info=True
    elif opt=='--test': test=True
    elif opt=='--tdl_counts': tdl_counts=True
    elif opt=='--idgfam_counts': idgfam_counts=True
    elif opt=='--idgfam_only': idgfam_only=True
    elif opt=='--list_targets': list_targets=True
    elif opt=='--list_xref_types': list_xref_types=True
    elif opt=='--find_targets': find_targets=True
    elif opt=='--find_targets_by_xref': find_targets_by_xref=True
    elif opt=='--tdl': tdl=val
    elif opt=='--idgfam': idgfam=val
    elif opt=='--dbname': DBNAME=val
    elif opt=='--dbhost': DBHOST=val
    elif opt=='--dbuser': DBUSER=val
    elif opt=='--dbpw': DBPW=val
    elif opt=='--expand': expand=True
    elif opt=='--v': verbose=1
    elif opt=='--vv': verbose=2
    elif opt=='--vvv': verbose=3
    else: ErrorExit('Illegal option: %s'%val)

  if ofile:
    fout=codecs.open(ofile,"w","utf8","replace")
    if not fout: ErrorExit('ERROR: cannot open outfile: %s'%ofile)
  else:
    fout=codecs.getwriter('utf8')(sys.stdout,errors="replace")

  if idgfam and idgfam not in tcrd_adaptor_utils.IDGFAM:
    ErrorExit('Illegal idgfam: "%s"; allowed values: %s'%(idgfam,('|'.join(tcrd_adaptor_utils.IDGFAM))))

  querys=[]
  if qfile:
    fin=open(qfile)
    if not fin: ErrorExit('ERROR: cannot open qfile: %s'%qfile)
    while True:
      line=fin.readline()
      if not line: break
      try:
        querys.append(line.rstrip())
      except:
        print >>sys.stderr, 'ERROR: bad input ID: %s'%line
        continue
    if verbose:
      print >>sys.stderr, '%s: input IDs: %d'%(PROG,len(querys))
    fin.close()
  elif query:
    querys.append(query)

  if test: verbose=3

  if tdl and tdl not in tcrd_adaptor_utils.TDLS:
    ErrorExit('Invalid tdl "%s".  Allowed tdls: %s'%(tdl,('|'.join(tcrd_adaptor_utils.TDLS))))


  loglev = (logging.DEBUG if verbose>1 else (logging.WARNING if verbose==1 else logging.ERROR))
  PWFILE = os.environ['HOME']+'/.dbirc_tcrd'
  dba = TCRD.DBAdaptor({ 'dbhost':DBHOST, 'dbname':DBNAME, 'dbuser':DBUSER, 'pwfile':PWFILE, 'loglevel':loglev })

  if info:
    for key,val in dba.get_dbinfo().items():
      print '%12s: %s'%(key,val)

  elif test:
    dba.test()

  elif tdl_counts:
    n_grand_total=0
    n_grand_total_idgfam=0
    for tdl in tcrd_adaptor_utils.TDLS:
      n_total = dba.get_tdl_target_count(tdl,idg=idgfam_only,family=False)    
      n_total_idgfam = dba.get_tdl_target_count(tdl,idg=True,family=False)    
      print "%6s:"%(tdl)
      for idgfam in tcrd_adaptor_utils.IDGFAM:
        n = dba.get_tdl_target_count(tdl,idg=idgfam_only,family=idgfam)    
        print "\t%6s: %6d (%4.1f%%)"%(idgfam,n,100.0*n/n_total)
      print "\t%6s: %6d"%('idgfam total',n_total_idgfam)
      print "\t%6s: %6d"%('total',n_total)
      n_grand_total+=n_total
      n_grand_total_idgfam+=n_total_idgfam
    print "\t%6s: %6d"%('idgfam grand total',n_grand_total_idgfam)
    print "\t%6s: %6d"%('grand total',n_grand_total)

  elif idgfam_counts:
    for idgfam in tcrd_adaptor_utils.IDGFAM:
      n_total = dba.get_target_count(idg=(idgfam_only or idgfam),family=idgfam)    
      print "%6s:"%(idgfam)
      for tdl in tcrd_adaptor_utils.TDLS:
        n = dba.get_tdl_target_count(tdl,idg=(idgfam_only or idgfam),family=idgfam)    
        print "\t%6s: %6d (%4.1f%%)"%(tdl,n,100.0*n/n_total)
      print "\t%6s: %6d"%('total',n_total)

  elif list_targets and tdl!=None:
    n=0;
    fout.write((','.join(tcrd_adaptor_utils.TAGS+map(lambda s:'protein:'+s,tcrd_adaptor_utils.PROTEIN_TAGS)))+'\n')
    #for tgt in dba.get_targets(idg=idgfam_only,family=idgfam,include_annotations=expand):
    for tgt in dba.get_tdl_targets(tdl,idg=(idgfam_only or idgfam),family=idgfam,include_annotations=expand):
      n+=1
      rows = tcrd_adaptor_utils.Target2Rows(tgt,True)
      for row in rows:
        fout.write((','.join(map(lambda v: csv_utils.ToStringForCSV(v),row)))+'\n')
    print >>sys.stderr, 'target count: %d'%n

  elif list_targets:
    n=0;
    fout.write((','.join(tcrd_adaptor_utils.TAGS+map(lambda s:'protein:'+s,tcrd_adaptor_utils.PROTEIN_TAGS)))+'\n')
    for tgt in dba.get_targets(idg=idgfam_only,family=idgfam,include_annotations=expand):
      n+=1
      rows = tcrd_adaptor_utils.Target2Rows(tgt,True)
      for row in rows:
        fout.write((','.join(map(lambda v: csv_utils.ToStringForCSV(v),row)))+'\n')
    print >>sys.stderr, 'target count: %d'%n

  elif list_xref_types:
    for xreftype in dba.get_xref_types():
      fout.write('\t"%s"\n'%xreftype)

  elif find_targets:
    if not qtype or qtype.lower() not in tcrd_adaptor_utils.QTYPE.keys():
      ErrorExit('Invalid qtype "%s".  Allowed qtypes: %s'%(qtype,('|'.join(tcrd_adaptor_utils.QTYPE.keys()))))
    elif qtype.lower()=='tid':
      tgt = dba.get_target(query,include_annotations=expand)
      if tgt:
        fout.write(json.dumps(tgt,indent=2,sort_keys=False)+'\n')
      else:
        print >>sys.stderr, 'target not found, TID = %s'%query
    else:
      tcrd_adaptor_utils.FindTargets(dba,querys,qtype,idgfam_only,expand,fout,verbose)

  elif find_targets_by_xref:
    xreftypes = list(dba.get_xref_types())
    if qtype not in xreftypes:
      ErrorExit('Invalid qtype "%s".  Allowed xref qtypes: %s'%(qtype,('|'.join(xreftypes))))
    tcrd_adaptor_utils.FindTargetsByXref(dba,querys,qtype,idgfam_only,expand,fout,verbose)

  else:
    ErrorExit('ERROR: No operation specified.')

