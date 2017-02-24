#! /usr/bin/env python
"""
csv_utils.py - A fine example of feature creep!

Jeremy Yang
"""
import sys,os,getopt,re,csv,copy,types
import gzip
import datetime,math,tempfile,shutil

PROG=os.path.basename(sys.argv[0])

#############################################################################
def FixVal(val,numeric,chron,force):
  '''Fix value string, adding quotes, formatting as specified.
Force a default numeric or chron value if force=True.'''
  val = val.strip()
  if numeric:
    try:
      val=float(val)
    except Exception, e:
      if not force: raise e
      print >>sys.stderr, 'ERROR: '+str(e)
      val = 0.0
    val='%.2f'%val
  elif chron:
    try:
      val = datetime.datetime.strptime(re.sub(r' .*$','',val),"%Y/%m/%d")
    except Exception, e:
      if not force: raise e
      print >>sys.stderr, 'ERROR: '+str(e)
      val = datetime.datetime.min
    val = str(val)
  else:
    val = '"%s"'%val
  return val

#############################################################################
def CsvConvert2Triples(fin,fout,col,numeric,delim,skip,nmax):
  '''
Functionality:

INPUT:
	"A",	"B",	"C",	"D"
	"X",	"foo",	"",	""
	"Y",	"bar",	"",	"grok"
	"Z",	"",	"oop",	""
OUTPUT:
	"X",	"B",	"foo"
	"Y",	"B",	"bar"
	"Y",	"D",	"grok"
	"Z",	"C",	"oop"

'''
  n_in=0; n_data=0; n_out=0;
  #csvReader=csv.DictReader(fin,fieldnames=None,restkey=None,restval=None,dialect='excel',delimiter=delim,quotechar='"')
  #colnames=csvReader.fieldnames[1:]
  csvReader=csv.reader(fin,dialect='excel',delimiter=delim,quotechar='"')
  while True:
    try:
      row=csvReader.next()
      n_in+=1
    except:
      break
    if n_in==1:
      colnames=row[1:]
    n_data+=1
    if skip>0 and n_data<=skip: continue
    #rowname = row[colnames[0]]
    rowname = row[0]
    if not rowname:
      continue
    #for colname in colnames:
    #  val = row[colname]
    for j in range(len(colnames)):
      colname = colnames[j]
      val = row[j+1]
      if not val.strip():
        continue
      try:
        val = FixVal(val,numeric,False,False)
      except Exception, e:
        print >>sys.stderr, 'ERROR: '+str(e)
        continue
      fout.write('"%s","%s",%s\n'%(rowname,colname,val))
      n_out+=1
  return n_in,n_out

#############################################################################
def Csv2Html(fin,fout,delim):
  n_in=0; n_out=0;
  csvReader=csv.DictReader(fin,fieldnames=None,restkey=None,restval=None,dialect='excel',delimiter=delim,quotechar='"')
  try:
    row=csvReader.next()    ## must do this to get fieldnames
    n_in+=1
  except:
    print >>sys.stderr, 'ERROR: bad ifile: %s'%fin.name
    return n_in,n_out
  fout.write('<TABLE>\n<TR>')
  for tag in csvReader.fieldnames:
    fout.write('<TH>%s</TH>'%tag)
  fout.write('</TR>\n')
  while True:
    try:
      row=csvReader.next()
      n_in+=1
    except:
      break
    fout.write('<TR>')
    for tag in csvReader.fieldnames:
      fout.write('<TD>%s</TD>'%row[tag])
    fout.write('</TR>\n')
    n_out+=1
  fout.write('</TABLE>\n')
  return n_in,n_out

#############################################################################
def CsvExtractColumn(fin,fout,col,delim,noheader,skip,nmax):
  '''Should not output header tag, only data values.'''
  n_in=0; n_data=0; n_out=0;
  csvReader=csv.reader(fin,dialect='excel',delimiter=delim,quotechar='"')
  while True:
    try:
      row=csvReader.next()
      n_in+=1
    except:
      break
    if n_in==1 and not noheader: continue
    n_data+=1
    if skip>0 and n_data<=skip: continue
    val = '' if len(row)<col else row[col-1]
    fout.write('%s\n'%val)
    n_out+=1
    if n_out==nmax: break
  return n_data,n_out

#############################################################################
def CsvExtractColumn2Array(fin,col,delim,noheader):
  n_in=0; n_data=0;
  vals=[]
  csvReader=csv.reader(fin,dialect='excel',delimiter=delim,quotechar='"')
  while True:
    try:
      row=csvReader.next()
      n_in+=1
    except:
      break
    if n_in==1 and not noheader: continue
    n_data+=1
    val = '' if len(row)<col else row[col-1]
    try:
      val = float(val)
      vals.append(val)
    except:
      continue
  return vals

#############################################################################
def CsvSize(fin,delim,noheader):
  n_in=0; n_data=0; n_col=0;
  csvReader=csv.reader(fin,dialect='excel',delimiter=delim,quotechar='"')
  while True:
    try:
      row=csvReader.next()
      n_in+=1
      if n_in==1: n_col=len(row)
    except:
      break
    if n_in==1 and not noheader: continue
    n_data+=1
  return n_data,n_col

#############################################################################
def CsvDeleteColumn(fin,fout,col,delim):
  '''extrasaction='ignore' should mean the deleted field is ignored and not written.'''
  n_in=0; n_out=0;
  csvReader=csv.DictReader(fin,fieldnames=None,restkey=None,restval=None,dialect='excel',delimiter=delim,quotechar='"')

  fields=csvReader.fieldnames[:]
  coltag=fields[col-1]
  fields.pop(col-1)
  csvWriter=csv.DictWriter(fout,fieldnames=fields,dialect='excel',delimiter=delim,quotechar='"',extrasaction='ignore')
  csvWriter.writeheader()

  while True:
    try:
      row=csvReader.next()
      n_in+=1
    except:
      break
    #if row.has_key(coltag): del row[coltag] ###SHOULD NOT BE NECESSARY.  BUG IN CSV PKG?
    csvWriter.writerow(row)
    #break ##DEBUG
    n_out+=1

  return n_in,n_out

#############################################################################
def CsvCleanColumn(fin,fout,col,delim):
  '''Kludgy.  Clean is what it is.  Currently s/\s.*$// '''
  n_in=0; n_out=0;
  csvReader=csv.reader(fin,dialect='excel',delimiter=delim,quotechar='"')
  csvWriter=csv.writer(fout,dialect='excel',delimiter=delim,quotechar='"')
  while True:
    try:
      row=csvReader.next()
      n_in+=1
    except:
      break
    row[col-1] = re.sub(r'\s.*$','',row[col-1])
    csvWriter.writerow(row)
    n_out+=1
  return n_in,n_out

#############################################################################
def CsvDelimReplace(fin,fout,delim,delim_out):
  n_in=0; n_out=0;
  csvReader=csv.reader(fin,dialect='excel',delimiter=delim,quotechar='"')
  csvWriter=csv.writer(fout,dialect='excel',delimiter=delim_out,quotechar='"',quoting=csv.QUOTE_NONNUMERIC)
  while True:
    try:
      row=csvReader.next()
      n_in+=1
    except:
      break
    csvWriter.writerow(row)
    n_out+=1
  return n_in,n_out

#############################################################################
def CsvRenameColumn(fin,fout,col,newtag,delim):
  n_in=0; n_out=0;
  csvReader=csv.DictReader(fin,fieldnames=None,restkey=None,restval=None,dialect='excel',delimiter=delim,quotechar='"')
  csvReader.fieldnames[col-1]=newtag
  csvWriter=csv.DictWriter(fout,fieldnames=csvReader.fieldnames,dialect='excel',delimiter=delim,quotechar='"',extrasaction='ignore')
  csvWriter.writeheader()
  while True:
    try:
      row=csvReader.next()
      n_in+=1
    except:
      break
    csvWriter.writerow(row)
    n_out+=1
  return n_in,n_out

#############################################################################
def CsvPrefixTags(fin,fout,tagprefix,delim):
  n_in=0; n_out=0;
  csvReader=csv.DictReader(fin,fieldnames=None,restkey=None,restval=None,dialect='excel',delimiter=delim,quotechar='"')
  csvWriter=csv.DictWriter(fout,fieldnames=csvReader.fieldnames,dialect='excel',delimiter=delim,quotechar='"')
  fields=map(lambda s:tagprefix+s,csvReader.fieldnames)
  fout.write('"'+('"'+delim+'"').join(fields)+'"\n')
  while True:
    try:
      row=csvReader.next()
      n_in+=1
    except:
      break
    csvWriter.writerow(row)
    n_out+=1
  return n_in,n_out

#############################################################################
def CsvFixTags(fin,fout,delim):
  '''Fix tags to work with standard tools. Replace spaces, punct with "_".'''
  n_in=0; n_out=0;
  csvReader=csv.DictReader(fin,fieldnames=None,restkey=None,restval=None,dialect='excel',delimiter=delim,quotechar='"')
  csvWriter=csv.DictWriter(fout,fieldnames=csvReader.fieldnames,dialect='excel',delimiter=delim,quotechar='"')
  print >>sys.stderr, 'Old tags: "%s"'%str(csvReader.fieldnames)
  fields=map(lambda s:re.sub(r'[\s,;]','_',s),csvReader.fieldnames)
  print >>sys.stderr, 'New tags: "%s"'%str(fields)
  fout.write('"'+('"'+delim+'"').join(fields)+'"\n')
  while True:
    try:
      row=csvReader.next()
      n_in+=1
    except:
      break
    csvWriter.writerow(row)
    n_out+=1
  return n_in,n_out

#############################################################################
def CsvAddQuotes(fin,fout,delim):
  '''Add quotes; quote non-numeric fields.'''
  n_in=0; n_out=0;
  csvReader=csv.reader(fin,dialect='excel',delimiter=delim,quotechar='"')
  csvWriter=csv.writer(fout,dialect='excel',delimiter=delim,quotechar='"',quoting=csv.QUOTE_NONNUMERIC)
  while True:
    try:
      row=csvReader.next()
      n_in+=1
    except:
      break
    csvWriter.writerow(row)
    n_out+=1
  return n_in,n_out

#############################################################################
def CsvFixQuotes(fin,fout,delim):
  '''Fix quotes; escape quotes not next to delim, at start or end.'''
  n_in=0; n_out=0;
  while True:
    line=fin.readline()
    if not line: break
    n_in+=1

    ###Not so good:
    #rob = re.compile('([^%s])"([^%s])'%(delim,delim))
    #line=rob.sub('\1""\2',line)
    #fout.write(line+'\n')

    iq = [m.start() for m in re.finditer('"',line)] #location of quotes
    iqe = [] #location of quotes to be escaped

    line=line.rstrip()

    for i in iq:
      if i==0 or i==(len(line)-1):
        continue
      elif line[i:(i+3)]==('"%s"'%(delim)):
        continue
      elif line[(i-2):(i+1)]==('"%s"'%(delim)):
        continue
      else:
        iqe.append(i)

    line_out=''
    i_prev=0;
    for i in iqe:
      line_out+=(line[i_prev:i]+'"')
      i_prev=i
    line_out+=(line[i_prev:])
    fout.write(line_out+'\n')

    n_out+=1
  return n_in,n_out

#############################################################################
def CsvAddHeader(fin,fout,header,delim):
  '''Insert header line.'''
  n_in=0; n_out=0;
  tags = re.split(r',',header)
  csvReader=csv.reader(fin,dialect='excel',delimiter=delim,quotechar='"')
  csvWriter=csv.writer(fout,dialect='excel',delimiter=delim,quotechar='"',quoting=csv.QUOTE_NONNUMERIC)
  while True:
    try:
      row=csvReader.next()
      n_in+=1
    except:
      break
    if n_in==1:
      if len(row) != len(tags):
        print >>sys.stderr, 'ERROR: #tags != #cols (%d != %d)'%(len(tags),len(row))
        return n_in,0
      else:
        csvWriter.writerow(map(lambda s:s.strip(),tags))
    csvWriter.writerow(row)
    n_out+=1
  return n_in,n_out

#############################################################################
def CsvUniqueSortedColumn(fin,fout,col,numeric,chron,delim):
  n_in=0; n_out=0;
  csvReader=csv.DictReader(fin,fieldnames=None,restkey=None,restval=None,dialect='excel',delimiter=delim,quotechar='"')
  vals = set()
  while True:
    try:
      row=csvReader.next()
      n_in+=1
    except:
      break
    val = row[csvReader.fieldnames[col-1]]
    try:
      if numeric:
        val=float(val)
      elif chron:
        val = datetime.datetime.strptime(re.sub(r' .*$','',val),"%Y/%m/%d")
    except Exception, e:
      print >>sys.stderr, 'ERROR: '+str(e)
      val = 0 if numeric else (datetime.datetime.min if chron else '')
    if val.strip(): vals.add(val.strip())
  vals_list = list(vals)
  vals_list.sort()
  for val in vals_list:
    fout.write(('%.3f\n'%val) if numeric else ('%s\n'%val))
    n_out+=1
  return n_in,n_out

#############################################################################
def CsvColumnValueUniquenessCheck(fin,col,delim,noheader,skip,nmax):
  n_in=0; n_data=0;
  csvReader=csv.DictReader(fin,fieldnames=None,restkey=None,restval=None,dialect='excel',delimiter=delim,quotechar='"')
  vals = {}
  vals_dup = set()
  while True:
    try:
      row=csvReader.next()
      n_in+=1
    except:
      break
    n_data+=1
    if skip>0 and n_data<=skip: continue
    val=row[csvReader.fieldnames[col-1]]
    if vals.has_key(val):
      vals_dup.add(val)
    else:
      vals[val]=0
    vals[val]+=1
    if (n_data-skip)==nmax: break

  print >>sys.stderr, 'Column %d "%s" values:%s UNIQUE.'%(col,csvReader.fieldnames[col-1],(' NOT' if vals_dup else ''))
  for val in vals_dup:
    print >>sys.stderr, ('\t%14s: %2d\n'%(val,vals[val]))

  print >>sys.stderr, 'values, col %d "%s", unique: %d ; total: %d'%(col,csvReader.fieldnames[col-1],len(vals),n_data)

#############################################################################
def CsvColumnValueCount(ifile,col,numeric,chron,delim,noheader,skip,nmax):
  fin = open(ifile)
  if not fin: ErrorExit('ERROR: cannot open ifile: %s'%ifile)
  return CsvColumnValueCount_File(fin,col,numeric,chron,delim,noheader,skip,nmax)

#############################################################################
def CsvColumnValueCount_File(fin,col,numeric,chron,delim,noheader,skip,nmax):
  '''Count the unique values.'''
  n_in=0; n_data=0;
  csvReader=csv.DictReader(fin,fieldnames=None,restkey=None,restval=None,dialect='excel',delimiter=delim,quotechar='"')
  vals = set()
  while True:
    try:
      row=csvReader.next()
      n_in+=1
    except:
      break
    n_data+=1
    if skip>0 and n_data<=skip: continue
    val=row[csvReader.fieldnames[col-1]]
    try:
      if numeric:
        val=float(val)
      elif chron:
        val = datetime.datetime.strptime(re.sub(r' .*$','',val),"%Y/%m/%d")
    except Exception, e:
      print >>sys.stderr, ('ERROR: '+str(e))
      val = 0 if numeric else (datetime.datetime.min if chron else '')
    vals.add(val)
    if (n_data-skip)==nmax: break

  #print >>sys.stderr, 'values, col %d "%s", unique: %d ; total: %d'%(col,csvReader.fieldnames[col-1],len(vals),n_data)
  return n_data,len(vals)

#############################################################################
def CsvColumnValueCounts(fin,fout,col,numeric,chron,delim,noheader,skip,nmax):
  '''Like unique sort but also count the unique values.  Output typically for human consumption.'''
  n_in=0; n_data=0; n_out=0;
  csvReader=csv.DictReader(fin,fieldnames=None,restkey=None,restval=None,dialect='excel',delimiter=delim,quotechar='"')
  vals = {}
  while True:
    try:
      row=csvReader.next()
      n_in+=1
    except:
      break
    n_data+=1
    if skip>0 and n_data<=skip: continue
    val=row[csvReader.fieldnames[col-1]]
    try:
      if numeric:
        val=float(val)
      elif chron:
        val = datetime.datetime.strptime(re.sub(r' .*$','',val),"%Y/%m/%d")
    except Exception, e:
      print >>sys.stderr, ('ERROR: '+str(e))
      val = 0 if numeric else (datetime.datetime.min if chron else '')
    if not vals.has_key(val): vals[val]=0
    vals[val]+=1
    if (n_data-skip)==nmax: break

  print >>sys.stderr, 'values, col %d "%s", unique: %d ; total: %d'%(col,csvReader.fieldnames[col-1],len(vals),n_data)
  fout.write('%24s\t%6s\n'%(csvReader.fieldnames[col-1],'counts'))
  for val in sorted(vals.keys()):
    fout.write('%24s\t%6d (%6.3f%%)\n'%(('"%s"'%val),vals[val],100.0*vals[val]/n_data))
    n_out+=1
  return n_data,n_out

#############################################################################
def CsvColumnStats(fin,col,delim,noheader,skip,nmax):
  '''For non-empty, non-NULL, numeric values, specified column, generate statistics.'''
  import numpy
  vals=[]
  n_in=0; n_data=0; n_nonempty=0;
  csvReader=csv.reader(fin,dialect='excel',delimiter=delim,quotechar='"')
  while True:
    try:
      row=csvReader.next()
      n_in+=1
    except:
      break
    if not noheader and n_in==1: continue
    n_data+=1
    if skip>0 and n_data<=skip: continue
    val=row[col-1]
    val=str(val).strip()
    if val!='' and val.upper()!='NULL':
      n_nonempty+=1
    try:
      val = float(val)
    except Exception,e:
      print >>sys.stderr, '%s'%str(e)
      continue
    vals.append(val)
    if (n_data-skip)==nmax: break
  fin.close()
  print >>sys.stderr, 'vals: %d ; range (%f,%f) ; mean: %f ; var: %f ; std: %f'%(len(vals),min(vals),max(vals),numpy.mean(vals),numpy.var(vals),numpy.std(vals))
  return n_data,n_nonempty

#############################################################################
def CsvColumnCount(ifile,col,delim,noheader,igz):
  '''Count non-empty, non-NULL values, specified column.'''
  fin = gzip.open(ifile) if igz else open(ifile)
  if not fin: ErrorExit('ERROR: cannot open ifile: %s'%ifile)
  return CsvColumnCount_File(fin,col,delim,noheader)

#############################################################################
def CsvColumnCount_File(fin,col,delim,noheader):
  n_in=0; n_data=0; n_nonempty=0;
  csvReader=csv.reader(fin,dialect='excel',delimiter=delim,quotechar='"')
  while True:
    try:
      row=csvReader.next()
      n_in+=1
    except:
      break
    if n_in==1 and not noheader: continue
    n_data+=1
    val = row[col-1] if col <= len(row) else ''
    val = str(val).strip()
    if val!='' and val.upper()!='NULL':
      n_nonempty+=1
  fin.close()
  return n_data,n_nonempty

#############################################################################
def CsvSortbyColumn(fin,fout,col,numeric,chron,delim):
  n_in=0; n_out=0;
  csvReader=csv.DictReader(fin,fieldnames=None,restkey=None,restval=None,dialect='excel',delimiter=delim,quotechar='"')

  lol=[];
  while True:
    try:
      row=csvReader.next()
      val=row[csvReader.fieldnames[col-1]]
      n_in+=1
    except:
      break #normal
    try:
      if numeric:
        val=float(val)
      elif chron:
        val = datetime.datetime.strptime(re.sub(r' .*$','',val),"%Y/%m/%d")
    except Exception, e:
      print >>sys.stderr, ('ERROR [val="%s"]: %s'%(val,str(e)))
      val = 0 if numeric else (datetime.datetime.min if chron else '')
      continue
    lol.append((val,row))

  csvWriter=csv.DictWriter(fout,fieldnames=csvReader.fieldnames,dialect='excel',delimiter=delim,quotechar='"')
  csvWriter.writeheader()

  for val,row in sorted(lol,key=lambda x: x[0]):
    try:
      csvWriter.writerow(row)
      n_out+=1
    except Exception,e:
      print >>sys.stderr, ('DEBUG: %s row="%s"'%(str(e),str(row)))

  return n_in,n_out

#############################################################################
def CsvDedup(fin,fout,col,numeric,delim,noheader):
  '''Based on specified row, keep only row with first occurance where duplicate values exist.'''
  n_in=0; n_data=0; n_out=0;
  csvReader=csv.reader(fin,dialect='excel',delimiter=delim,quotechar='"')
  csvWriter=csv.writer(fout,dialect='excel',delimiter=delim,quotechar='"',quoting=csv.QUOTE_NONNUMERIC)
  vals = set()
  while True:
    try:
      row=csvReader.next()
      n_in+=1
    except:
      break
    if n_in==1 and not noheader:
      csvWriter.writerow(row)
      continue
    n_data+=1
    val = row[col-1]
    if numeric:
      try:
        val=float(val)
      except Exception, e:
        print >>sys.stderr, ('ERROR [val="%s"]: %s'%(val,str(e)))
        continue
    if val not in vals:
      csvWriter.writerow(row)
      n_out+=1
      vals.add(val)
  return n_data,n_out

#############################################################################
def CsvRmEmptyRows(fin,fout,delim,noheader):
  n_in=0; n_data=0; n_out=0;
  csvReader=csv.reader(fin,dialect='excel',delimiter=delim,quotechar='"')
  csvWriter=csv.writer(fout,dialect='excel',delimiter=delim,quotechar='"',quoting=csv.QUOTE_NONNUMERIC)
  vals = set()
  while True:
    try:
      row=csvReader.next()
      n_in+=1
    except:
      break
    if n_in==1 and not noheader:
      csvWriter.writerow(row)
      continue
    n_data+=1
    has_data=False
    for val in row:
      has_data |= bool((str(val)).strip())
    if has_data:
      csvWriter.writerow(row)
      n_out+=1
  return n_data,n_out

#############################################################################
def CsvFilterbyValset(fin,fout,col,numeric,vals,deselect,delim,noheader):
  n_in=0; n_data=0; n_out=0;
  csvReader=csv.reader(fin,dialect='excel',delimiter=delim,quotechar='"')
  csvWriter=csv.writer(fout,dialect='excel',delimiter=delim,quotechar='"',quoting=csv.QUOTE_NONNUMERIC)
  while True:
    try:
      row=csvReader.next()
      n_in+=1
    except:
      break
    if n_in==1 and not noheader:
      csvWriter.writerow(row)
      continue
    n_data+=1
    ok=False
    val = row[col-1]
    if numeric:
      try:
        val=float(val)
      except Exception, e:
        print >>sys.stderr, ('ERROR [val="%s"]: %s'%(val,str(e)))
        ok=False
    ok = (val in vals)
    ok = not ok if deselect else ok
    if not ok: print >>sys.stderr, 'DEBUG: val NOT ok: "%s"'%val
    if ok:
      csvWriter.writerow(row)
      n_out+=1
  return n_data,n_out

#############################################################################
def CsvFilterbyColumn(fin,fout,col,numeric,chron,minval,maxval,eqval,negate,delim):
  '''Filter and remove rows based on value criteria.  Numeric, chron, or NULL/non-NULL.
Allow both minval and maxval.'''
  n_in=0; n_out=0;
  csvReader=csv.DictReader(fin,fieldnames=None,restkey=None,restval=None,dialect='excel',delimiter=delim,quotechar='"')
  while True:
    try:
      row=csvReader.next()
    except Exception, e:
      break #normal
    if n_in==0:
      csvWriter=csv.DictWriter(fout,fieldnames=csvReader.fieldnames,dialect='excel',delimiter=delim,quotechar='"')
      csvWriter.writeheader()
    n_in+=1
    try:
      val=row[csvReader.fieldnames[col-1]]
    except Exception, e:
      print >>sys.stderr, ('ERROR: '+str(e))
      continue
    try:
      if numeric:
        val=float(val)
      elif chron:
        val = datetime.datetime.strptime(re.sub(r' .*$','',val),"%Y/%m/%d")
        #print >>sys.stderr, 'DEBUG: val = %s'%val.isoformat()
    except Exception, e:
      print >>sys.stderr, ('ERROR: '+str(e))
      val = 0 if numeric else (datetime.datetime.min if chron else '')
      continue

    ok=True #default is pass-through

    if type(val) in (types.FloatType,types.IntType,types.LongType):
      if minval!=None and val<minval: ok=False
      if maxval!=None and val>maxval: ok=False
    if (type(eqval) in types.StringTypes) and eqval.upper()=='NULL':
      if val not in (None,''): ok=False
    elif eqval!=None:
      if val!=eqval: ok=False
    #if maxval!=None: print >>sys.stderr, 'DEBUG %s < %s'%(str(val),str(maxval))

    if negate: ok = not ok

    if ok:
      csvWriter.writerow(row)
      n_out+=1

  return n_in,n_out

#############################################################################
def CsvSubsetColumns(fin,fout,coltags,delim):
  n_in=0; n_out=0;
  csvReader=csv.DictReader(fin,fieldnames=None,restkey=None,restval=None,dialect='excel',delimiter=delim,quotechar='"')
  for coltag in coltags:
    if coltag not in csvReader.fieldnames:
      print >>sys.stderr, 'ERROR: selected tag "%s" not in fieldnames %s'%(coltag,str(csvReader.fieldnames))
      return 0,0
  csvWriter=csv.DictWriter(fout,fieldnames=coltags,dialect='excel',delimiter=delim,quotechar='"')
  csvWriter.writeheader()
  while True:
    try:
      row=csvReader.next()
    except Exception, e:
      break #normal
    n_in+=1
    outrow = { coltag:row[coltag] for coltag in coltags }
    csvWriter.writerow(outrow)
    n_out+=1
  return n_in,n_out

#############################################################################
def CsvMergeColumns(fin,fout,mergetags,delim):
  '''Merge specified cols, precedence by order specified.'''
  n_in=0; n_out=0;
  csvReader=csv.DictReader(fin,fieldnames=None,restkey=None,restval=None,dialect='excel',delimiter=delim,quotechar='"')
  for coltag in mergetags:
    if coltag not in csvReader.fieldnames:
      print >>sys.stderr, 'ERROR: selected tag "%s" not in fieldnames %s'%(coltag,str(csvReader.fieldnames))
      return 0,0

  fieldnames_out = csvReader.fieldnames[:]
  for coltag in mergetags[1:]:
    fieldnames_out.remove(coltag)

  csvWriter=csv.DictWriter(fout,fieldnames=fieldnames_out,dialect='excel',delimiter=delim,quotechar='"')
  csvWriter.writeheader()

  while True:
    try:
      row=csvReader.next()
    except Exception, e:
      break #normal
    n_in+=1
    outrow = { coltag:row[coltag] for coltag in fieldnames_out }

    for j in range(len(mergetags)-1):
      if outrow[mergetags[0]] in (None,''):
        outrow[mergetags[0]] = row[mergetags[j+1]]

    csvWriter.writerow(outrow)
    n_out+=1
  return n_in,n_out

#############################################################################
def CsvColPairAnalysis(fin,fout,tagA,tagB,numeric,delim,verbose):
  '''Output only one-to-one pairs.'''
  n_in=0;
  a2b={}; b2a={};
  csvReader=csv.DictReader(fin,fieldnames=None,restkey=None,restval=None,dialect='excel',delimiter=delim,quotechar='"')
  fout.write('%s,%s\n'%(tagA,tagB)) #One-to-one pairs only.
  while True:
    try:
      row=csvReader.next()
    except Exception, e:
      break #normal
    n_in+=1
    a = row[tagA]
    b = row[tagB]
    if verbose>1: print >>sys.stderr, 'a = %s, b = %s'%(a,b)
    if numeric and a!=None and a!='':
      try:
        a = float(a)
      except Exception, e:
        print >>sys.stderr, str(e)
        a = None
    if numeric and b!=None and b!='':
      try:
        b = float(b)
      except Exception, e:
        print >>sys.stderr, str(e)
        b = None
    if a!=None and a!='' and b!=None and b!='':
      if a2b.has_key(a): a2b[a].add(b)
      else: a2b[a] = set([b])
      if b2a.has_key(b): b2a[b].add(a)
      else: b2a[b] = set([a])
    elif a!=None and a!='':
      if not a2b.has_key(a): a2b[a] = set()
    elif b!=None and b!='':
      if not b2a.has_key(b): b2a[b] = set()
    else:
      continue

  a2b_mincount=sys.maxint
  a2b_mincount_a=None
  a2b_maxcount=0
  a2b_maxcount_a=None
  for a in a2b.keys():
    if len(a2b[a])> a2b_maxcount:
      a2b_maxcount = len(a2b[a])
      a2b_maxcount_a=a
    if len(a2b[a])<a2b_mincount:
      a2b_mincount = len(a2b[a])
      a2b_mincount_a=a
  b2a_mincount=sys.maxint
  b2a_mincount_b=None
  b2a_maxcount=0
  b2a_maxcount_b=None
  for b in b2a.keys():
    if len(b2a[b])>b2a_maxcount:
      b2a_maxcount = len(b2a[b])
      b2a_maxcount_b=b
    if len(b2a[b])<b2a_mincount:
      b2a_mincount = len(b2a[b])
      b2a_mincount_b=b

  n_121=0;
  n_a2b_singles=0
  for a in sorted(a2b.keys()):
    if len(a2b[a])==1:
      n_a2b_singles+=1
      b = list(a2b[a])[0]
      if len(b2a[b])==1:
        n_121+=1
        fout.write('%s,%s\n'%(a,b)) #One-to-one pairs only.
  n_b2a_singles=0
  for b in b2a.keys():
    if len(b2a[b])==1:
      n_b2a_singles+=1

  print >>sys.stderr, 'total rows: %d'%n_in
  print >>sys.stderr, 'total unique A count = %d'%len(a2b.keys())
  print >>sys.stderr, 'total unique B count = %d'%len(b2a.keys())
  if a2b_maxcount>1:
    print >>sys.stderr, 'A2B one-to-many, max Bcount = %d'%a2b_maxcount
  elif a2b_maxcount==1:
    print >>sys.stderr, 'A2B one-to-one, max Bcount = %d'%a2b_maxcount
  print >>sys.stderr, 'A2B max Bcount a: %s'%a2b_maxcount_a
  if a2b_mincount==0:
    print >>sys.stderr, 'A2B some missing, min Bcount = %d'%a2b_mincount
  else:
    print >>sys.stderr, 'A2B none missing, min Bcount = %d'%a2b_mincount
  print >>sys.stderr, 'A2B min Bcount a: %s'%a2b_mincount_a

  if b2a_maxcount>1:
    print >>sys.stderr, 'B2A one-to-many, max Acount = %d'%b2a_maxcount
  elif b2a_maxcount==1:
    print >>sys.stderr, 'B2A one-to-one, max Acount = %d'%b2a_maxcount
  print >>sys.stderr, 'B2B max Acount b: %s'%b2a_maxcount_b
  if b2a_mincount==0:
    print >>sys.stderr, 'B2A some missing, min Acount = %d'%b2a_mincount
  else:
    print >>sys.stderr, 'B2A none missing, min Acount = %d'%b2a_mincount
  print >>sys.stderr, 'B2B min Acount b: %s'%b2a_mincount_b

  print >>sys.stderr, 'A2B As with 1 B: %d'%n_a2b_singles
  print >>sys.stderr, 'B2B Bs with 1 A: %d'%n_b2a_singles
  print >>sys.stderr, 'AB one-to-one pairs: %d'%n_121

#############################################################################
def MergeCSVs(finA,finB,fout,id_tagA,id_tagB,discard_unmerged,numeric,delim,verbose=0):
  '''The specified id_tag used as key, determines number of merged rows. 
All other common tags are merged, determining the number of output
columns.'''
  n_inA=0; n_inB=0; n_out=0;
  csvReaderA=csv.DictReader(finA,fieldnames=None,restkey=None,restval=None,dialect='excel',delimiter=delim,quotechar='"')
  try:
    rowA=csvReaderA.next()    ## must do this to get fieldnames
    n_inA+=1
  except Exception, e:
    print >>sys.stderr, 'ERROR: '+str(e)
    return n_inA,n_inB,n_out
  if id_tagA not in csvReaderA.fieldnames:
    print >>sys.stderr, 'ERROR: cannot find field "%s" in ifileA.'%id_tagA
    #print >>sys.stderr, 'DEBUG: fieldnames=', csvReaderA.fieldnames
    return n_inA,n_inB,n_out

  csvReaderB=csv.DictReader(finB,fieldnames=None,restkey=None,restval=None,dialect='excel',delimiter=delim,quotechar='"')
  try:
    rowB=csvReaderB.next()    ## must do this to get fieldnames
    n_inB+=1
  except Exception, e:
    print >>sys.stderr, 'ERROR: '+str(e)
    return n_inA,n_inB,n_out
  if id_tagB not in csvReaderB.fieldnames:
    print >>sys.stderr, 'ERROR: cannot find field "%s" in ifileB.'%id_tagB
    #print >>sys.stderr, 'DEBUG: fieldnames=', csvReaderB.fieldnames
    return n_inA,n_inB,n_out

  mergetags=[]  ## = all common tags
  onlyAtags=[]
  onlyBtags=[]
  for tag in csvReaderA.fieldnames:
    #if tag!=id_tagA and tag not in mergetags:
    if tag not in mergetags:
      if tag in csvReaderB.fieldnames:
        mergetags.append(tag)
      else:
        onlyAtags.append(tag)
  for tag in csvReaderB.fieldnames:
    if tag not in csvReaderA.fieldnames:
      onlyBtags.append(tag)
  #print >>sys.stderr, 'DEBUG: mergetags=', mergetags
  #print >>sys.stderr, 'DEBUG: onlyAtags=', onlyAtags
  #print >>sys.stderr, 'DEBUG: onlyBtags=', onlyBtags

  #outtags=[id_tagA]+mergetags+onlyAtags+onlyBtags
  outtags=mergetags+onlyAtags+onlyBtags
  if id_tagB not in outtags: outtags.insert(0,id_tagB)
  if id_tagA not in outtags: outtags.insert(0,id_tagA)

  csvWriter=csv.DictWriter(fout,fieldnames=outtags,delimiter=delim,quotechar='"')
  #fout.write('"'+('"'+delim+'"').join(outtags)+'"\n') ## pre-Python2.7
  csvWriter.writeheader() ## Python2.7+


  idA=rowA[id_tagA]
  #print >>sys.stderr, 'DEBUG: idA="%s"'%idA
  if numeric: idA=float(idA)
  idB=rowB[id_tagB]
  #print >>sys.stderr, 'DEBUG: idB="%s"'%idB
  if numeric: idB=float(idB)
  doneA=False; doneB=False;
  while True:
    if (idA!=None and idB!=None) and idA==idB:
      if verbose>1: print >>sys.stderr, 'found in A and B: %s'%(str(idA))
      newrow=PasteRows(rowA,rowB,onlyAtags,onlyBtags)
      csvWriter.writerow(newrow)
      n_out+=1
      try:
        rowA=csvReaderA.next()
        n_inA+=1
        idA=rowA[id_tagA]
        #print >>sys.stderr, 'DEBUG: idA="%s"'%idA
        if numeric: idA=float(idA)
      except:
        doneA=True
        idA=None
      try:
        rowB=csvReaderB.next()
        n_inB+=1
        idB=rowB[id_tagB]
        #print >>sys.stderr, 'DEBUG: idB="%s"'%idB
        if numeric: idB=float(idB)
      except:
        doneB=True
        idB=None
    elif ((idA!=None and idB!=None) and idA<idB) or (idA!=None and idB==None):
      if verbose>1: print >>sys.stderr, 'found in A not B: %s'%(str(idA))
      if not discard_unmerged:
        newrow=PasteRows(rowA,None,onlyAtags,onlyBtags)
        csvWriter.writerow(newrow)
        n_out+=1
      try:
        rowA=csvReaderA.next()
        n_inA+=1
        idA=rowA[id_tagA]
        if numeric: idA=float(idA)
      except:
        doneA=True
        idA=None
    elif ((idA!=None and idB!=None) and idA>idB) or (idA==None and idB!=None):
      if verbose>1: print >>sys.stderr, 'found in B not A: %s'%(str(idA))
      if not discard_unmerged:
        newrow=PasteRows(None,rowB,onlyAtags,onlyBtags)
        csvWriter.writerow(newrow)
        n_out+=1
      try:
        rowB=csvReaderB.next()
        n_inB+=1
        idB=rowB[id_tagB]
        if numeric: idB=float(idB)
      except:
        doneB=True
        idB=None
    else:
      print >>sys.stderr, 'DEBUG: Aaack!'
      doneA=True
      doneB=True

    #print >>sys.stderr, 'DEBUG: n_inA=%d, n_inB=%d, idA=%s, idB=%s'%(n_inA,n_inB,idA,idB)
    #if doneA: print >>sys.stderr, 'DEBUG: A is %s, B is %s.'%('DONE' if doneA else 'NOT DONE', 'DONE' if doneB else 'NOT DONE')

    if doneA and doneB: break

  return n_inA,n_inB,n_out

#############################################################################
def PasteRows(rowA,rowB,onlyAtags,onlyBtags):
  '''Simple.  RowB supercedes RowA if a column of same name conflicts.'''
  if rowA and rowB:
    #print >>sys.stderr, 'DEBUG: rowA and rowB'
    #for key,val in rowA.items(): print >>sys.stderr, 'DEBUG: rowA[%s] = %s'%(key,val)
    newrow=copy.deepcopy(rowB)
    for tag in onlyAtags:
      newrow[tag]=rowA[tag]
      #print >>sys.stderr, 'DEBUG: rowA[%s] = %s'%(tag,rowA[tag])
  elif rowA and not rowB:
    newrow=copy.deepcopy(rowA)
    for tag in onlyBtags:
      newrow[tag]=''
  elif not rowA and rowB:
    newrow=copy.deepcopy(rowB)
    for tag in onlyAtags:
      newrow[tag]=''
  return newrow
#############################################################################
def Coltags(fin,delim):
  csvReader=csv.DictReader(fin,fieldnames=None,restkey=None,restval=None,dialect='excel',delimiter=delim,quotechar='"')
  row=csvReader.next()
  coltags=list(csvReader.fieldnames)
  fin.close()
  return coltags

#############################################################################
def Coltag2Col(ifile,delim,igz,coltag):
  fin = gzip.open(ifile) if igz else open(ifile)
  if not fin: ErrorExit('ERROR: cannot open ifile: %s'%ifile)
  csvReader=csv.DictReader(fin,fieldnames=None,restkey=None,restval=None,dialect='excel',delimiter=delim,quotechar='"')
  #row=csvReader.next()
  fields=csvReader.fieldnames[:]
  fin.close()
  for j,tag in enumerate(fields):
    if tag == coltag: return j+1
  return None #ERROR

#############################################################################
def Col2Coltag(ifile,delim,igz,col):
  fin = gzip.open(ifile) if igz else open(ifile)
  if not fin: ErrorExit('ERROR: cannot open ifile: %s'%ifile)
  csvReader=csv.DictReader(fin,fieldnames=None,restkey=None,restval=None,dialect='excel',delimiter=delim,quotechar='"')
  row=csvReader.next()
  for j,tag in enumerate(csvReader.fieldnames):
    if (j+1)==col: return tag
  fin.close()
  return None #ERROR

##############################################################################
def ToStringForCSV(val,maxlen=0):
  '''Stringify and quote as needed'''
  if type(val) in (types.IntType,types.LongType):
    val=str(val)
  elif type(val) in (types.ListType,types.TupleType):
    val=(('"'+re.sub(r'"','\\"',str(val))+'"') if len(val)>0 else '')
  elif type(val) is types.FloatType:
    val=('%.3f'%val)
  elif type(val) is types.DictType:
    #val=(('"'+re.sub(r'"','\\"',str(val))+'"') if len(val)>0 else '')
    val=(('"'+re.sub(r'"','""',str(val))+'"') if len(val)>0 else '')
  elif type(val) in (types.StringType,types.UnicodeType):
    val=re.sub(r'\n',' ',val)
    #val=re.sub(r'"','\\"',val)
    val=re.sub(r'"','""',val)
    if maxlen and len(val)>maxlen: val=val[:maxlen]+'...'
    val=('"'+val+'"')
  elif type(val) is types.NoneType:
    val=('')
  else:
    #val=('"'+re.sub(r'"','\\"',str(val))+'"')
    val=('"'+re.sub(r'"','""',str(val))+'"')
  return val

#############################################################################
def ErrorExit(msg):
  print >>sys.stderr,msg
  sys.exit(1)

#############################################################################
if __name__=='__main__':

  USAGE='''\
%(PROG)s - CSV file utilities

required:
  --i INFILE .................. input CSV file ("-" means stdin)

operations (one of):
  --list_tags ................. list tags [default operation]
  --size ...................... col and row counts
  --colcount .................. column count (non-empty), specified col
  --colcount_all .............. column count (non-empty), all cols
  --csv2html .................. write HTML table
  --prefixtags ................ prefix all column tags (--tagprefix TAGPREFIX)
  --fixtags ................... fix all column tags (replace spaces with _)
  --addquotes ................. all non-numeric fields quoted
  --fixquotes ................. escape quotes not next to delim
  --colvalstats ............... range, mean, variance for numerical col
  --colval_ucheck ............. column vals uniqueness check
  --colpairanalysis ........... one-to-one, one-to-many, many-to-many, etc. (--cols I1,I2)
  --convert2triples ........... output format: "ROWNAME","COLNAME","VAL" (always 3 cols)
  --selectrows ................ select rows if val in valfile
  --deselectrows .............. deselect rows if val in valfile
  --deduprows ................. deduplicate rows, based on specified column
  --rmemptyrows ............... deduplicate rows, based on specified column
  --addheader HEADER .......... add header row
  --change_delim .............. from DELIM to DELIM_OUT
  --tsv2csv ................... 
  --csv2tsv ................... 

operations requiring --col[s] or --coltag[s]:
  --extractcol ................ extract column (no header)
  --deletecol ................. delete column
  --renamecol ................. rename column (--newtag NEWTAG)
  --cleancol .................. s/\s.*$//
  --usortedcol ................ distinct column values, sorted
  --sortbycol ................. sort by column 
  --filterbycol ............... filter by column 
  --defilterbycol ............. filter by column, reverse logic
  --usortedcol ................ distinct column values, sorted
  --colvalcount ............... distinct column value count
  --colvalcounts .............. distinct column value counts (frequencies)
  --colvalstats ............... range, mean, variance for numerical col
  --colval_ucheck ............. column vals uniqueness check
  --colcount .................. column count (non-empty), specified col
  --subsetcols ................ subset selected columns 
  --mergecols ................. merge multiple cols into first, precedence by order

parameters:
  --col I ..................... column index
  --coltag TAG ................ column tag of interest
  --cols I1,I2,... ............ column indices
  --coltag TAG ................ column tag
  --coltags TAG1,TAG2[,..] .... column tags
  --numeric ................... numeric sort/filter/merge
  --chron ..................... date sort/filter
  --minval VAL ................ min for --filterbycol
  --maxval VAL ................ max for --filterbycol
  --eqval VAL ................. val for --filterbycol (use "NULL" for empty or NULL)
  --colB IB ................... column index B for merge
  --coltagB TAGB .............. column tag B for merge
  --newtag NEWTAG ............. new column tag for rename
  --tagprefix PREFIX .......... column tag prefix
  --skip NSKIP ................ skip 1st NSKIP rows
  --nmax NMAX ................. process max NMAX rows

options:
  --o OUTFILE ................. [default=stdout]
  --tsv ....................... delimiter=tab [default=comma]
  --noheader .................. no header row
  --iB INFILEB ................ input file B for merging
  --overwrite_input_file ...... overwrite input file with output
  --valfile fvals ............. file of values to [de]select
  --delim DELIM ............... use if not comma, tab
  --delim_out DELIM_OUT ....... for --change_delim
  --igz ....................... input gz
  --v ......................... verbose
  --h ......................... this help

'''%{'PROG':PROG}

  ifile=None; ofile=None; verbose=0; 
  ifileB=None;
  valfile=None;
  tsv=False;
  tsv=False;
  list_tags=False;
  csv2html=False;
  extractcol=False;
  deletecol=False;
  renamecol=False;
  cleancol=False;
  usortedcol=False;
  colvalcount=False;
  colvalcount_all=False;
  colvalcounts=False;
  colvalstats=False;
  colval_ucheck=False;
  size=False;
  colcount_all=False;
  colcount=False;
  subsetcols=False;
  mergecols=False;
  deselectrows=False;
  deduprows=False;
  rmemptyrows=False;
  selectrows=False;
  sortbycol=False;
  filterbycol=False;
  defilterbycol=False;
  addheader=None;
  colpairanalysis=False;
  convert2triples=False;
  tsv2csv=False;
  csv2tsv=False;
  numeric=False;
  chron=False;
  minval=None; maxval=None; eqval=None; eqval=None;
  col=0; cols=[];
  coltag=None; coltags=[];
  colB=0; coltagB=None;
  newtag=None;
  prefixtags=False;
  fixtags=False;
  addquotes=False;
  fixquotes=False;
  change_delim=False;
  tagprefix=None;
  delim=None;
  delim_out=None;
  overwrite_input_file=False;
  igz=False;
  noheader=False;
  nmax=0; skip=0;
  opts,pargs = getopt.getopt(sys.argv[1:],'',['h','v','vv','i=','o=','valfile=',
	'tsv','csv2html','col=','colB=','coltag=','cols=','coltags=','igz',
	'extractcol','deletecol','renamecol','usortedcol','cleancol',
	'colvalcount','colvalcount_all','colvalcounts','colcount','colcount_all','size',
	'colvalstats',
	'colval_ucheck',
	'subsetcols','sortbycol','filterbycol','defilterbycol',
	'selectrows',
	'mergecols',
	'change_delim',
	'deselectrows',
	'deduprows',
	'rmemptyrows',
	'tsv2csv','csv2tsv',
	'prefixtags','tagprefix=',
	'fixtags',
	'addquotes',
	'fixquotes',
	'list_tags','minval=','maxval=','eqval=','numeric','chron',
	'addheader=',
	'nmax=','skip=',
	'colpairanalysis',
	'convert2triples',
	'iB=','coltagB=','newtag=',
	'delim=',
	'delim_out=',
	'noheader',
	'overwrite_input_file'])
  if not opts: ErrorExit(USAGE)
  for (opt,val) in opts:
    if opt=='--h': ErrorExit(USAGE)
    elif opt=='--i': ifile=val
    elif opt=='--iB': ifileB=val
    elif opt=='--o': ofile=val
    elif opt=='--valfile': valfile=val
    elif opt=='--tsv': tsv=True
    elif opt=='--igz': igz=True
    elif opt=='--list_tags': list_tags=True
    elif opt=='--csv2html': csv2html=True
    elif opt=='--extractcol': extractcol=True
    elif opt=='--deletecol': deletecol=True
    elif opt=='--renamecol': renamecol=True
    elif opt=='--cleancol': cleancol=True
    elif opt=='--usortedcol': usortedcol=True
    elif opt=='--size': size=True
    elif opt=='--colcount': colcount=True
    elif opt=='--colcount_all': colcount_all=True
    elif opt=='--colvalcount': colvalcount=True
    elif opt=='--colvalcount_all': colvalcount_all=True
    elif opt=='--colvalcounts': colvalcounts=True
    elif opt=='--colvalstats': colvalstats=True
    elif opt=='--colval_ucheck': colval_ucheck=True
    elif opt=='--subsetcols': subsetcols=True
    elif opt=='--mergecols': mergecols=True
    elif opt=='--sortbycol': sortbycol=True
    elif opt=='--filterbycol': filterbycol=True
    elif opt=='--defilterbycol': defilterbycol=True
    elif opt=='--prefixtags': prefixtags=True
    elif opt=='--fixtags': fixtags=True
    elif opt=='--addquotes': addquotes=True
    elif opt=='--fixquotes': fixquotes=True
    elif opt=='--tagprefix': tagprefix=val
    elif opt=='--addheader': addheader=re.sub(r'\s','',val)
    elif opt=='--colpairanalysis': colpairanalysis=True
    elif opt=='--convert2triples': convert2triples=True
    elif opt=='--tsv2csv': tsv2csv=True
    elif opt=='--csv2tsv': csv2tsv=True
    elif opt=='--change_delim': change_delim=True
    elif opt=='--selectrows': selectrows=True
    elif opt=='--deselectrows': deselectrows=True
    elif opt=='--deduprows': deduprows=True
    elif opt=='--rmemptyrows': rmemptyrows=True
    elif opt=='--overwrite_input_file': overwrite_input_file=True
    elif opt=='--noheader': noheader=True
    elif opt=='--numeric': numeric=True
    elif opt=='--chron': chron=True
    elif opt=='--col': col=int(val)
    elif opt=='--cols': cols=map(lambda x:int(x),re.split(r'[\s,]*',val.strip()))
    elif opt=='--coltag': coltag=val
    elif opt=='--coltagB': coltagB=val
    elif opt=='--newtag': newtag=val
    elif opt=='--colB': colB=int(val)
    elif opt=='--coltags': coltags = re.split(r'[\s,]*',val.strip())
    elif opt=='--minval': minval=val
    elif opt=='--maxval': maxval=val
    elif opt=='--eqval': eqval=val
    elif opt=='--delim': delim=val
    elif opt=='--delim_out': delim_out=val
    elif opt=='--nmax': nmax=int(val)
    elif opt=='--skip': skip=int(val)
    elif opt=='--v': verbose=1
    elif opt=='--vv': verbose=2
    else: ErrorExit('Illegal option: %s'%val)

  if not ifile: ErrorExit('ERROR: --i required.  Specify "-" for stdin.')

  delim = delim if delim else ('\t' if tsv else ',')

  if coltag:
    col=Coltag2Col(ifile,delim,igz,coltag)
    if not col: ErrorExit('ERROR: coltag "%s" not found.'%coltag)
    if verbose: print >>sys.stderr, '"%s" is column %d.'%(coltag,col)
# elif col and not noheader:
#   coltag=Col2Coltag(ifile,delim,igz,col)
#   if verbose: print >>sys.stderr, '"%s" is column %d.'%(coltag,col)
  elif coltags:
    for coltag in coltags:
      col=Coltag2Col(ifile,delim,igz,coltag)
      if not col: ErrorExit('ERROR: coltag "%s" not found.'%coltag)
      cols.append(col)
      if verbose: print >>sys.stderr, '"%s" is column %d.'%(coltag,col)
  elif cols and not noheader:
    for col in cols:
      coltag=Col2Coltag(ifile,delim,igz,col)
      coltags.append(coltag)
      if verbose: print >>sys.stderr, '"%s" is column %d.'%(coltag,col)

  if coltagB:
    colB=Coltag2Col(ifileB,delim,igz,coltagB)
    if not colB: ErrorExit('ERROR: coltag "%s" not found.'%coltagB)
    if verbose: print >>sys.stderr, '"%s" is file B column %d.'%(coltagB,colB)
  elif colB and not noheader:
    coltagB=Col2Coltag(ifileB,delim,igz,colB)
    if verbose: print >>sys.stderr, '"%s" is file B column %d.'%(coltagB,colB)

  if ifile=='-':
    if overwrite_input_file:
      ErrorExit('ERROR: --overwrite_input_file not compatible with --i "-".')
    fin = sys.stdin
  elif igz:
    fin=gzip.open(ifile)
  else:
    fin = open(ifile)
  if not fin: ErrorExit('ERROR: cannot open ifile: %s'%ifile)

  if ofile: fout=open(ofile,"w")
  elif overwrite_input_file: fout=tempfile.NamedTemporaryFile(prefix=PROG,suffix='.csv',delete=False)
  else: fout=sys.stdout
  if not fout: ErrorExit('ERROR: cannot open outfile: %s'%ofile)

  if eqval:
    eqval = float(eqval) if numeric else (datetime.datetime.strptime(eqval,"%Y%m%d") if chron else eqval)
  if minval:
    minval = float(minval) if numeric else (datetime.datetime.strptime(minval,"%Y%m%d") if chron else minval)
  if maxval:
    maxval = float(maxval) if numeric else (datetime.datetime.strptime(maxval,"%Y%m%d") if chron else maxval)

  vals=set()
  if valfile:
    fin_val=open(valfile)
    if not fin_val: ErrorExit('ERROR: cannot open valfile: %s'%valfile)
    while True:
      line=fin_val.readline()
      if not line: break
      val = float(val) if numeric else line.rstrip()
      vals.add(val)
    if verbose:
      print >>sys.stderr, '%s: input values: %d'%(PROG,len(vals))
    fin_val.close()

  n_in,n_out = 0,0

  if csv2html:
    n_in,n_out = Csv2Html(fin,fout,delim)
    print >>sys.stderr, '%s: input file: %s ; rows in: %d'%(PROG,ifile,n_in)
    print >>sys.stderr, '%s: output file: %s ; records out: %d'%(PROG,fout.name,n_out)

  elif extractcol:
    if not col: ErrorExit('ERROR: --col required.')
    n_in,n_out = CsvExtractColumn(fin,fout,col,delim,noheader,skip,nmax)
    if verbose:
      print >>sys.stderr, '%s: input file: %s ; rows in: %d'%(PROG,ifile,n_in)
      print >>sys.stderr, '%s: output file: %s ; values out: %d'%(PROG,fout.name,n_out)

  elif deletecol:
    if not col: ErrorExit('ERROR: --col required.')
    n_in,n_out = CsvDeleteColumn(fin,fout,col,delim)
    print >>sys.stderr, '%s: input file: %s ; rows in: %d'%(PROG,ifile,n_in)
    print >>sys.stderr, '%s: output file: %s ; rows out: %d'%(PROG,fout.name,n_out)

  elif renamecol:
    if not (col and newtag): ErrorExit('ERROR: (--col OR --coltag) AND --newtag required for --renamecol.')
    n_in,n_out = CsvRenameColumn(fin,fout,col,newtag,delim)
    print >>sys.stderr, '%s: input file: %s ; rows in: %d'%(PROG,ifile,n_in)
    print >>sys.stderr, '%s: output file: %s ; rows out: %d'%(PROG,fout.name,n_out)

  elif cleancol:
    if not col: ErrorExit('ERROR: --col required.')
    n_in,n_out = CsvCleanColumn(fin,fout,col,delim)
    print >>sys.stderr, '%s: input file: %s ; rows in: %d'%(PROG,ifile,n_in)
    print >>sys.stderr, '%s: output file: %s ; rows out: %d'%(PROG,fout.name,n_out)

  elif prefixtags:
    if not tagprefix: ErrorExit('ERROR: --tagprefix required.')
    n_in,n_out = CsvPrefixTags(fin,fout,tagprefix,delim)
    print >>sys.stderr, '%s: input file: %s ; rows in: %d'%(PROG,ifile,n_in)
    print >>sys.stderr, '%s: output file: %s ; rows out: %d'%(PROG,fout.name,n_out)

  elif fixtags:
    n_in,n_out = CsvFixTags(fin,fout,delim)
    print >>sys.stderr, '%s: input file: %s ; rows in: %d'%(PROG,ifile,n_in)
    print >>sys.stderr, '%s: output file: %s ; rows out: %d'%(PROG,fout.name,n_out)

  elif addquotes:
    n_in,n_out = CsvAddQuotes(fin,fout,delim)
    print >>sys.stderr, '%s: input file: %s ; rows in: %d'%(PROG,ifile,n_in)
    print >>sys.stderr, '%s: output file: %s ; rows out: %d'%(PROG,fout.name,n_out)

  elif fixquotes:
    n_in,n_out = CsvFixQuotes(fin,fout,delim)
    print >>sys.stderr, '%s: input file: %s ; rows in: %d'%(PROG,ifile,n_in)
    print >>sys.stderr, '%s: output file: %s ; rows out: %d'%(PROG,fout.name,n_out)

  elif addheader:
    n_in,n_out = CsvAddHeader(fin,fout,addheader,delim)
    print >>sys.stderr, '%s: input file: %s ; rows in: %d'%(PROG,ifile,n_in)
    print >>sys.stderr, '%s: output file: %s ; rows out: %d'%(PROG,fout.name,n_out)

  elif usortedcol:
    if not col: ErrorExit('ERROR: --col required.')
    n_in,n_out = CsvUniqueSortedColumn(fin,fout,col,numeric,chron,delim)
    print >>sys.stderr, '%s: input file: %s ; rows in: %d'%(PROG,ifile,n_in)
    print >>sys.stderr, '%s: output file: %s ; rows out: %d'%(PROG,fout.name,n_out)

  elif size:
    n_row,n_col = CsvSize(fin,delim,noheader)
    print >>sys.stderr, '%s: input file: %s ; rows: %d, cols: %d'%(PROG,ifile,n_row,n_col)

  elif colcount:
    if not col: ErrorExit('ERROR: --col required.')
    n_in,n_nonempty = CsvColumnCount_File(fin,col,delim,noheader)
    print '%d. %24s: non-empty: %3d, empty: %3d, total: %3d'%(col,coltag,n_nonempty,n_in-n_nonempty,n_in)

  elif colcount_all:
    if ifile=='-': ErrorExit('ERROR: this operation not available with --i "-".')
    coltags=Coltags(fin,delim)
    for j,tag in enumerate(coltags):
      n_in,n_nonempty = CsvColumnCount(ifile,j+1,delim,noheader,igz)
      print '%d. %24s: non-empty: %3d, empty: %3d, total: %3d'%(j+1,tag,n_nonempty,n_in-n_nonempty,n_in)

  elif colvalcount:
    if not col: ErrorExit('ERROR: --col required.')
    n_in,n_nonempty = CsvColumnCount(ifile,col,delim,noheader,igz)
    n_in,n_unique = CsvColumnValueCount_File(fin,col,numeric,chron,delim,noheader,skip,nmax)
    print '%d. %24s: non-empty: %3d, empty: %3d, unique: %3d, total: %3d'%(col,coltag,n_nonempty,n_in-n_nonempty,n_unique,n_in)

  elif colvalcount_all:
    if ifile=='-': ErrorExit('ERROR: this operation not available with --i "-".')
    coltags=Coltags(fin,delim)
    for j,tag in enumerate(coltags):
      n_in,n_nonempty = CsvColumnCount(ifile,j+1,delim,noheader,igz)
      n_in,n_unique = CsvColumnValueCount(ifile,j+1,numeric,chron,delim,noheader,skip,nmax)
      print '%d. %24s: non-empty: %3d, empty: %3d, unique: %3d, total: %3d'%(j+1,tag,n_nonempty,n_in-n_nonempty,n_unique,n_in)

  elif colvalcounts:
    if not col: ErrorExit('ERROR: --col required.')
    n_in,n_out = CsvColumnValueCounts(fin,fout,col,numeric,chron,delim,noheader,skip,nmax)

  elif colval_ucheck:
    if not col: ErrorExit('ERROR: --col required.')
    CsvColumnValueUniquenessCheck(fin,col,delim,noheader,skip,nmax)

  elif colvalstats:
    if not col: ErrorExit('ERROR: --col required.')
    n_in,n_nonempty = CsvColumnStats(fin,col,delim,noheader,skip,nmax)
    print '%d. %24s: non-empty: %3d, empty: %3d, total: %3d'%(col,coltag,n_nonempty,n_in-n_nonempty,n_in)

  elif tsv2csv:
    n_in,n_out = CsvDelimReplace(fin,fout,'\t',',')
    print >>sys.stderr, '%s: input file: %s ; rows in: %d'%(PROG,ifile,n_in)
    print >>sys.stderr, '%s: output file: %s ; rows out: %d'%(PROG,fout.name,n_out)

  elif csv2tsv:
    n_in,n_out = CsvDelimReplace(fin,fout,',','\t')
    print >>sys.stderr, '%s: input file: %s ; rows in: %d'%(PROG,ifile,n_in)
    print >>sys.stderr, '%s: output file: %s ; rows out: %d'%(PROG,fout.name,n_out)

  elif change_delim:
    if not delim_out: ErrorExit('ERROR: --delim_out required.')
    n_in,n_out = CsvDelimReplace(fin,fout,delim,delim_out)
    print >>sys.stderr, '%s: input file: %s ; rows in: %d'%(PROG,ifile,n_in)
    print >>sys.stderr, '%s: output file: %s ; rows out: %d'%(PROG,fout.name,n_out)

  elif subsetcols:
    if not cols: ErrorExit('ERROR: --cols or --coltags required.')
    n_in,n_out = CsvSubsetColumns(fin,fout,coltags,delim)
    print >>sys.stderr, '%s: input file: %s ; rows in: %d'%(PROG,ifile,n_in)
    print >>sys.stderr, '%s: output file: %s ; rows out: %d'%(PROG,fout.name,n_out)

  elif sortbycol:
    if not col: ErrorExit('ERROR: --col required.')
    n_in,n_out = CsvSortbyColumn(fin,fout,col,numeric,chron,delim)
    print >>sys.stderr, '%s: input file: %s ; rows in: %d'%(PROG,ifile,n_in)
    print >>sys.stderr, '%s: output file: %s ; rows out: %d'%(PROG,fout.name,n_out)

  elif filterbycol or defilterbycol:
    if not col: ErrorExit('ERROR: --col required.')
    n_in,n_out = CsvFilterbyColumn(fin,fout,col,numeric,chron,minval,maxval,eqval,defilterbycol,delim)
    print >>sys.stderr, '%s: input file: %s ; rows in: %d'%(PROG,ifile,n_in)
    print >>sys.stderr, '%s: output file: %s ; rows out: %d'%(PROG,fout.name,n_out)

  elif selectrows or deselectrows:
    if not col: ErrorExit('ERROR: --col required.')
    if not vals: ErrorExit('ERROR: --valfile required.')
    n_in,n_out = CsvFilterbyValset(fin,fout,col,numeric,vals,deselectrows,delim,noheader)
    print >>sys.stderr, '%s: input file: %s ; rows in: %d'%(PROG,ifile,n_in)
    print >>sys.stderr, '%s: output file: %s ; rows out: %d'%(PROG,fout.name,n_out)

  elif deduprows:
    if not col: ErrorExit('ERROR: --col required.')
    n_in,n_out = CsvDedup(fin,fout,col,numeric,delim,noheader)
    print >>sys.stderr, '%s: input file: %s ; rows in: %d'%(PROG,ifile,n_in)
    print >>sys.stderr, '%s: output file: %s ; rows out: %d'%(PROG,fout.name,n_out)

  elif rmemptyrows:
    n_in,n_out = CsvRmEmptyRows(fin,fout,delim,noheader)
    print >>sys.stderr, '%s: input file: %s ; rows in: %d'%(PROG,ifile,n_in)
    print >>sys.stderr, '%s: output file: %s ; rows out: %d'%(PROG,fout.name,n_out)

  elif colpairanalysis:
    if not cols: ErrorExit('ERROR: --cols or --coltags required.')
    CsvColPairAnalysis(fin,fout,coltags[0],coltags[1],numeric,delim,verbose)

  elif mergecols:
    if not cols: ErrorExit('ERROR: --cols or --coltags required.')
    n_in,n_out = CsvMergeColumns(fin,fout,coltags,delim)
    print >>sys.stderr, '%s: input file: %s ; rows in: %d'%(PROG,ifile,n_in)
    print >>sys.stderr, '%s: output file: %s ; rows out: %d'%(PROG,fout.name,n_out)

  elif convert2triples:
    n_in,n_out = CsvConvert2Triples(fin,fout,col,numeric,delim,skip,nmax)
    print >>sys.stderr, '%s: input file: %s ; rows in: %d'%(PROG,ifile,n_in)
    print >>sys.stderr, '%s: output file: %s ; rows out: %d'%(PROG,fout.name,n_out)

  else: # default: list_tags
    #ErrorExit('ERROR: no operation specified.\n'+USAGE)
    coltags=Coltags(fin,delim)
    for j,tag in enumerate(coltags):
      print '%d. "%s"'%(j+1,tag)

  if fout:
    fout.close()

  if overwrite_input_file and n_out>0:
    fin.close()
    fpath_tmp = fout.name
    shutil.copyfile(fpath_tmp,ifile)
    os.remove(fpath_tmp)
    print >>sys.stderr, '%s: input file OVERWRITTEN: %s'%(PROG,ifile)
