#!/usr/bin/env python
#############################################################################
### csv2sql.py - Convert CSV to INSERTS for a specified table, with
### control over column names, datatypes, and database systems (dbsystem).
###
### Jeremy Yang
###  12 May 2016
#############################################################################
import sys,os,getopt,re,codecs
import csv

PROG=os.path.basename(sys.argv[0])
#
DBSYSTEMS=['postgres','mysql','oracle','derby']
#
MAXCHAR=1024
#
CHARTYPES=('CHAR','CHARACTER','VARCHAR')
NUMTYPES=('INT','BIGINT','FLOAT','NUM')
TIMETYPES=('DATE','TIMESTAMP')
#
NULLWORDS=['NULL','UNSPECIFIED','MISSING','UNKNOWN']
#
#
#############################################################################
def CsvCheck(fin,dbsystem,noheader,maxchar,delim,qc,verbose):
  csvReader=csv.reader(fin,dialect='excel',delimiter=delim,quotechar=qc) 
  colnames=None

  n_in=0;
  n_err=0;
  while True:
    try:
      row=csvReader.next()
      n_in+=1
    except Exception,e:
      print >>sys.stderr, '%s'%str(e)
      break
    if n_in==1 or not colnames:
      if noheader:
        prefix = re.sub(r'\..*$','',os.path.basename(fin.name))
        colnames = ['%s_%d'%(prefix,j) for j in range(1,1+len(row))]
      else:
        colnames = row[:]
      for j,tag in enumerate(colnames):
        print >>sys.stderr, 'Column tag %d: "%s"'%(j+1,tag)
      colnames_clean = CleanNames(colnames[:],'')
      DedupNames(colnames_clean)
      for j,tag in enumerate(colnames_clean):
        print >>sys.stderr, 'Cleaned column tag %d: "%s"'%(j+1,tag)
      nval = {colname:0 for colname in colnames}
      maxlen = {colname:0 for colname in colnames}

    for j in range(len(row)):
      val=row[j]
      if j<=len(colnames):
        colname = colnames[j]
      else:
        print >>sys.stderr,'ERROR [%d] row j_col>len(colnames) %d>%d'%(n_in,j,len(colnames))
        n_err+=1
      try:
        val=val.encode('ascii','replace')
      except Exception,e:
        print >>sys.stderr,'ERROR [%d] %s'%(n_in,str(e))
        val='%s:ENCODING_ERROR'%PROG
        n_err+=1

      if val.strip(): nval[colname]+=1
      val = EscapeString(val,False,dbsystem)

      maxlen[colname] = max(maxlen[colname],len(val))

      if len(val)>maxchar:
        val=val[:maxchar]
        print >>sys.stderr, 'WARNING: [row=%d] string length>MAXCHAR (%d>%d)'%(n_in,len(val),maxchar)

  for j,tag in enumerate(colnames):
    print >>sys.stderr,'%d. "%s":'%(j+1,tag)
    print >>sys.stderr,'\tnval = %6d'%(nval[tag])
    print >>sys.stderr,'\tmaxlen = %6d'%(maxlen[tag])

  print >>sys.stderr, "n_in: %d"%(n_in)
  print >>sys.stderr, "n_err: %d"%(n_err)

#############################################################################
def Csv2Create(fin,fout,dbsystem,dtypes,schema,tablename,colnames,prefix,noheader,coltypes,fixtags,delim,qc,verbose):
  csvReader=csv.DictReader(fin,fieldnames=None,dialect='excel',delimiter=delim,quotechar=qc) 
  if colnames:
    if len(colnames) != len(csvReader.fieldnames):
      print >>sys.stderr, 'ERROR: #colnames)!=#fieldnames (%d!=%d)'%(len(colnames),len(csvReader.fieldnames))
      return
    csvReader.fieldnames = colnames
  else:
    colnames = csvReader.fieldnames[:]
    if fixtags:
      CleanNames(colnames,prefix)
      DedupNames(colnames)
  if coltypes:
    if len(coltypes) != len(csvReader.fieldnames):
      print >>sys.stderr, 'ERROR: #coltypes!=#fieldnames (%d!=%d)'%(len(coltypes),len(csvReader.fieldnames))
      return
    for j in range(len(coltypes)):
      if not coltypes[j]: coltypes[j] = 'CHAR'
  else:
    coltypes = ['CHAR' for i in range(len(colnames))]
  if dbsystem=='mysql':
    sql='CREATE TABLE %s (\n\t'%(tablename)
  else:
    sql='CREATE TABLE %s.%s (\n\t'%(schema,tablename)
  sql+=(',\n\t'.join(('%s %s'%(colnames[j],dtypes[dbsystem][coltypes[j]])) for j in range(len(colnames))))
  sql+=('\n);')
  if dbsystem=='postgres':
    sql+="\nCOMMENT ON TABLE %s.%s IS 'Created by %s.';"%(schema,tablename,PROG)
  fout.write(sql+'\n')
  print >>sys.stderr, "%s: output SQL CREATE written, columns: %d"%(PROG,len(colnames))
  return colnames

#############################################################################
def Csv2Insert(fin,fout,dbsystem,schema,tablename,colnames,prefix,noheader,coltypes,nullify,fixtags,maxchar,delim,qc,skip,nmax,verbose):
  n_in=0; n_out=0; n_err=0;
  csvReader=csv.DictReader(fin,fieldnames=None,dialect='excel',delimiter=delim,quotechar=qc) 
  if colnames:
    if len(colnames) != len(csvReader.fieldnames):
      print >>sys.stderr, 'ERROR: #colnames!=#fieldnames (%d!=%d)'%(len(colnames),len(csvReader.fieldnames))
      return
    csvReader.fieldnames = colnames
  else:
    colnames = csvReader.fieldnames[:]
    if fixtags:
      CleanNames(colnames,prefix)
      DedupNames(colnames)
  if coltypes:
    if len(coltypes) != len(csvReader.fieldnames):
      print >>sys.stderr, 'ERROR: #coltypes!=$fieldnames (%d!=%d)'%(len(coltypes),len(csvReader.fieldnames))
      return
  else:
    coltypes = ['CHAR' for i in range(len(colnames))]
  for j in range(len(coltypes)):
    if not coltypes[j]: coltypes[j]='CHAR'
  while True:
    try:
      row=csvReader.next()
      n_in+=1
    except Exception,e:
      print >>sys.stderr, '%s'%str(e)
      break
    if n_in<=skip: continue
    if dbsystem=='mysql':
      line = ('INSERT INTO %s (%s) VALUES ('%(tablename,','.join(colnames)))
    else:
      line = ('INSERT INTO %s.%s (%s) VALUES ('%(schema,tablename,','.join(colnames)))
    for j,colname in enumerate(csvReader.fieldnames):
      val=row[colname]
      try:
        #val=codecs.encode(val,'ascii','replace') #same
        val=val.encode('ascii','replace')
      except Exception,e:
        print >>sys.stderr,'%s'%str(e)
        val='%s:ENCODING_ERROR'%PROG
      if coltypes[j].upper() in CHARTYPES:
        val = EscapeString(val,nullify,dbsystem)
        if len(val)>maxchar:
          val=val[:maxchar]
          print >>sys.stderr, 'WARNING: [row=%d] string truncated to %d chars: "%s"'%(n_in,maxchar,val)
        val = ("'%s'"%val)
      elif coltypes[j].upper() in NUMTYPES:
        val = 'NULL' if (val.upper() in NULLWORDS or val=='') else ('%s'%val)
      elif coltypes[j].upper() in TIMETYPES:
        val = ("to_timestamp('%s')"%val)
      else:
        print >>sys.stderr, 'ERROR: no type specified or implied: (col=%d)'%(j+1)
        continue
      line+=('%s%s'%((',' if j>0 else ''),val))
    line +=(') ;')
    fout.write(line+'\n')
    n_out+=1
    if n_in==nmax: break
  print >>sys.stderr, "%s: input CSV lines: %d"%(PROG,n_in)
  print >>sys.stderr, "%s: output SQL inserts: %d"%(PROG,n_out)

#############################################################################
def CleanName(name):
  '''Clean table or col name for use without escaping.
1. Downcase.
2. Replace spaces and colons with underscores.
3. Remove punctuation and special chars.
4. Prepend leading numeral.
5. Truncate to 50 chars.
'''
  name_clean = re.sub(r'[\s:-]+','_',name.lower())
  name_clean = re.sub(r'[^\w]','',name_clean)
  name_clean = re.sub(r'^([\d])',r'col_\1',name_clean)
  name_clean = name_clean[:50]
  return name_clean

#############################################################################
def CleanNames(colnames,prefix):
  for j in range(len(colnames)):
    colnames[j] = CleanName(prefix+colnames[j] if prefix else colnames[j])
  return colnames

#############################################################################
def DedupNames(colnames):
  unames = set()
  for j in range(len(colnames)):
    if colnames[j] in unames:
      colname_orig = colnames[j]
      k=1
      while colnames[j] in unames:
        k+=1
        colnames[j] = '%s_%d'%(colname_orig,k)
    unames.add(colnames[j])
  return colnames

#############################################################################
def EscapeString(val,nullify,dbsystem):
  val=re.sub(r"'",'',val)
  if dbsystem=='postgres':
    val=re.sub(r'\\',r"'||E'\\\\'||'",val)
  elif dbsystem=='mysql':
    val=re.sub(r'\\',r'\\\\',val)
  if val.strip()=='' and nullify: val='NULL'
  return val

#############################################################################
if __name__=='__main__':
  schema='public';
  dbsystem='postgres';
  quotechar='"';
  usage='''
  %(PROG)s - CSV to SQL CREATEs or INSERTs

operations:
	--insert ..................... output INSERT statements
	--create ..................... output CREATE statements
	--check ...................... check input file, profile columns
options:
	--i INFILE ................... input CSV [stdin]
	--o OUTFILE .................. output SQL INSERTs [stdout]
	--schema SCHEMA .............. (Postgres schema, or MySql db) [%(SCHEMA)s]
	--tablename TABLE ............ table [convert filename]
	--prefix_tablename PREFIX .... prefix + [convert filename]
	--dbsystem DBSYSTEM .......... %(DBSYSTEMS)s [%(DBSYSTEM)s]
	--colnames COLNAMES .......... comma-separated [default: CSV tags]
	--noheader .............. auto-name columns
	--prefix_colnames PREFIX ..... prefix CSV tags
	--coltypes COLTYPES .......... comma-separated, CHAR|INT|FLOAT|NUM|BOOL [default: all CHAR]
	--nullify .................... CSV missing CHAR value converts to NULL
	--nullwords NULLWORDS ........ words synonymous with NULL [%(NULLWORDS)s]
	--maxchar MAXCHAR ............ max string length [%(MAXCHAR)s]
	--fixtags .................... tags to colnames (downcase/nopunct/nospace)
	--tsv ........................ input file TSV
	--delim DELIM ................ use if not comma or tab
	--quotechar C ................ [%(QUOTECHAR)s]
	--skip N ..................... skip N records (--insert only)
	--nmax N ..................... max N records (--insert only)
	--v .......................... verbose
	--h .......................... this help
'''%{	'PROG':PROG,
	'DBSYSTEMS':('|'.join(DBSYSTEMS)),
	'DBSYSTEM':dbsystem,
	'MAXCHAR':MAXCHAR,
	'QUOTECHAR':quotechar,
	'NULLWORDS':(','.join(NULLWORDS)),
	'SCHEMA':schema
	}

  def ErrorExit(msg):
    print >>sys.stderr,msg
    sys.exit(1)

  check=False;
  insert=False;
  create=False;
  delim=',';
  tablename=None;
  prefix_tablename='';
  ifile=None; ofile=None; 
  verbose=0;
  nmax=0;
  skip=0;
  colnames=None;
  prefix_colnames=None;
  coltypes=None;
  fixtags=False;
  noheader=False;
  nullify=False;
  nullwords=None;
  opts,pargs = getopt.getopt(sys.argv[1:],'',['h','v','vv',
	'i=','o=',
	'dbsystem=',
	'maxchar=',
	'tsv',
	'nullify',
	'nullwords=',
	'fixtags',
	'noheader',
	'insert',
	'check',
	'create',
	'prefix_colnames=',
	'colnames=',
	'coltypes=',
	'delim=',
	'quotechar=',
	'schema=',
	'tablename=',
	'prefix_tablename=',
	'nmax=',
	'skip='
	])
  if not opts: ErrorExit(usage)
  for (opt,val) in opts:
    if opt=='--h': ErrorExit(usage)
    elif opt=='--i': ifile=val
    elif opt=='--o': ofile=val
    elif opt=='--insert': insert=True
    elif opt=='--check': check=True
    elif opt=='--create': create=True
    elif opt=='--tablename': tablename=val
    elif opt=='--prefix_tablename': prefix_tablename=val
    elif opt=='--schema': schema=val
    elif opt=='--dbsystem': dbsystem=val
    elif opt=='--maxchar': MAXCHAR=int(val)
    elif opt=='--colnames': colnames=re.split(r'[\s,]',val)
    elif opt=='--prefix_colnames': prefix_colnames=val
    elif opt=='--coltypes': coltypes=re.split(r'[\s,]',val)
    elif opt=='--tsv': delim='\t'
    elif opt=='--delim': delim=val
    elif opt=='--quotechar': quotechar=val
    elif opt=='--nullify': nullify=True
    elif opt=='--nullwords': NULLWORDS=re.split(r'[\s,]',val)
    elif opt=='--fixtags': fixtags=True
    elif opt=='--noheader': noheader=True
    elif opt=='--v': verbose=1
    elif opt=='--nmax': nmax=int(val)
    elif opt=='--skip': skip=int(val)
    else: ErrorExit('Illegal option: %s'%val)

  if ifile:
    fin=file(ifile)
    #fin=codecs.open(ifile,'r','UTF-8','replace')
    if not fin:
      ErrorExit('ERROR: cannot open %s'%ifile)
  else:
    fin = sys.stdin

  if ofile:
    fout=open(ofile,'w')
    #fout=codecs.open(ofile,'w','UTF-8','replace')
  else:
    fout=sys.stdout
    #fout=codecs.getwriter('UTF-8')(sys.stdout,errors='replace')
  if not fout:
    ErrorExit('ERROR: cannot open %s'%ofile)

  if not tablename:
    if not ifile: ErrorExit('ERROR: --tablename or --i required.')
    tablename = CleanName(prefix_tablename+re.sub(r'\..*$','',os.path.basename(ifile)))
    if verbose:
      print >>sys.stderr, 'tablename = "%s"'%tablename

  DTYPES={
	'postgres': {
		'CHAR':'VARCHAR(%d)'%MAXCHAR,
		'CHARACTER':'VARCHAR(%d)'%MAXCHAR,
		'VARCHAR':'VARCHAR(%d)'%MAXCHAR,
		'INT':'INTEGER',
		'BIGINT':'BIGINT',
		'FLOAT':'FLOAT',
		'NUM':'FLOAT',
		'BOOL':'BOOLEAN'
		},
	'mysql': {
		'CHAR':'VARCHAR(%d)'%MAXCHAR,
		'CHARACTER':'VARCHAR(%d)'%MAXCHAR,
		'VARCHAR':'VARCHAR(%d)'%MAXCHAR,
		'INT':'INTEGER',
		'BIGINT':'BIGINT',
		'FLOAT':'FLOAT',
		'NUM':'FLOAT',
		'BOOL':'BOOLEAN'
		}
	}

  if insert:
    Csv2Insert(fin,fout,dbsystem,schema,tablename,colnames,prefix_colnames,noheader,coltypes,nullify,fixtags,MAXCHAR,delim,quotechar,skip,nmax,verbose)

  elif create:
    Csv2Create(fin,fout,dbsystem,DTYPES,schema,tablename,colnames,prefix_colnames,noheader,coltypes,fixtags,delim,quotechar,verbose)

  elif check:
    CsvCheck(fin,dbsystem,noheader,MAXCHAR,delim,quotechar,verbose)

  else:
    ErrorExit('ERROR: no operation specified.\n'+usage)

