import gzip

def get_pw(f):
  f = open(f, 'r')
  pw = f.readline().strip()
  return pw

def conn_tcrd(init):
  if 'dbhost' in init:
    dbhost = init['dbhost']
  else:
    dbhost = DBHOST
  if 'dbport' in init:
    dbport = init['dbport']
  else:
    dbport = 3306
  if 'dbname' in init:
    dbname = init['dbname']
  else:
    dbname = DBNAME
  if 'dbuser' in init:
    dbuser = init['dbuser']
  else:
    dbuser = 'smathias'
  if 'pwfile' in init:
    dbauth = get_pw(init['pwfile'])
  else:
    dbauth = get_pw('/home/smathias/.dbirc')
  conn = mysql.connect(host=dbhost, port=dbport, db=dbname, user=dbuser, passwd=dbauth,
                       charset='utf8', init_command='SET NAMES UTF8')
  return conn

def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])

def wcl(fname):
  with open(fname) as f:
    for i, l in enumerate(f):
      pass
  return i + 1

def gzwcl(fname):
  with gzip.open(fname, 'rb') as f:
    for i, l in enumerate(f):
      pass
  return i + 1
