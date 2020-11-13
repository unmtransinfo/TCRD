#! /usr/bin/env python
'''
  Python Interfate to IDG-KMC Target Central Repository Database with support for Metapath ML

  Steve Mathias
  smathias@salud.unm.edu
  Time-stamp: <2020-11-12 09:59:41 smathias>
'''
from __future__ import print_function
import sys
import platform
#import MySQLdb as mysql
import mysql.connector as mysql
from contextlib import closing
from collections import defaultdict
import logging
import json
import csv

class DBAdaptor:
  # Default config
  _DBHost = 'localhost' ;
  _DBPort = 3306 ;
  _DBName = 'tcrd7' ;
  _DBUser = 'smathias'
  if platform.system() == 'Darwin':
    _PWFile = '/Users/smathias/.dbirc'
  else:
    _PWFile = '/home/smathias/.dbirc'
  _LogFile = '/tmp/TCRD_DBA.log'
  _LogLevel = logging.WARNING

  def __init__(self, init):
    # DB Connection
    if 'dbhost' in init:
      dbhost = init['dbhost']
    else:
      dbhost = self._DBHost
    if 'dbport' in init:
      dbport = init['dbport']
    else:
      dbport = self._DBPort
    if 'dbname' in init:
      dbname = init['dbname']
    else:
      dbname = self._DBName
    if 'dbuser' in init:
      dbuser = init['dbuser']
    else:
      dbuser = self._DBUser
    if 'pwfile' in init:
      dbauth = self._get_auth(init['pwfile'])
    else:
      dbauth = self._get_auth(self._PWFile)
    self._connect(host=dbhost, port=dbport, db=dbname, user=dbuser, passwd=dbauth)

    # Logging
    # levels are:
    # CRITICAL 50
    # ERROR    40
    # WARNING  30
    # INFO     20
    # DEBUG    10
    # NOTSET	0
    if 'logger_name' in init:
      # use logger from calling module
      ln = init['logger_name'] + '.auxiliary.DBAdaptor'
      self._logger = logging.getLogger(ln)
    else:
      if 'logfile' in init:
        lfn = init['logfile']
      else:
        lfn = self._LogFile
      if 'loglevel' in init:
        ll = init['loglevel']
      else:
        ll = self._LogLevel
      self._logger = logging.getLogger(__name__)
      self._logger.propagate = False # turns off console logging
      fh = logging.FileHandler(lfn)
      self._logger.setLevel(ll)
      fmtr = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
      fh.setFormatter(fmtr)
      self._logger.addHandler(fh)
    self._logger.info('Creating new TCRD DBAdaptor instance')

    # Initialize the error flag and message
    #self._error = 0
    #self._error_msg = ''

    self._cache_info_types()
    self._cache_xref_types()
    self._cache_expression_types()
    self._cache_phenotype_types()
    #self._cache_gene_attribute_types()

  def __del__(self):
    #print "Closing connection"
    self._conn.close()

  def test(self):
    self._logger.info('test() entry')
    curs = self._conn.cursor()
    try:
      curs.execute('select 1;')
      self._logger.debug('cursor is open')
    except mysql.Error, e:
      try:
        self._logger.debug( 'cursor is closed')
        print("MySQL Error [%d]: %s" % (e.args[0], e.args[1]))
      except IndexError, ie:
        self._logger.debug( 'cursor is closed')
        print("MySQL Error: %s" % str(ie))
    #except mysql.ProgrammingError:
    if self._conn.open:
      self._logger.debug( 'connection is open')
    else:
     self._logger.debug( 'connection is closed')
    self._logger.info('test() exit')

  def get_dbinfo(self):
    sql = 'SELECT * FROM dbinfo'
    cur = self._conn.cursor(dictionary=True)
    cur.execute(sql)
    row = cur.fetchone()
    return row

  def warning(*objs):
    print("TCRD DBAdaptor WARNING: ", *objs, file=sys.stderr)

  def error(*objs):
    print("TCRD DBAdaptor ERROR: ", *objs, file=sys.stderr)

  #
  # Create Methods
  #
  def ins_target(self, init):
    '''
    Function  : Insert a target and all associated data
    Arguments : Dictionary containing target data.
    Returns   : Integer containing target.id
    Example   : tid = dba->ins_target(init) ;
    Scope     : Public
    Comments  : So far this and ins_protein() handle only data from UniProt API
    '''
    if 'name' in init and 'ttype' in init:
      params = [init['name'], init['ttype']]
    else:
      self.warning("Invalid parameters sent to ins_target(): ", init)
      return False
    cols = ['name', 'ttype']
    vals = ['%s','%s']
    for optcol in ['description', 'comment', 'fam', 'tdl']:
      if optcol in init:
        cols.append(optcol)
        vals.append('%s')
        params.append(init[optcol])
    sql = "INSERT INTO target (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%','.join([str(p) for p in params]))
    target_id = None
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, tuple(params))
        target_id = curs.lastrowid
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_target(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    if 'pathways' in init:
      for d in init['pathways']:
        d['target_id'] = target_id
        rv = self.ins_pathway(d, commit=False)
        if not rv:
          return False
    if 'diseases' in init:
      for d in init['diseases']:
        d['target_id'] = target_id
        rv = self.ins_disease(d, commit=False)
        if not rv:
          return False
    for protein in init['components']['protein']:
      protein_id = self.ins_protein(protein, commit=False)
      if not protein_id:
        return False
      sql = "INSERT INTO t2tc (target_id, protein_id) VALUES (%s, %s)"
      params = (target_id, protein_id)
      self._logger.debug("SQLpat: %s"%sql)
      self._logger.debug("SQLparams: %s"%','.join([str(p) for p in params]))
      with closing(self._conn.cursor()) as curs:
        try:
          curs.execute(sql, tuple(params))
        except mysql.Error, e:
          self._conn.rollback()
          self._logger.error("MySQL Error in ins_target(): %s"%str(e))
          self._logger.error("SQLpat: %s"%sql)
          self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
          return False

    try:
      self._conn.commit()
    except mysql.Error, e:
      self._conn.rollback()
      self._logger.error("MySQL commit error in ins_target(): %s"%str(e))
      return False

    return target_id

  def ins_protein(self, init, commit=True):
    if 'name' in init and 'description' in init and 'uniprot' in init:
      params = [init['name'], init['description'], init['uniprot']]
    else:
      self.warning("Invalid parameters sent to ins_protein(): ", init)
      return False
    cols = ['name', 'description', 'uniprot']
    vals = ['%s','%s', '%s']
    for optcol in ['up_version', 'geneid', 'sym', 'family', 'chr', 'seq', 'dtoid', 'stringid']:
      if optcol in init:
        cols.append(optcol)
        vals.append('%s')
        params.append(init[optcol])
    sql = "INSERT INTO protein (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%','.join([str(p) for p in params]))
    self._logger.debug("Cols: %d, Vals: %d, Params: %d"%(len(cols), len(vals), len(params)))
    protein_id = None
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, tuple(params))
        protein_id = curs.lastrowid
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_protein(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    for d in init['aliases']:
      d['protein_id'] = protein_id
      rv = self.ins_alias(d, commit=False)
      if not rv:
        return False
    for d in init['xrefs']:
      d['protein_id'] = protein_id
      rv = self.ins_xref(d, commit=False)
      if not rv:
        return False
    for d in init['goas']:
      d['protein_id'] = protein_id
      rv = self.ins_goa(d, commit=False)
      if not rv:
        return False
    for d in init['tdl_infos']:
      d['protein_id'] = protein_id
      rv = self.ins_tdl_info(d, commit=False)
      if not rv:
        return False
    if 'pathways' in init:
      for d in init['pathways']:
        d['target_id'] = target_id
        rv = self.ins_pathway(d, commit=False)
        if not rv:
          return False
    if 'diseases' in init:
      for d in init['diseases']:
        d['target_id'] = target_id
        rv = self.ins_disease(d, commit=False)
        if not rv:
          return False
    
    try:
      self._conn.commit()
    except mysql.Error, e:
      self._conn.rollback()
      self._logger.error("MySQL commit error in ins_target(): %s"%str(e))
      return False

    return target_id

  def ins_protein(self, init, commit=True):
    if 'name' in init and 'description' in init and 'uniprot' in init:
      params = [init['name'], init['description'], init['uniprot']]
    else:
      self.warning("Invalid parameters sent to ins_protein(): ", init)
      return False
    cols = ['name', 'description', 'uniprot']
    vals = ['%s','%s', '%s']
    for optcol in ['up_version', 'geneid', 'sym', 'family', 'chr', 'seq', 'dtoid', 'stringid']:
      if optcol in init:
        cols.append(optcol)
        vals.append('%s')
        params.append(init[optcol])
    sql = "INSERT INTO protein (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%','.join([str(p) for p in params]))
    self._logger.debug("Cols: %d, Vals: %d, Params: %d"%(len(cols), len(vals), len(params)))
    protein_id = None
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, tuple(params))
        protein_id = curs.lastrowid
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_protein(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    if 'aliases' in init:
      for d in init['aliases']:
        d['protein_id'] = protein_id
        rv = self.ins_alias(d, commit=False)
        if not rv:
          return False
    if 'xrefs' in init:
      for d in init['xrefs']:
        d['protein_id'] = protein_id
        rv = self.ins_xref(d, commit=False)
        if not rv:
          return False
    if 'tdl_infos' in init:
      for d in init['tdl_infos']:
        d['protein_id'] = protein_id
        rv = self.ins_tdl_info(d, commit=False)
        if not rv:
          return False
    if 'goas' in init:
      for d in init['goas']:
        d['protein_id'] = protein_id
        rv = self.ins_goa(d, commit=False)
        if not rv:
          return False
    if 'expressions' in init:
      for d in init['expressions']:
        d['protein_id'] = protein_id
        rv = self.ins_expression(d, commit=False)
        if not rv:
          return False
    if 'pathways' in init:
      for d in init['pathways']:
        d['protein_id'] = protein_id
        rv = self.ins_pathway(d, commit=False)
        if not rv:
          return False
    if 'diseases' in init:
      for d in init['diseases']:
        d['protein_id'] = protein_id
        rv = self.ins_disease(d, commit=False)
        if not rv:
          return False
    if 'features' in init:
      for d in init['features']:
        d['protein_id'] = protein_id
        rv = self.ins_feature(d, commit=False)
        if not rv:
          return False

    if commit:
      try:
        self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL commit error in ins_protein: %s")
        return False

    return protein_id

  def ins_nhprotein(self, init, commit=True):
    if 'uniprot' in init and 'name' in init and 'species' in init and 'taxid' in init:
      params = [init['uniprot'], init['name'], init['species'], init['taxid']]
    else:
      self.warning("Invalid parameters sent to ins_nhprotein(): ", init)
      return False
    cols = ['uniprot', 'name', 'species', 'taxid']
    vals = ['%s','%s','%s','%s']
    for optcol in ['sym', 'description', 'geneid', 'stringid']:
      if optcol in init:
        cols.append(optcol)
        vals.append('%s')
        params.append(init[optcol])
    sql = "INSERT INTO nhprotein (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%','.join([str(p) for p in params]))
    self._logger.debug("Cols: %d, Vals: %d, Params: %d"%(len(cols), len(vals), len(params)))
    nhprotein_id = None
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, tuple(params))
        nhprotein_id = curs.lastrowid
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_nhprotein(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    if 'xrefs' in init:
      for d in init['xrefs']:
        d['nhprotein_id'] = nhprotein_id
        rv = self.ins_xref(d, commit=False)
        if not rv:
          return False
    
    try:
      self._conn.commit()
    except mysql.Error, e:
      self._conn.rollback()
      self._logger.error("MySQL commit error in ins_nhprotein(): %s"%str(e))
      return False

    return nhprotein_id

  def ins_dataset(self, init):
    if 'name' in init and 'source' in init :
      params = [init['name'], init['source']]
    else:
      self.warning("Invalid parameters sent to ins_dataset(): ", init)
      return False
    cols = ['name', 'source']
    vals = ['%s','%s']
    for optcol in ['app', 'app_version', 'datetime', 'url', 'comments']:
      if optcol in init:
        cols.append(optcol)
        vals.append('%s')
        params.append(init[optcol])
    sql = "INSERT INTO dataset (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%','.join([str(p) for p in params]))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, tuple(params))
        dataset_id = curs.lastrowid
        self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        msg = "MySQL Error: %s" % str(e)
        self._logger.error(msg)
        return False
    return dataset_id

  def ins_provenance(self, init):
    if 'dataset_id' in init and 'table_name' in init :
      params = [init['dataset_id'], init['table_name']]
    else:
      self.warning("Invalid parameters sent to ins_provenance(): ", init)
      return False
    cols = ['dataset_id', 'table_name']
    vals = ['%s','%s']
    for optcol in ['column_name', 'where_clause', 'comment']:
      if optcol in init:
        cols.append(optcol)
        vals.append('%s')
        params.append(init[optcol])
    sql = "INSERT INTO provenance (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%','.join([str(p) for p in params]))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, tuple(params))
        self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        msg = "MySQL Error: %s" % str(e)
        self._logger.error(msg)
        return False
    return True

  def ins_alias(self, init, commit=True):
    if 'protein_id' not in init or 'type' not in init or 'dataset_id' not in init or 'value' not in init:
      self.warning("Invalid parameters sent to ins_alias(): ", init)
      return False
    sql = "INSERT INTO alias (protein_id, type, dataset_id, value) VALUES (%s, %s, %s, %s)"
    params = (init['protein_id'], init['type'], init['dataset_id'], init['value'])
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %d, %s, %d, %s"%params)
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
        if commit: self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_alias(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    return True

  def ins_xref(self, init, commit=True):
    if 'xtype' in init and 'dataset_id' in init and 'value' in init:
      params = [init['xtype'], init['dataset_id'], init['value']]
    else:
      self.warning("Invalid parameters sent to ins_xref(): ", init)
      return False
    if 'protein_id' in init:
      cols = ['protein_id', 'xtype', 'dataset_id', 'value']
      vals = ['%s','%s','%s','%s']
      params.insert(0, init['protein_id'])
    elif 'target_id' in init:
      cols = ['target_id', 'xtype', 'dataset_id', 'value']
      vals = ['%s','%s','%s','%s']
      params.insert(0, init['target_id'])
    elif 'nhprotein_id' in init:
      cols = ['nhprotein_id', 'xtype', 'dataset_id', 'value']
      vals = ['%s','%s','%s','%s']
      params.insert(0, init['nhprotein_id'])
    else:
      self.warning("Invalid parameters sent to ins_xref(): ", init)
      return False
    if 'xtra' in init:
      cols.append('xtra')
      vals.append('%s')
      params.append(init['xtra'])
    sql = "INSERT INTO xref (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%','.join([str(p) for p in params]))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
        if commit: self._conn.commit()
      except mysql.Error, e:
        if 'Duplicate entry' in e[1] and "key 'xref_idx5'" in e[1]:
          pass
        else:
          self._conn.rollback()
          self._logger.error("MySQL Error in ins_xref(): %s"%str(e))
          self._logger.error("SQLpat: %s"%sql)
          self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
          return False
    return True

  def ins_generif(self, init, commit=True):
    if 'protein_id' in init and 'pubmed_ids' in init and 'text' in init:
      params = (init['protein_id'], init['pubmed_ids'], init['text'])
    else:
      self.warning("Invalid parameters sent to ins_generif(): ", init)
      return False
    sql = "INSERT INTO generif (protein_id, pubmed_ids, text) VALUES (%s, %s, %s)"
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %d, %s, %s"%params)
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
        if commit: self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_generif(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    return True

  def ins_goa(self, init, commit=True):
    if 'protein_id' in init and 'go_id' in init:
      params = [init['protein_id'], init['go_id']]
    else:
      self.warning("Invalid parameters sent to ins_goa(): ", init)
      return False
    cols = ['protein_id', 'go_id']
    vals = ['%s','%s']
    for optcol in ['go_term', 'evidence', 'goeco', 'assigned_by']:
      if optcol in init:
        cols.append(optcol)
        vals.append('%s')
        params.append(init[optcol])
    sql = "INSERT INTO goa (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%','.join([str(p) for p in params]))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
        if commit: self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_goa(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    return True

  def ins_tdl_info(self, init, commit=True):
    if 'itype' in init:
      itype = init['itype']
    else:
      self.warning("Invalid parameters sent to ins_tdl_info(): ", init)
      return False
    if 'string_value' in init:
      val_col = 'string_value'
      value = init['string_value']
    elif 'integer_value' in init:
      val_col = 'integer_value'
      value = init['integer_value']
    elif 'number_value' in init:
      val_col = 'number_value'
      value = init['number_value']
    elif 'boolean_value' in init:
      val_col = 'boolean_value'
      value = init['boolean_value']
    elif 'date_value' in init:
      val_col = 'date_value'
      value = init['date_value']
    else:
      self.warning("Invalid parameters sent to ins_tdl_info(): ", init)
      return False
    if 'protein_id' in init:
      xid = init['protein_id']
      sql = "INSERT INTO tdl_info (protein_id, itype, %s)" % val_col
    elif 'target_id' in init:
      xid = init['target_id']
      sql = "INSERT INTO tdl_info (target_id, itype, %s)" % val_col
    else:
      self.warning("Invalid parameters sent to ins_tdl_info(): ", init)
      return False
    sql += " VALUES (%s, %s, %s)"
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %d, %s, %s"%(xid, itype, str(value)))

    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, (xid, itype, value))
        if commit: self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_tdl_info(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(xid), itype, str(value)]))
        return False
    return True

  def ins_expression(self, init, commit=True):
    if 'etype' in init and 'tissue' in init:
      params = [init['etype'], init['tissue']]
    else:
      self.warning("Invalid parameters sent to ins_expression(): ", init)
      return False
    cols = ['etype', 'tissue']
    vals = ['%s','%s']
    if 'protein_id' in init:
      cols = ['protein_id', 'etype', 'tissue']
      vals = ['%s','%s','%s']
      params.insert(0, init['protein_id'])
    elif 'target_id' in init:
      cols = ['target_id', 'etype', 'tissue']
      vals = ['%s','%s','%s']
      params.insert(0, init['target_id'])
    else:
      self.warning("Invalid parameters sent to ins_expression(): ", init)
      return False
    for optcol in ['qual_value', 'string_value', 'number_value', 'boolean_value', 'pubmed_id', 'evidence', 'zscore', 'conf', 'oid', 'confidence', 'url', 'cell_id', 'uberon_id']:
      if optcol in init:
        cols.append(optcol)
        vals.append('%s')
        params.append(init[optcol])
    sql = "INSERT INTO expression (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%", ".join([str(p) for p in params]))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
        if commit: self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_expression(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    return True

  def ins_gtex(self, init, commit=True):
    if 'protein_id' in init and 'tissue' in init and 'gender' in init and 'tpm' in init and 'tpm_level' in init:
      cols = ['protein_id', 'tissue', 'gender', 'tpm', 'tpm_level']
      vals = ['%s','%s', '%s','%s','%s']
      params = [init['protein_id'], init['tissue'], init['gender'], init['tpm'], init['tpm_level']]
    else:
      self.warning("Invalid parameters sent to ins_gtex(): ", init)
      return False
    for optcol in ['tpm_rank', 'tpm_rank_bysex', 'tpm_level_bysex', 'tpm_f', 'tpm_m', 'log2foldchange', 'tau', 'tau_bysex', 'uberon_id']:
      if optcol in init:
        cols.append(optcol)
        vals.append('%s')
        params.append(init[optcol])
    sql = "INSERT INTO gtex (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%", ".join([str(p) for p in params]))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
        if commit: self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_gtex(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    return True
  
  def ins_drug_activity(self, init, commit=True):
    if 'target_id' in init and 'drug' in init and 'dcid' in init and 'has_moa' in init:
      params = [init['target_id'], init['drug'], init['dcid'], init['has_moa']]
    else:
      self.warning("Invalid parameters sent to ins_drug_activity(): ", init)
      return False
    cols = ['target_id', 'drug', 'dcid', 'has_moa']
    vals = ['%s','%s','%s','%s']
    for optcol in ['act_value', 'act_type', 'action_type', 'source', 'reference', 'smiles', 'cmpd_chemblid', 'nlm_drug_info']:
      if optcol in init:
        cols.append(optcol)
        vals.append('%s')
        params.append(init[optcol])
    sql = "INSERT INTO drug_activity (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%','.join([str(p) for p in params]))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, tuple(params))
        if commit: self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_drug_activity(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    return True

  def ins_cmpd_activity(self, init, commit=True):
    if 'target_id' in init and 'catype' in init and 'cmpd_id_in_src' in init:
      params = [init['target_id'], init['catype'], init['cmpd_id_in_src']]
    else:
      self.warning("Invalid parameters sent to ins_cmpd_activity(): ", init)
      return False
    cols = ['target_id', 'catype', 'cmpd_id_in_src']
    vals = ['%s','%s','%s']
    for optcol in ['cmpd_name_in_src', 'smiles', 'act_value', 'act_type', 'reference', 'pubmed_ids', 'cmpd_pubchem_cid']:
      if optcol in init:
        cols.append(optcol)
        vals.append('%s')
        params.append(init[optcol])
    sql = "INSERT INTO cmpd_activity (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%','.join([str(p) for p in params]))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, tuple(params))
        if commit: self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_cmpd_activity(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    return True

  def ins_phenotype(self, init, commit=True):
    if 'ptype' not in init:
      self.warning("Invalid parameters sent to ins_phenotype(): ", init)
      return False
    if 'protein_id' in init:
      cols = ['protein_id', 'ptype']
      vals = ['%s','%s']
      params = [init['protein_id'], init['ptype']]
    elif 'nhprotein_id' in init:
      cols = ['nhprotein_id', 'ptype']
      vals = ['%s','%s']
      params = [init['nhprotein_id'], init['ptype']]
    else:
      self.warning("Invalid parameters sent to ins_phenotype(): ", init)
      return False
    for optcol in ['trait', 'top_level_term_id', 'top_level_term_name', 'term_id', 'term_name', 'term_description', 'p_value', 'percentage_change', 'effect_size', 'procedure_name', 'parameter_name', 'gp_assoc', 'statistical_method', 'sex']:
      if optcol in init:
        cols.append(optcol)
        vals.append('%s')
        params.append(init[optcol])
    sql = "INSERT INTO phenotype (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%','.join([str(p) for p in params]))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, tuple(params))
        if commit: self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_phenotype(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    return True

  def ins_gwas(self, init, commit=True):
    if 'protein_id' in init and 'disease_trait' in init:
      params = [init['protein_id'], init['disease_trait']]
    else:
      self.warning("Invalid parameters sent to ins_gwas(): ", init)
      return False
    cols = ['protein_id', 'disease_trait']
    vals = ['%s','%s']
    for optcol in ['snps', 'pmid', 'study', 'context', 'intergenic', 'p_value', 'or_beta', 'cnv', 'mapped_trait', 'mapped_trait_uri']:
      if optcol in init:
        cols.append(optcol)
        vals.append('%s')
        params.append(init[optcol])
    sql = "INSERT INTO gwas (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%','.join([str(p) for p in params]))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, tuple(params))
        if commit: self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_gwas(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    return True

  def ins_ppi(self, init, commit=True):
    if 'ppitype' in init and 'protein1_id' in init and 'protein2_id' in init:
      params = [init['ppitype'], init['protein1_id'], init['protein2_id']]
    else:
      self.warning("Invalid parameters sent to ins_ppi(): ", init)
      return False
    cols = ['ppitype', 'protein1_id', 'protein2_id']
    vals = ['%s','%s','%s']
    for optcol in ['protein1_str', 'protein2_str', 'p_int', 'p_ni', 'p_wrong', 'evidence', 'interaction_type', 'score']:
      if optcol in init:
        cols.append(optcol)
        vals.append('%s')
        params.append(init[optcol])
    sql = "INSERT INTO ppi (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%','.join([str(p) for p in params]))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, tuple(params))
        if commit: self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_ppi(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    return True

  def ins_tdl_update_log(self, init, commit=True):
    if 'target_id' in init and 'old_tdl' in init and 'new_tdl' in init and 'person' in init:
      params = [init['target_id'], init['old_tdl'], init['new_tdl'], init['person']]
    else:
      self.warning("Invalid parameters sent to ins_tdl_update_log(): ", init)
      return False
    cols = ['target_id', 'old_tdl', 'new_tdl', 'person']
    vals = ['%s','%s','%s','%s']
    for optcol in ['explanation', 'application', 'app_version']:
      if optcol in init:
        cols.append(optcol)
        vals.append('%s')
        params.append(init[optcol])
    sql = "INSERT INTO tdl_update_log (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%','.join([str(p) for p in params]))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, tuple(params))
        if commit: self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_tdl_update_log(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    return True

  def ins_disease(self, init, commit=True):
    if 'dtype' in init and 'name' in init:
      cols = ['dtype', 'name']
      params = [init['dtype'], init['name']]
    else:
      self.warning("Invalid parameters sent to ins_disease(): ", init)
      return False
    if 'protein_id' in init:
      cols.insert(0, 'protein_id')
      vals = ['%s','%s','%s']
      params.insert(0, init['protein_id'])
    elif 'target_id' in init:
      cols.insert(0, 'target_id')
      vals = ['%s','%s','%s']
      params.insert(0, init['target_id'])
    else:
      self.warning("Invalid parameters sent to ins_disease(): ", init)
      return False
    for optcol in ['evidence', 'description', 'reference', 'zscore', 'conf', 'did', 'drug_name', 'log2foldchange', 'pvalue', 'score', 'source', 'O2s', 'S2O']:
      if optcol in init:
        cols.append(optcol)
        vals.append('%s')
        params.append(init[optcol])
    sql = "INSERT INTO disease (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%','.join([str(p) for p in params]))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, tuple(params))
        if commit: self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_disease(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    return True

  def ins_ortholog_disease(self, init, commit=True):
    if 'did' in init and 'name' in init and 'protein_id' in init and 'ortholog_id' in init and 'score' in init:
      cols = ['protein_id', 'did', 'name', 'ortholog_id', 'score']
      vals = ['%s','%s','%s','%s','%s']
      params = [init['protein_id'], init['did'], init['name'], init['ortholog_id'], init['score']]
    else:
      self.warning("Invalid parameters sent to ins_ortholog_disease(): ", init)
      return False
    sql = "INSERT INTO ortholog_disease (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%','.join([str(p) for p in params]))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, tuple(params))
        if commit: self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_ortholog_disease(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    return True

  def ins_pathway(self, init, commit=True):
    if 'pwtype' in init and 'name' in init:
      pwtype = init['pwtype']
      name = init['name']
    else:
      self.warning("Invalid parameters sent to ins_pathway(): ", init)
      return False
    if 'protein_id' in init:
      cols = ['protein_id', 'pwtype', 'name']
      vals = ['%s','%s', '%s']
      params = [ init['protein_id'], pwtype, name ]
    elif 'target_id' in init:
      cols = ['target_id', 'pwtype', 'name']
      vals = ['%s','%s','%s']
      params = [ init['target_id'], pwtype, name ]
    else:
      self.warning("Invalid parameters sent to ins_pathway(): ", init)
      return False
    for optcol in ['id_in_source', 'description', 'url']:
      if optcol in init:
        cols.append(optcol)
        vals.append('%s')
        params.append(init[optcol])
    sql = "INSERT INTO pathway (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%','.join([str(p) for p in params]))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
        if commit: self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_pathway(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    return True

  def ins_mlp_assay_info(self, init, commit=True):
    if 'protein_id' in init and 'assay_name' in init and 'method' in init:
      params = [init['protein_id'], init['assay_name'], init['method']]
    else:
      self.warning("Invalid parameters sent to ins_mlp_assay_info(): ", init)
      return False
    cols = ['protein_id', 'assay_name', 'method']
    vals = ['%s','%s', '%s']
    for optcol in ['aid', 'active_sids', 'inactive_sids', 'iconclusive_sids', 'total_sids']:
      if optcol in init:
        cols.append(optcol)
        vals.append('%s')
        params.append(init[optcol])
    sql = "INSERT INTO mlp_assay_info (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%(", ".join([str(p) for p in params])))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
        if commit: self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_mlp_assay_info(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    return True

  def ins_protein_similarity(self, init, commit=True):
    if 'pid1' not in init or 'pid2' not in init:
      self.warning("Invalid parameters sent to ins_protein_similarity(): ", init)
      return False
    cols = ['pid1', 'pid2']
    vals = ['%s','%s']
    params = [ init['pid1'], init['pid2'] ]
    for optcol in ['local_score', 'global_score']:
      if optcol in init:
        cols.append(optcol)
        vals.append('%s')
        params.append(init[optcol])
    sql = "INSERT INTO protein_similarity (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%','.join([str(p) for p in params]))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
        if commit: self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_protein_similarity(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    return True

  def ins_gene_attribute_type(self, init, commit=True):
    if 'name' in init and 'association' in init and 'description' in init and 'resource_group' in init and 'measurement' in init and 'attribute_group' in init and 'attribute_type' in init:
      params = [init['name'], init['association'], init['description'], init['resource_group'], init['measurement'], init['attribute_group'], init['attribute_type']]
    else:
      self.warning("Invalid parameters sent to ins_gene_attribute(): ", init)
      return False
    cols = ['name', 'association', 'description', 'resource_group', 'measurement', 'attribute_group', 'attribute_type']
    vals = ['%s','%s','%s','%s','%s','%s','%s']
    for optcol in ['pubmed_ids', 'url']:
      if optcol in init:
        cols.append(optcol)
        vals.append('%s')
        params.append(init[optcol])
    sql = "INSERT INTO gene_attribute_type (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%','.join([str(p) for p in params]))
    gat_it = None
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
        gat_id = curs.lastrowid
        if commit: self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_gene_attribute_type(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    return gat_id

  def ins_gene_attribute(self, init, commit=True):
    if 'protein_id' in init and 'gat_id' in init and 'name' in init and 'value' in init:
      params = [init['protein_id'], init['gat_id'], init['name'], init['value']]
    else:
      self.warning("Invalid parameters sent to ins_gene_attribute(): ", init)
      return False
    sql = "INSERT INTO gene_attribute (protein_id, gat_id, name, value) VALUES (%s, %s, %s, %s)"
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%','.join([str(p) for p in params]))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
        if commit: self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_gene_attribute(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    return True

  def ins_grant(self, init, commit=True):
    if 'target_id' in init and 'appid' in init and 'full_project_num' in init and 'activity' in init and 'funding_ics' in init and 'year' in init and 'cost' in init:
      params = [init['target_id'], init['appid'], init['full_project_num'], init['activity'], init['funding_ics'], init['year'], init['cost']]
    else:
      self.warning("Invalid parameters sent to ins_grant(): ", init)
      return False
    cols = ['target_id', 'appid', 'full_project_num', 'activity', 'funding_ics', 'year', 'cost']
    vals = ['%s', '%s', '%s', '%s', '%s', '%s', '%s']
    sql = "INSERT INTO `grant` (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%','.join([str(p) for p in params]))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
        if commit: self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_grant(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    return True

  def ins_tinx_disease(self, init, commit=True):
    if 'doid' in init and 'name' in init:
      params = [init['doid'], init['name']]
    else:
      self.warning("Invalid parameters sent to ins_tinx_disease(): ", init)
      return False
    cols = ['doid', 'name']
    vals = ['%s','%s']
    for optcol in ['parent_doid', 'num_children', 'summary', 'num_important_targets', 'score']:
      if optcol in init:
        cols.append(optcol)
        vals.append('%s')
        params.append(init[optcol])
    sql = "INSERT INTO tinx_disease (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%','.join([str(p) for p in params]))
    did = None
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
        did = curs.lastrowid
        if commit: self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_tinx_disease(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    return did

  def ins_tinx_novelty(self, init, commit=True):
    if 'protein_id' in init and 'score' in init:
      params = [init['protein_id'], init['score']]
    else:
      self.warning("Invalid parameters sent to ins_tinx_novelty(): ", init)
      return False
    sql = "INSERT INTO tinx_novelty (protein_id, score) VALUES (%s, %s)"
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%','.join([str(p) for p in params]))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
        if commit: self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_tinx_novelty(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    return True

  def ins_tinx_importance(self, init, commit=True):
    if 'protein_id' in init and 'disease_id' in init and 'score' in init:
      params = [init['protein_id'], init['disease_id'], init['score']]
    else:
      self.warning("Invalid parameters sent to ins_tinx_importance(): ", init)
      return False
    sql = "INSERT INTO tinx_importance (protein_id, disease_id, score) VALUES (%s, %s, %s)"
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%','.join([str(p) for p in params]))
    iid = None
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
        iid = curs.lastrowid
        if commit: self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_tinx_importance(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    return iid

  def ins_tinx_articlerank(self, init, commit=True):
    if 'importance_id' in init and 'pmid' in init and 'rank' in init:
      params = [init['importance_id'], init['pmid'], init['rank']]
    else:
      self.warning("Invalid parameters sent to ins_tinx_articlerank(): ", init)
      return False
    sql = "INSERT INTO tinx_articlerank (importance_id, pmid, rank) VALUES (%s, %s, %s)"
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%','.join([str(p) for p in params]))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
        if commit: self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_tinx_articlerank(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    return True

  def ins_panther_class(self, init, commit=True):
    if 'pcid' in init and 'name' in init:
      params = [init['pcid'], init['name']]
    else:
      self.warning("Invalid parameters sent to ins_panther_class(): ", init)
      return False
    cols = ['pcid', 'name']
    vals = ['%s','%s']
    for optcol in ['description', 'parent_pcids']:
      if optcol in init:
        cols.append(optcol)
        vals.append('%s')
        params.append(init[optcol])# if 'treenum' in init:
    sql = "INSERT INTO panther_class (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%(", ".join([str(p) for p in params])))
    pcid = None
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
        pcid = curs.lastrowid
        if commit: self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_panther_class(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    return pcid

  def ins_p2pc(self, init, commit=True):
    if 'protein_id' in init and 'panther_class_id' in init:
      params = [init['protein_id'], init['panther_class_id']]
    else:
      self.warning("Invalid parameters sent to ins_p2pc(): ", init)
      return False
    sql = "INSERT INTO p2pc (protein_id, panther_class_id) VALUES (%s, %s)"
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%(", ".join([str(p) for p in params])))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
        if commit: self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_p2pc(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    return True

  def ins_dto(self, init, commit=True):
    if 'dtoid' in init and 'name' in init:
      cols = ['dtoid', 'name']
      vals = ['%s','%s']
      params = [init['dtoid'], init['name']]
    else:
      self.warning("Invalid parameters sent to ins_dto(): ", init)
      return False
    for optcol in ['def', 'parent_id']:
      if optcol in init:
        cols.append(optcol)
        vals.append('%s')
        if optcol == 'def':
          init[optcol] = init[optcol].encode('ascii', 'ignore').decode('ascii')
        params.append(init[optcol])
    sql = "INSERT INTO dto (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    #self._logger.debug("SQLparams: %s"%(", ".join([str(p) for p in params])))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
        if commit: self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_dto(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    return True

  def ins_pmscore(self, init, commit=True):
    if 'protein_id' in init and 'year' in init and 'score' in init:
      params = [init['protein_id'], init['year'], init['score']]
    else:
      self.warning("Invalid parameters sent to ins_pmscore(): ", init)
      return False
    sql = "INSERT INTO pmscore (protein_id, year, score) VALUES (%s, %s, %s)"
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%','.join([str(p) for p in params]))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
        if commit: self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_pmscore(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    return True

  def ins_ptscore(self, init, commit=True):
    if 'protein_id' in init and 'year' in init and 'score' in init:
      params = [init['protein_id'], init['year'], init['score']]
    else:
      self.warning("Invalid parameters sent to ins_ptscore(): ", init)
      return False
    sql = "INSERT INTO ptscore (protein_id, year, score) VALUES (%s, %s, %s)"
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%','.join([str(p) for p in params]))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
        if commit: self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_ptscore(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    return True

  def ins_patent_count(self, init, commit=True):
    if 'protein_id' in init and 'year' in init and 'count' in init:
      params = [init['protein_id'], init['year'], init['count']]
    else:
      self.warning("Invalid parameters sent to ins_patent_count(): ", init)
      return False
    sql = "INSERT INTO patent_count (protein_id, year, count) VALUES (%s, %s, %s)"
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%','.join([str(p) for p in params]))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
        if commit: self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_patent_count(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    return True

  def ins_hgram_cdf(self, init, commit=True):
    if 'protein_id' in init and 'type' in init and 'attr_count' in init and 'attr_cdf' in init:
      params = [init['protein_id'], init['type'], init['attr_count'], init['attr_cdf']]
    else:
      self.warning("Invalid parameters sent to ins_hgram_cdf(): ", init)
      return False
    sql = "INSERT INTO hgram_cdf (protein_id, type, attr_count, attr_cdf) VALUES (%s, %s, %s, %s)"
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%(", ".join([str(p) for p in params])))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
        if commit: self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_hgram_cdf(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    return True

  def ins_feature(self, init, commit=True):
    if 'protein_id' in init and 'type' in init:
      params = [init['protein_id'], init['type']]
    else:
      self.warning("Invalid parameters sent to ins_feature(): ", init)
      return False
    cols = ['protein_id', 'type']
    vals = ['%s','%s']
    for optcol in ['description', 'srcid', 'evidence', 'position', 'begin', 'end']:
      if optcol in init:
        cols.append(optcol)
        vals.append('%s')
        params.append(init[optcol])
    sql = "INSERT INTO feature (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%','.join([str(p) for p in params]))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
        if commit: self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_feature(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    return True

  def ins_pubmed(self, init, commit=True):
    if 'id' in init and 'title' in init:
      cols = ['id', 'title']
      vals = ['%s', '%s']
      params = [init['id'], init['title'] ]
    else:
      self.warning("Invalid parameters sent to ins_pubmed(): ", init)
      return False
    for optcol in ['journal', 'date', 'authors', 'abstract']:
      if optcol in init:
        cols.append(optcol)
        vals.append('%s')
        params.append(init[optcol])
    sql = "INSERT INTO pubmed (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    #self._logger.debug("SQLparams: %s"%','.join([str(p) for p in params]))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
        if commit: self._conn.commit()
      except mysql.Error, e:
        if 'Duplicate entry' in e[1] and "key 'PRIMARY'" in e[1]:
          pass
        else:
          self._conn.rollback()
          self._logger.error("MySQL Error in ins_pubmed(): %s"%str(e))
          self._logger.error("SQLpat: %s"%sql)
          #self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
          return False
    return True

  def ins_protein2pubmed(self, init, commit=True):
    if 'protein_id' in init and 'pubmed_id' in init:
      sql = "INSERT INTO protein2pubmed (protein_id, pubmed_id) VALUES (%s, %s)"
      params = [init['protein_id'], init['pubmed_id']]
    else:
      self.warning("Invalid parameters sent to ins_protein2pubmed(): ", init)
      return False
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%','.join([str(p) for p in params]))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
        if commit: self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_feature(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    return True

  def ins_compartment(self, init, commit=True):
    if 'ctype' not in init :
      self.warning("Invalid parameters sent to ins_compartment(): ", init)
      return False
    if 'protein_id' in init:
      cols = ['ctype', 'protein_id']
      vals = ['%s','%s']
      params = [init['ctype'], init['protein_id']]
    elif 'target_id' in init:
      cols = ['ctype', 'target_id']
      vals = ['%s','%s']
      params = [init['ctype'], init['target_id']]
    else:
      self.warning("Invalid parameters sent to ins_compartment(): ", init)
      return False
    for optcol in ['go_id', 'go_term', 'evidence', 'zscore', 'conf', 'url', 'reliability']:
      if optcol in init:
        cols.append(optcol)
        vals.append('%s')
        params.append(init[optcol])
    sql = "INSERT INTO compartment (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%", ".join([str(p) for p in params]))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
        if commit: self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_compartment(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    return True

  def ins_do(self, init, commit=True):
    if 'doid' in init and 'name' in init:
      cols = ['doid', 'name']
      vals = ['%s','%s']
      params = [init['doid'], init['name']]
    else:
      self.warning("Invalid parameters sent to ins_do(): ", init)
      return False
    for optcol in ['def']:
      if optcol in init:
        cols.append(optcol)
        vals.append('%s')
        params.append(init[optcol])
    sql = "INSERT INTO do (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%(", ".join([str(p) for p in params])))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_do(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    if 'parents' in init:
      for parent_id in init['parents']:
        sql = "INSERT INTO do_parent (doid, parent_id) VALUES (%s, %s)"
        params = [init['doid'], parent_id]
        self._logger.debug("SQLpat: %s"%sql)
        self._logger.debug("SQLparams: %s"%(", ".join([str(p) for p in params])))
        with closing(self._conn.cursor()) as curs:
          try:
            curs.execute(sql, params)
          except mysql.Error, e:
            self._conn.rollback()
            self._logger.error("MySQL Error inserting do_parent in ins_do(): %s"%str(e))
            self._logger.error("SQLpat: %s"%sql)
            self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
            return False
    if 'xrefs' in init:
      for xref in init['xrefs']:
        sql = "INSERT INTO do_xref (doid, db, value) VALUES (%s, %s, %s)"
        params = [init['doid'], xref['db'], xref['value']]
        self._logger.debug("SQLpat: %s"%sql)
        self._logger.debug("SQLparams: %s"%(", ".join([str(p) for p in params])))
        with closing(self._conn.cursor()) as curs:
          try:
            curs.execute(sql, params)
          except mysql.Error, e:
            if 'Duplicate entry' in e[1] and "for key 'PRIMARY'" in e[1]:
              pass
            else:
              self._conn.rollback()
              self._logger.error("MySQL Error inserting do_xref in ins_do(): %s"%str(e))
              self._logger.error("SQLpat: %s"%sql)
              self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
              return False
    if commit:
      try:
        self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL commit error in ins_do(): %s"%str(e))
        return False
    
    return True

  def ins_mpo(self, init, commit=True):
    if 'mpid' in init and 'name' in init:
      cols = ['mpid', 'name']
      vals = ['%s','%s']
      params = [init['mpid'], init['name']]
    else:
      self.warning("Invalid parameters sent to ins_mpo(): ", init)
      return False
    for optcol in ['def', 'parent_id']:
      if optcol in init:
        cols.append(optcol)
        vals.append('%s')
        if optcol == 'def':
          init[optcol] = init[optcol].encode('ascii', 'ignore').decode('ascii')
        params.append(init[optcol])
    sql = "INSERT INTO mpo (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    #self._logger.debug("SQLparams: %s"%(", ".join([str(p) for p in params])))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_mpo(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        #self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        self._logger.error("SQLparams: mpid %s"%sinit['mpid'])
        return False
    if commit:
      try:
        self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL commit error in ins_mpo(): %s"%str(e))
        return False
    
    return True

  def ins_rdo(self, init, commit=True):
    if 'doid' in init and 'name' in init:
      cols = ['doid', 'name']
      vals = ['%s','%s']
      params = [init['doid'], init['name']]
    else:
      self.warning("Invalid parameters sent to ins_rdo(): ", init)
      return False
    for optcol in ['def']:
      if optcol in init:
        cols.append(optcol)
        vals.append('%s')
        params.append(init[optcol])
    sql = "INSERT INTO rdo (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%(", ".join([str(p) for p in params])))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_rdo(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    # if 'parents' in init:
    #   for parent_id in init['parents']:
    #     sql = "INSERT INTO do_parent (doid, parent_id) VALUES (%s, %s)"
    #     params = [init['doid'], parent_id]
    #     self._logger.debug("SQLpat: %s"%sql)
    #     self._logger.debug("SQLparams: %s"%(", ".join([str(p) for p in params])))
    #     with closing(self._conn.cursor()) as curs:
    #       try:
    #         curs.execute(sql, params)
    #       except mysql.Error, e:
    #         self._conn.rollback()
    #         self._logger.error("MySQL Error inserting do_parent in ins_rdo(): %s"%str(e))
    #         self._logger.error("SQLpat: %s"%sql)
    #         self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
    #         return False
    if 'xrefs' in init:
      for xref in init['xrefs']:
        sql = "INSERT INTO rdo_xref (doid, db, value) VALUES (%s, %s, %s)"
        params = [init['doid'], xref['db'], xref['value']]
        self._logger.debug("SQLpat: %s"%sql)
        self._logger.debug("SQLparams: %s"%(", ".join([str(p) for p in params])))
        with closing(self._conn.cursor()) as curs:
          try:
            curs.execute(sql, params)
          except mysql.Error, e:
            if 'Duplicate entry' in e[1] and "for key 'PRIMARY'" in e[1]:
              pass
            else:
              self._conn.rollback()
              self._logger.error("MySQL Error inserting rdo_xref in ins_rdo(): %s"%str(e))
              self._logger.error("SQLpat: %s"%sql)
              self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
              return False
    if commit:
      try:
        self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL commit error in ins_do(): %s"%str(e))
        return False
    
    return True

  def ins_uberon(self, init, commit=True):
    if 'uid' in init and 'name' in init:
      cols = ['uid', 'name']
      vals = ['%s','%s']
      params = [init['uid'], init['name']]
    else:
      self.warning("Invalid parameters sent to ins_uberon(): ", init)
      return False
    for optcol in ['def', 'comment']:
      if optcol in init:
        cols.append(optcol)
        vals.append('%s')
        params.append(init[optcol])
    sql = "INSERT INTO uberon (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%(", ".join([str(p) for p in params])))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_uberon(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    if 'parents' in init:
      for parent_id in init['parents']:
        sql = "INSERT INTO uberon_parent (uid, parent_id) VALUES (%s, %s)"
        params = [init['uid'], parent_id]
        self._logger.debug("SQLpat: %s"%sql)
        self._logger.debug("SQLparams: %s"%(", ".join([str(p) for p in params])))
        with closing(self._conn.cursor()) as curs:
          try:
            curs.execute(sql, params)
          except mysql.Error, e:
            self._conn.rollback()
            self._logger.error("MySQL Error inserting uberon_parent in ins_uberon(): %s"%str(e))
            self._logger.error("SQLpat: %s"%sql)
            self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
            return False
    if 'xrefs' in init:
      for xref in init['xrefs']:
        sql = "INSERT INTO uberon_xref (uid, db, value) VALUES (%s, %s, %s)"
        params = [init['uid'], xref['db'], xref['value']]
        self._logger.debug("SQLpat: %s"%sql)
        self._logger.debug("SQLparams: %s"%(", ".join([str(p) for p in params])))
        with closing(self._conn.cursor()) as curs:
          try:
            curs.execute(sql, params)
          except mysql.Error, e:
            if 'Duplicate entry' in e[1] and "for key 'PRIMARY'" in e[1]:
              pass
            else:
              self._conn.rollback()
              self._logger.error("MySQL Error inserting uberon_xref in ins_uberon(): %s"%str(e))
              self._logger.error("SQLpat: %s"%sql)
              self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
              return False
    if commit:
      try:
        self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL commit error in ins_uberon(): %s"%str(e))
        return False
    
    return True

  def ins_techdev_contact(self, init, commit=True):
    if 'id' in init and 'contact_name' in init and 'contact_email' in init and 'pi' in init:
      params = [init['id'], init['contact_name'], init['contact_email'], init['pi']]
    else:
      self.warning("Invalid parameters sent to ins_techdev_contact(): ", init)
      return False
    cols = ['id', 'contact_name', 'contact_email', 'pi']
    vals = ['%s','%s', '%s', '%s']
    for optcol in ['grant_number', 'date']:
      if optcol in init:
        cols.append(optcol)
        vals.append('%s')
        params.append(init[optcol])
    sql = "INSERT INTO techdev_contact (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%','.join([str(p) for p in params]))
    #self._logger.debug("Cols: %d, Vals: %d, Params: %d"%(len(cols), len(vals), len(params)))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, tuple(params))
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_techdev_contact(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    if commit:
      try:
        self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL commit error in ins_techdev_contact(): %s"%str(e))
        return False
    
    return init['id']

  def ins_techdev_info(self, init, commit=True):
    if 'contact_id' in init and 'protein_id' in init and 'comment' in init:
      params = [init['contact_id'], init['protein_id'], init['comment']]
    else:
      self.warning("Invalid parameters sent to ins_techdev_info(): ", init)
      return False
    cols = ['contact_id', 'protein_id', 'comment']
    vals = ['%s','%s', '%s']
    for optcol in ['publication_pcmid', 'publication_pmid', 'resource_url', 'data_url']:
      if optcol in init:
        cols.append(optcol)
        vals.append('%s')
        params.append(init[optcol])
    sql = "INSERT INTO techdev_info (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%','.join([str(p) for p in params]))
    #self._logger.debug("Cols: %d, Vals: %d, Params: %d"%(len(cols), len(vals), len(params)))
    tc_id = None
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, tuple(params))
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_techdev_info(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    if commit:
      try:
        self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL commit error in ins_techdev_info(): %s"%str(e))
        return False
    
    return True

  def ins_kegg_distance(self, init, commit=True):
    if 'pid1' in init and 'pid2' in init and 'distance' in init:
      params = [init['pid1'], init['pid2'], init['distance']]
      cols = ['pid1', 'pid2', 'distance']
      vals = ['%s','%s','%s']
    else:
      self.warning("Invalid parameters sent to ins_kegg_distance(): ", init)
      return False
    # for optcol in ['protein1_str', 'protein2_str']:
    #   if optcol in init:
    #     cols.append(optcol)
    #     vals.append('%s')
    #     params.append(init[optcol])
    sql = "INSERT INTO kegg_distance (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%','.join([str(p) for p in params]))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, tuple(params))
        if commit: self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_kegg_distance(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    return True

  def ins_kegg_nearest_tclin(self, init, commit=True):
    if 'protein_id' in init and 'tclin_id' in init and 'direction' in init and 'distance' in init:
      cols = ['protein_id', 'tclin_id', 'direction', 'distance']
      vals = ['%s','%s','%s','%s']
      params = [init['protein_id'], init['tclin_id'], init['direction'], init['distance']]
    else:
      self.warning("Invalid parameters sent to ins_kegg_nearest_tclin(): ", init)
      return False
    sql = "INSERT INTO kegg_nearest_tclin (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%(", ".join([str(p) for p in params])))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_kegg_nearest_tclin(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    if commit:
      try:
        self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL commit error in ins_do(): %s"%str(e))
        return False
    
    return True

  def ins_locsig(self, init, commit=True):
    if 'protein_id' in init and 'location' in init and 'signal' in init:
      cols = ['protein_id', 'location', '`signal`'] # NB. signal needs backticks in MySQL
      vals = ['%s','%s','%s']
      params = [init['protein_id'], init['location'], init['signal']]
    else:
      self.warning("Invalid parameters sent to ins_locsig(): ", init)
      return False
    for optcol in ['pmids']:
      if optcol in init:
        cols.append(optcol)
        vals.append('%s')
        params.append(init[optcol])
    sql = "INSERT INTO locsig (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%(", ".join([str(p) for p in params])))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_locsig(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    if commit:
      try:
        self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL commit error in ins_locsig(): %s"%str(e))
        return False
    
    return True

  def ins_ortholog(self, init, commit=True):
    if 'protein_id' in init and 'taxid' in init and 'species' in init and 'symbol' in init and 'name' in init and 'sources' in init:
      cols = ['protein_id', 'taxid', 'species', 'symbol', 'name', 'sources']
      vals = ['%s','%s','%s', '%s','%s', '%s']
      params = [init['protein_id'], init['taxid'], init['species'], init['symbol'], init['name'], init['sources']]
    else:
      self.warning("Invalid parameters sent to ins_ortholog(): ", init)
      return False
    for optcol in ['db_id', 'geneid', 'mod_url']:
      if optcol in init:
        cols.append(optcol)
        vals.append('%s')
        params.append(init[optcol])
    sql = "INSERT INTO ortholog (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%(", ".join([str(p) for p in params])))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_ortholog(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    if commit:
      try:
        self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL commit error in ins_ortholog(): %s"%str(e))
        return False
    
    return True

  def ins_homologene(self, init, commit=True):
    if 'groupid' in init and 'taxid' in init:
      cols = ['groupid', 'taxid']
      params = [init['groupid'], init['taxid']]
    else:
      self.warning("Invalid parameters sent to ins_homologene(): ", init)
      return False
    if 'protein_id' in init:
      cols.insert(0, 'protein_id')
      vals = ['%s','%s','%s']
      params.insert(0, init['protein_id'])
    elif 'nhprotein_id' in init:
      cols.insert(0, 'nhprotein_id')
      vals = ['%s','%s','%s']
      params.insert(0, init['nhprotein_id'])
    else:
      self.warning("Invalid parameters sent to ins_homologene(): ", init)
      return False
    sql = "INSERT INTO homologene (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%(", ".join([str(p) for p in params])))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, tuple(params))
        if commit: self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_homologene(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    return True

  def ins_omim(self, init, commit=True):
    if 'mim' in init and 'title' in init:
      cols = ['mim', 'title']
      vals = ['%s','%s']
      params = [init['mim'], init['title']]
    else:
      self.warning("Invalid parameters sent to ins_omim(): ", init)
      return False
    sql = "INSERT INTO omim (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%(", ".join([str(p) for p in params])))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_omim(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    if commit:
      try:
        self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL commit error in ins_omim(): %s"%str(e))
        return False
    return True

  def ins_omim_ps(self, init, commit=True):
    if 'omim_ps_id' in init and 'title' in init:
      cols = ['omim_ps_id', 'title']
      vals = ['%s','%s']
      params = [init['omim_ps_id'], init['title']]
    else:
      self.warning("Invalid parameters sent to ins_omim_ps(): ", init)
      return False
    if 'mim' in init:
        cols.append('mim')
        vals.append('%s')
        params.append(init['mim'])
    sql = "INSERT INTO omim_ps (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%(", ".join([str(p) for p in params])))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_omim_ps(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    if commit:
      try:
        self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL commit error in ins_omim_ps(): %s"%str(e))
        return False
    return True

  def ins_rat_qtl(self, init, commit=True):
    if 'nhprotein_id' in init and 'rgdid' in init and 'qtl_rgdid' in init and 'qtl_symbol' in init and 'qtl_name' in init:
      cols = ['nhprotein_id', 'rgdid', 'qtl_rgdid', 'qtl_symbol', 'qtl_name']
      vals = ['%s','%s','%s', '%s','%s']
      params = [init['nhprotein_id'], init['rgdid'], init['qtl_rgdid'], init['qtl_symbol'], init['qtl_name']]

    else:
      self.warning("Invalid parameters sent to ins_rat_qtl(): ", init)
      return False
    for optcol in ['trait_name', 'measurement_type', 'associated_disease', 'phenotype', 'p_value', 'lod']:
      if optcol in init:
        cols.append(optcol)
        vals.append('%s')
        params.append(init[optcol])
    sql = "INSERT INTO rat_qtl (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%','.join([str(p) for p in params]))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_rat_qtl(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    if commit:
      try:
        self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL commit error in ins_rat_qtl(): %s"%str(e))
        return False
    return True

  def ins_rat_term(self, init, commit=True):
    if 'rgdid' in init and 'term_id' in init:
      cols = ['rgdid', 'term_id']
      vals = ['%s','%s']
      params = [init['rgdid'], init['term_id']]
    else:
      self.warning("Invalid parameters sent to ins_rat_term(): ", init)
      return False
    for optcol in ['obj_symbol', 'term_name', 'qualifier', 'evidence', 'ontology']:
      if optcol in init:
        cols.append(optcol)
        vals.append('%s')
        params.append(init[optcol])
    sql = "INSERT INTO rat_term (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%','.join([str(p) for p in params]))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_rat_term(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    if commit:
      try:
        self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL commit error in ins_rat_term(): %s"%str(e))
        return False
    return True

  def ins_lincs(self, init, commit=True):
    if 'protein_id' in init and 'cellid' in init and 'zscore' in init and 'pert_dcid' in init and 'pert_smiles' in init:
      cols = ['protein_id', 'cellid', 'zscore', 'pert_dcid', 'pert_smiles']
      vals = ['%s','%s', '%s','%s','%s']
      params = [init['protein_id'], init['cellid'], init['zscore'], init['pert_dcid'], init['pert_smiles']]
    else:
      self.warning("Invalid parameters sent to ins_lincs(): ", init)
      return False
    for optcol in ['pert_canonical_smiles']:
      if optcol in init:
        cols.append(optcol)
        vals.append('%s')
        params.append(init[optcol])
    sql = "INSERT INTO lincs (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%','.join([str(p) for p in params]))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_lincs(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    if commit:
      try:
        self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL commit error in ins_lincs(): %s"%str(e))
        return False
    return True

  def ins_drgc_resource(self, init, commit=True):
    if 'target_id' in init and 'resource_type' in init and 'json' in init:
      cols = ['target_id', 'resource_type', 'json']
      vals = ['%s','%s','%s']
      params = [init['target_id'], init['resource_type'], init['json']]
    else:
      self.warning("Invalid parameters sent to ins_drgc_resource(): ", init)
      return False
    sql = "INSERT INTO drgc_resource (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%(", ".join([str(p) for p in params])))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, tuple(params))
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_drgc_resource(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    if commit:
      try:
        self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL commit error in ins_drgc_resource(): %s"%str(e))
        return False
    
    return True

  def ins_clinvar_phenotype(self, init):
    if 'name' in init:
      cols = ['name']
      vals = ['%s']
      params = [init['name']]
    else:
      self.warning("Invalid parameters sent to ins_clinvar_phenotype(): ", init)
      return False
    sql = "INSERT INTO clinvar_phenotype (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%(", ".join([str(p) for p in params])))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, tuple(params))
        cvpt_id = curs.lastrowid
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_clinvar_phenotype: %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    try:
      self._conn.commit()
    except mysql.Error, e:
      self._conn.rollback()
      self._logger.error("MySQL commit error in ins_clinvar_phenotype(): %s"%str(e))
      return False
    
    return cvpt_id

  def ins_clinvar_phenotype_xref(self, init):
    if 'clinvar_phenotype_id' in init and 'source' in init and 'value' in init:
      cols = ['clinvar_phenotype_id', 'source', 'value']
      vals = ['%s', '%s', '%s']
      params = [init['clinvar_phenotype_id'], init['source'], init['value']]
    else:
      self.warning("Invalid parameters sent to ins_clinvar_phenotype_xref(): ", init)
      return False
    sql = "INSERT INTO clinvar_phenotype_xref (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%(", ".join([str(p) for p in params])))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, tuple(params))
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_clinvar_phenotype_xref: %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    try:
      self._conn.commit()
    except mysql.Error, e:
      self._conn.rollback()
      self._logger.error("MySQL commit error in ins_clinvar_phenotype_xref(): %s"%str(e))
      return False
    
    return True

  def ins_clinvar(self, init):
    if 'protein_id' in init and 'clinvar_phenotype_id' in init and 'alleleid' in init and 'type' in init and 'name' in init and 'review_status' in init:
      cols = ['protein_id', 'clinvar_phenotype_id', 'alleleid', 'type', 'name', 'review_status']
      vals = ['%s','%s','%s','%s','%s','%s']
      params = [init['protein_id'], init['clinvar_phenotype_id'], init['alleleid'], init['type'],init['name'], init['review_status']]
    else:
      self.warning("Invalid parameters sent to ins_clinvar(): ", init)
      return False
    for optcol in ['clinical_significance', 'clin_sig_simple', 'last_evaluated', 'dbsnp_rs', 'dbvarid', 'origin', 'origin_simple', 'assembly', 'chr', 'chr_acc', 'start', 'stop', 'number_submitters', 'tested_in_gtr', 'submitter_categories']:
      if optcol in init:
        cols.append(optcol)
        vals.append('%s')
        params.append(init[optcol])
    sql = "INSERT INTO clinvar (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%','.join([str(p) for p in params]))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_clinvar(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    try:
      self._conn.commit()
    except mysql.Error, e:
      self._conn.rollback()
      self._logger.error("MySQL commit error in ins_clinvar(): %s"%str(e))
      return False
    return True

  def ins_idg_evol(self, init):
    if 'tcrd_ver' in init and 'tcrd_dbid' in init and 'name' in init and 'description' in init and 'uniprot' in init and 'tdl' in init:
      cols = ['tcrd_ver', 'tcrd_dbid', 'name', 'description', 'uniprot', 'tdl']
      vals = ['%s','%s','%s','%s','%s','%s']
      params = [init['tcrd_ver'], init['tcrd_dbid'], init['name'], init['description'],init['uniprot'], init['tdl']]
    else:
      self.warning("Invalid parameters sent to ins_idg_evol(): ", init)
      return False
    for optcol in ['sym', 'geneid', 'fam']:
      if optcol in init:
        cols.append(optcol)
        vals.append('%s')
        params.append(init[optcol])
    sql = "INSERT INTO idg_evol (%s) VALUES (%s)" % (','.join(cols), ','.join(vals))
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%','.join([str(p) for p in params]))
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
      except mysql.Error, e:
        self._conn.rollback()
        self._logger.error("MySQL Error in ins_idg_evol(): %s"%str(e))
        self._logger.error("SQLpat: %s"%sql)
        self._logger.error("SQLparams: %s"%','.join([str(p) for p in params]))
        return False
    try:
      self._conn.commit()
    except mysql.Error, e:
      self._conn.rollback()
      self._logger.error("MySQL commit error in ins_idg_evol(): %s"%str(e))
      return False
    return True
  
  #
  # Read Methods
  #
  def get_info_types(self):
    return self._info_types

  def get_xref_types(self):
    return self._xref_types

  def get_expression_types(self):
    return self._expression_types

  def get_phenotype_types(self):
    return self._phenotype_types

  def get_gene_attribute_types(self):
    # unlke other get_*_types() methods, this returns a dict of name => id
    self._cache_gene_attribute_types()
    return self._gene_attribute_types
  
  def get_count_typecount(self, table):
    tab2col = {'compartment': 'ctype', 'expression': 'etype', 'disease': 'dtype', 'expression': 'etype', 'phenotype': 'ptype', 'ppi': 'ppi_type', 'tdl_info': 'itype', 'pathway': 'pwtype'}
    with closing(self._conn.cursor()) as curs:
      curs.execute("SELECT count(*) FROM %s" % table)
      ct = curs.fetchone()[0]
      curs.execute("SELECT count(distinct %s) FROM %s" % (tab2col[table], table))
      type_ct = curs.fetchone()[0]
    return (ct, type_ct)

  def get_tinx_pmids(self):
    pmids = []
    with closing(self._conn.cursor()) as curs:
      curs.execute("SELECT DISTINCT pmid FROM tinx_articlerank")
      for pmid in curs:
        pmids.append(pmid[0])
    return pmids

  def get_pmids(self):
    pmids = []
    with closing(self._conn.cursor()) as curs:
      curs.execute("SELECT id FROM pubmed")
      for pmid in curs:
        pmids.append(pmid[0])
    return pmids

  def get_expression_count(self, etype=None, oid_flag=False):
    '''
    Function  : Function to get TCRD expression count
    Arguments : Optional flag to require an oid
    Returns   : Integer
    Example   : 
    Scope     : Public
    '''
    sql = "SELECT count(*) FROM expression"
    if etype:
      if oid_flag:
        sql += " WHERE etype = '%s' AND oid IS NOT NULL"
      else:
        sql += " WHERE etype = '%s'" % etype
    elif oid_flag:
      sql += " WHERE oid IS NOT NULL"
    with closing(self._conn.cursor()) as curs:
      curs.execute(sql)
      ct = curs.fetchone()[0]
    return ct

  def get_expressions(self, etype=None, oid_flag=False):
    '''
    Function  : Generator function to get TCRD expressions
    Arguments : Optional flag to require an oid
    Returns   : One expression dict at a time
    Example   : for exp in dba.get_expressions():
                  do something with exp
    Scope     : Public
    '''
    sql = 'SELECT * FROM expression'
    if etype:
      if oid_flag:
        sql += " WHERE etype = '%s' AND oid IS NOT NULL"
      else:
        sql += " WHERE etype = '%s'" % etype
    elif oid_flag:
      sql += " WHERE oid IS NOT NULL"
    with closing(self._conn.cursor(dictionary=True)) as curs:
      curs.execute(sql)
      for exp in curs:
        yield exp

  def get_beans(self):
    beans = {}
    with closing(self._conn.cursor(dictionary=True)) as curs:
      beans['Target Count'] = self.get_target_count()
      curs.execute("SELECT COUNT(*) AS CT FROM protein")
      beans['Protein Count'] = curs.fetchone()['CT']
      curs.execute("SELECT COUNT(*) AS CT FROM protein WHERE sym IS NOT NULL")
      beans['HGNC Symbols'] = curs.fetchone()['CT']
      curs.execute("SELECT COUNT(*) AS CT FROM protein WHERE uniprot IS NOT NULL")
      beans['UniProt Count'] = curs.fetchone()['CT']
      curs.execute("SELECT COUNT(*) AS CT FROM protein WHERE geneid IS NOT NULL")
      beans['NCBI GENEID COUNT'] = curs.fetchone()['CT']
      curs.execute("SELECT COUNT(*) AS CT FROM protein WHERE chr IS NOT NULL")
      beans['Chromosomal Location Count'] = curs.fetchone()['CT']
      curs.execute("SELECT COUNT(*) AS CT FROM protein WHERE dtoid IS NOT NULL")
      beans['DTO ID Count'] = curs.fetchone()['CT']
      curs.execute("SELECT COUNT(*) AS CT FROM dto_classification")
      beans['DTO Classification Count'] = curs.fetchone()['CT']
      curs.execute("SELECT COUNT(*) AS CT FROM p2pc")
      beans['PANTHER Classification Count'] = curs.fetchone()['CT']
      curs.execute("SELECT COUNT(*) AS CT FROM mlp_assay_info")
      beans['MLP Assay Count'] = curs.fetchone()['CT']
      curs.execute("SELECT COUNT(*) AS CT FROM generif")
      beans['GeneRIF Count'] = curs.fetchone()['CT']

      curs.execute("SELECT it.name, it.description, count(*) AS CT FROM info_type it, tdl_info ti WHERE ti.itype = it.name GROUP BY it.name, it.description")
      for d in curs:
        # d['type'] = d['name']
        # del(d['name'])
        # beans['tdl_infos'].append(d)
        key = d['name'] + 's'
        beans[key] = d['CT']

      curs.execute("SELECT type, count(*) AS CT FROM alias GROUP BY type ORDER BY CT DESC")
      for d in curs:
        if d['type'] == 'uniprot':
          beans['UniProt Aliases'] = d['CT']
        elif d['type'] == 'symbol':
          beans['HGNC Aliases'] = d['CT']

      curs.execute("SELECT COUNT(*) AS CT FROM xref")
      beans['Cross Reference Total Count'] = curs.fetchone()['CT']
      curs.execute("SELECT COUNT(distinct xtype) AS CT FROM xref")
      beans['Cross Reference Types'] = curs.fetchone()['CT']
      curs.execute("SELECT xtype, count(*) AS CT FROM xref GROUP BY xtype ORDER BY CT DESC")
      beans['Cross References'] = []
      beans['Protein Domains'] = []
      for d in curs:
        d['type'] = d['xtype']
        if d['xtype'] in ['InterPro', 'Pfam', 'PROSITE']:
          #beans['domains'][d['xtype']] = d['CT']
          del(d['xtype'])
          beans['Protein Domains'].append(d)
        else:
          del(d['xtype'])
          beans['Cross References'].append(d)

      curs.execute("SELECT COUNT(*) AS CT FROM goa WHERE go_term LIKE 'C:%'")
      beans['GO Cellular Location Annotations'] = curs.fetchone()['CT']
      curs.execute("SELECT COUNT(*) AS CT FROM goa WHERE go_term LIKE 'F:%'")
      beans['GO Molecular Function Annotations'] = curs.fetchone()['CT']
      curs.execute("SELECT COUNT(*) AS CT FROM goa WHERE go_term LIKE 'P:%'")
      beans['GO Biological Process Annotations'] = curs.fetchone()['CT']

      curs.execute("SELECT COUNT(*) AS CT FROM drug_activity")
      beans['Drug Example Activities'] = curs.fetchone()['CT']
      curs.execute("SELECT COUNT(*) AS CT FROM cmpd_activity")
      beans['Cmpd Example Activities'] = curs.fetchone()['CT']

      curs.execute("SELECT pwtype, count(*) AS CT FROM pathway GROUP BY pwtype ORDER BY CT DESC")
      beans['Pathway Links'] = []
      for d in curs:
        beans['Pathway Links'].append(d)

      curs.execute("SELECT dtype, count(*) AS CT FROM disease GROUP BY dtype ORDER BY CT DESC")
      beans['Disease Associations'] = []
      for d in curs:
        d['type'] = d['dtype']
        del(d['dtype'])
        beans['Disease Associations'].append(d)

      curs.execute("SELECT etype, count(*) AS CT FROM expression GROUP BY etype ORDER BY CT DESC")
      beans['Expression Values'] = []
      for d in curs:
        d['type'] = d['etype']
        del(d['etype'])
        beans['Expression Values'].append(d)

      curs.execute("SELECT ptype, count(*) AS CT FROM phenotype GROUP BY ptype ORDER BY CT DESC")
      beans['Phenotypes'] = []
      for d in curs:
        d['type'] = d['ptype']
        del(d['ptype'])
        beans['Phenotypes'].append(d)

      curs.execute("SELECT type, count(*) AS CT FROM gene_attribute GROUP BY type ORDER BY CT DESC")
      beans["Ma'ayan Lab Gene Attributes"] = []
      for d in curs:
        beans["Ma'ayan Lab Gene Attributes"].append(d)

    return beans

  def get_cmpd_activities(self, catype=None):
    cmpd_activities = []
    sql = "SELECT * FROM cmpd_activity"
    if catype:
      sql += " WHERE catype = '%s'" % catype
    with closing(self._conn.cursor(dictionary=True)) as curs:
      curs.execute(sql)
      for d in curs:
        cmpd_activities.append(d)
    return cmpd_activities

  def get_drug_activities(self):
    drug_activities = []
    with closing(self._conn.cursor(dictionary=True)) as curs:
      curs.execute("SELECT * FROM drug_activity")
      for d in curs:
        drug_activities.append(d)
    return drug_activities

  def get_techdev_info(self, contact_id):
    tdi = []
    with closing(self._conn.cursor(dictionary=True)) as curs:
      curs.execute("SELECT p.sym, p.description, p.uniprot, t.tdl, t.fam, tdi.comment, tdi.resource_url, tdi.data_url FROM target t, t2tc, protein p, techdev_info tdi WHERE t.id = t2tc.target_id AND t2tc.protein_id = p.id AND p.id = tdi.protein_id AND tdi.contact_id = %s", (contact_id))
      for d in curs:
        tdi.append(d)
    return tdi

  def get_generifs(self):
    generifs = []
    with closing(self._conn.cursor(dictionary=True)) as curs:
      curs.execute("SELECT * FROM generif")
      for d in curs:
        generifs.append(d)
    return generifs

  def get_pubmed(self, pmid):
    with closing(self._conn.cursor(dictionary=True)) as curs:
      curs.execute("SELECT * FROM pubmed WHERE id = %s", (pmid,))
      pm = curs.fetchone()
      if pm:
        return pm
      else:
        return None

  def get_uberon_id(self, q):
    if 'oid' in q:
      (db, val) = q['oid'].split(':')
      sql = "SELECT uid FROM uberon_xref WHERE db = %s AND value = %s"
      params = (db, val)
    elif 'name' in q:
      name = q['name'].lower()
      sql = "SELECT uid FROM uberon WHERE LOWER(name) = %s"
      params = (name,)
    else:
      self.warning("Invalid query parameters sent to get_uberon_id(): ", q)
      return False
    with closing(self._conn.cursor()) as curs:
      curs.execute(sql, params)
      row = curs.fetchone()
    if row:
      return row[0]
    else:
      return None

  def get_target(self, id, include_annotations=False, get_ga_counts=False):
    '''
    Function  : Get a target by id. To get a target by any other attribute, see find_targets().
    Arguments : An integer and an optional boolean.
    Returns   : Dictionary containing target data.
    Example   : target = dba->get_target(42, include_annotations=True) ;
    Scope     : Public
    Comments  : By default, this returns target and target component (ie. protein and
                nucleic_acid) data only.
                To get all associated annotations, call with include_annotations=True
    '''
    with closing(self._conn.cursor(dictionary=True)) as curs:
      self._logger.debug("ID: %s" % id)
      curs.execute("SELECT * FROM target WHERE id = %s", (id,))
      t = curs.fetchone()
      if not t: return False
      t['tdl_updates'] = []
      curs.execute("SELECT * FROM tdl_update_log WHERE target_id = %s", (id,))
      for u in curs:
        u['datetime'] = str(u['datetime'])
        t['tdl_updates'].append(u)
      if not t['tdl_updates']: del(t['tdl_updates'])
      if include_annotations:
        # tdl_info
        t['tdl_infos'] = {}
        curs.execute("SELECT * FROM tdl_info WHERE target_id = %s", (id,))
        for ti in curs:
          self._logger.debug("  tdl_info: %s" % str(ti))
          itype = ti['itype']
          val_col = self._info_types[itype]
          t['tdl_infos'][itype] = {'id': ti['id'], 'value': ti[val_col]}
        if not t['tdl_infos']: del(t['tdl_infos'])
        # xrefs
        t['xrefs'] = {}
        for xt in self._xref_types:
          l = []
          curs.execute("SELECT * FROM xref WHERE target_id = %s AND xtype = %s", (id, xt))
          for x in curs:
            init = {'id': x['id'], 'value': x['value']}
            if x['xtra']:
              init['xtra'] = x['xtra']
            l.append(init)
          if l:
            t['xrefs'][xt] = l
        if not t['xrefs']: del(t['xrefs'])
        # Drug Activity
        t['drug_activities'] = []
        curs.execute("SELECT * FROM drug_activity WHERE target_id = %s", (id,))
        for da in curs:
          t['drug_activities'].append(da)
        if not t['drug_activities']: del(t['drug_activities'])
        # Cmpd Activity
        t['cmpd_activities'] = []
        curs.execute("SELECT * FROM cmpd_activity WHERE target_id = %s", (id,))
        for ca in curs:
          t['cmpd_activities'].append(ca)
        if not t['cmpd_activities']: del(t['cmpd_activities'])
      # Components
      t['components'] = {}
      t['components']['protein'] = []
      curs.execute("SELECT * FROM t2tc WHERE target_id = %s", (id,))
      for tc in curs:
        if tc['protein_id']:
          p = self.get_protein(tc['protein_id'], include_annotations, get_ga_counts)
          t['components']['protein'].append(p)
        else:
          # for possible future targets with Eg. nucleic acid components
          pass
      return t

  def get_protein(self, id, include_annotations=False, get_ga_counts=False):
    '''
    Function  : Get a protein by id.
    Arguments : An integer and an optional boolean.
    Returns   : Dictionary containing protein data.
    Example   : protein = dba->get_protein(42, include_annotations=True) ;
    Scope     : Public
    Comments  : By default, this returns protein data only. To get all
                associated annotations, call with include_annotations=True
    '''
    with closing(self._conn.cursor(dictionary=True)) as curs:
      curs.execute("SELECT * FROM protein WHERE id = %s", (id,))
      p = curs.fetchone()
      if not p: return False
      if include_annotations:
        # aliases
        p['aliases'] = []
        curs.execute("SELECT * FROM alias WHERE protein_id = %s", (id,))
        for a in curs:
          p['aliases'].append(a)
        if not p['aliases']: del(p['aliases'])
        # tdl_info
        p['tdl_infos'] = {}
        curs.execute("SELECT * FROM tdl_info WHERE protein_id = %s", (id,))
        decs = []
        for ti in curs:
          itype = ti['itype']
          val_col = self._info_types[itype]
          if itype == 'Drugable Epigenome Class':
            decs.append( {'id': ti['id'], 'value': str(ti[val_col])} )
          else:
            p['tdl_infos'][itype] = {'id': ti['id'], 'value': str(ti[val_col])}
        if decs:
          p['tdl_infos']['Drugable Epigenome Class'] = decs
        # xrefs
        p['xrefs'] = {}
        for xt in self._xref_types:
          l = []
          curs.execute("SELECT * FROM xref WHERE protein_id = %s AND xtype = %s", (id, xt))
          for x in curs:
            init = {'id': x['id'], 'value': x['value']}
            if x['xtra']:
              init['xtra'] = x['xtra']
            l.append(init)
          if l:
            p['xrefs'][xt] = l
        # generifs
        p['generifs'] = []
        curs.execute("SELECT * FROM generif WHERE protein_id = %s", (id,))
        for gr in curs:
          p['generifs'].append({'id': gr['id'], 'pubmed_ids': gr['pubmed_ids'], 'text': gr['text']})
        if not p['generifs']: del(p['generifs'])
        # goas
        p['goas'] = []
        curs.execute("SELECT * FROM goa WHERE protein_id = %s", (id,))
        for g in curs:
          p['goas'].append(g)
        if not p['goas']: del(p['goas'])
        # pmscores
        p['pmscores'] = []
        curs.execute("SELECT * FROM pmscore WHERE protein_id = %s", (id,))
        for pms in curs:
          p['pmscores'].append(pms)
        if not p['pmscores']: del(p['pmscores'])
        # phenotypes
        p['phenotypes'] = []
        curs.execute("SELECT * FROM phenotype WHERE protein_id = %s", (id,))
        for pt in curs:
          p['phenotypes'].append(pt)
        if not p['phenotypes']: del(p['phenotypes'])
        # GWAS
        p['gwases'] = []
        curs.execute("SELECT * FROM gwas WHERE protein_id = %s", (id,))
        for gw in curs:
          p['gwases'].append(gw)
        if not p['gwases']: del(p['gwases'])
        # IMPC phenotypes (via Mouse ortholog)
        p['impcs'] = []
        curs.execute("SELECT DISTINCT pt.term_id, pt.term_name, pt.p_value FROM ortholog o, nhprotein nhp, phenotype pt WHERE o.symbol = nhp.sym AND o.species = 'Mouse' AND nhp.species = 'Mus musculus' AND nhp.id = pt.nhprotein_id AND o.protein_id = %s", (id,))
        for pt in curs:
          p['impcs'].append(pt)
        if not p['impcs']: del(p['impcs'])
        # RGD QTLs (via Rat ortholog)
        # TBD
        # diseases
        p['diseases'] = []
        bad_diseases = ['Disease', 'Disease by infectious agent', 'Bacterial infectious disease', 'Fungal infectious disease', 'Parasitic infectious disease', 'Viral infectious disease', 'Disease of anatomical entity', 'Cardiovascular system disease', 'Endocrine system disease', 'Gastrointestinal system disease', 'Immune system disease', 'Integumentary system disease', 'Musculoskeletal system disease', 'Nervous system disease', 'Reproductive system disease', 'Respiratory system disease', 'Thoracic disease', 'Urinary system disease', 'Disease of cellular proliferation', 'Benign neoplasm', 'Cancer', 'Pre-malignant neoplasm', 'Disease of mental health', 'Cognitive disorder', 'Developmental disorder of mental health', 'Dissociative disorder', 'Factitious disorder', 'Gender identity disorder', 'Impulse control disorder', 'Personality disorder', 'Sexual disorder', 'Sleep disorder', 'Somatoform disorder', 'Substance-related disorder', 'Disease of metabolism', 'Acquired metabolic disease', 'Inherited metabolic disorder', 'Genetic disease', 'Physical disorder', 'Syndrome']
        curs.execute("SELECT * FROM disease WHERE protein_id = %s ORDER BY zscore DESC", (id,))
        for d in curs:
          #if d['name'] not in bad_diseases:
          p['diseases'].append(d)
        if not p['diseases']: del(p['diseases'])
        # ortholog_diseases
        p['ortholog_diseases'] = []
        curs.execute("SELECT od.did, od.name, od.ortholog_id, od.score, o.taxid, o.species, o.db_id, o.geneid, o.symbol, o.name FROM ortholog o, ortholog_disease od WHERE o.id = od.ortholog_id AND od.protein_id = %s", (id,))
        for od in curs:
          p['ortholog_diseases'].append(od)
        if not p['ortholog_diseases']: del(p['ortholog_diseases'])
        # expression
        p['expressions'] = []
        curs.execute("SELECT * FROM expression WHERE protein_id = %s", (id,))
        for ex in curs:
          etype = ex['etype']
          val_col = self._expression_types[etype]
          ex['value'] = ex[val_col]
          del(ex['number_value'])
          del(ex['boolean_value'])
          del(ex['string_value'])
          p['expressions'].append(ex)
          #p['expressions'].append({'id': ex['id'], 'etype': etype, 'tissue': ex['tissue'], 'evidence': ex['evidence'], 'zscore': str(ex['zscore']), 'conf': ex['conf'], 'oid': ex['oid'], 'value': ex[val_col], 'qual_value': ex['qual_value'], 'confidence': ex['confidence'], 'gender': ex['gender']})
        if not p['expressions']: del(p['expressions'])
        # gtex
        p['gtexs'] = []
        curs.execute("SELECT * FROM gtex WHERE protein_id = %s", (id,))
        for gtex in curs:
          p['gtexs'].append(gtex)
        if not p['gtexs']: del(p['gtexs'])
        # compartments
        p['compartments'] = []
        curs.execute("SELECT * FROM compartment WHERE protein_id = %s", (id,))
        for comp in curs:
          p['compartments'].append(comp)
        if not p['compartments']: del(p['compartments'])
        # phenotypes
        p['phenotypes'] = []
        curs.execute("SELECT * FROM phenotype WHERE protein_id = %s", (id,))
        for pt in curs:
          p['phenotypes'].append(pt)
        if not p['phenotypes']: del(p['phenotypes'])
        # pathways
        p['pathways'] = []
        curs.execute("SELECT * FROM pathway WHERE protein_id = %s", (id,))
        for pw in curs:
          p['pathways'].append(pw)
        if not p['pathways']: del(p['pathways'])
        # pubmeds
        p['pubmeds'] = []
        curs.execute("SELECT pm.* FROM pubmed pm, protein2pubmed p2p WHERE pm.id = p2p.pubmed_id AND p2p.protein_id = %s", (id,))
        for pm in curs:
          p['pubmeds'].append(pm)
        if not p['pubmeds']: del(p['pubmeds'])
        # features
        p['features'] = {}
        curs.execute("SELECT * FROM feature WHERE protein_id = %s", (id,))
        for f in curs:
          ft = f['type']
          del(f['type'])
          if ft in p['features']:
            p['features'][ft].append(f)
          else:
            p['features'][ft] = [f]
        if not p['features']: del(p['features'])
        # panther_classes
        p['panther_classes'] = []
        curs.execute("SELECT pc.pcid, pc.name FROM panther_class pc, p2pc WHERE p2pc.panther_class_id = pc.id AND p2pc.protein_id = %s", (id,))
        for pc in curs:
          p['panther_classes'].append(pc)
        if not p['panther_classes']: del(p['panther_classes'])
        # orthologs
        p['orthologs'] = []
        curs.execute("SELECT * FROM ortholog WHERE protein_id = %s", (id,))
        for o in curs:
          p['orthologs'].append(o)
        if not p['orthologs']: del(p['orthologs'])
        ## DTO classification
        #if p['dtoid']:
        #  p['dto_classification'] = "::".join(self.get_protein_dto(p['dtoid']))
        # patent_counts
        p['patent_counts'] = []
        curs.execute("SELECT * FROM patent_count WHERE protein_id = %s", (id,))
        for pc in curs:
          p['patent_counts'].append(pc)
        if not p['patent_counts']: del(p['patent_counts'])
        # TIN-X Novelty and Importance(s)
        curs.execute("SELECT * FROM tinx_novelty WHERE protein_id = %s", (id,))
        row = curs.fetchone()
        if row:
          p['tinx_novelty'] = row['score']
        else:
          p['tinx_novelty'] = ''
        p['tinx_importances'] = []
        bad_diseases = ['disease', 'disease by infectious agent', 'bacterial infectious disease', 'fungal infectious disease', 'parasitic infectious disease', 'viral infectious disease', 'disease of anatomical entity', 'cardiovascular system disease', 'endocrine system disease', 'gastrointestinal system disease', 'immune system disease', 'integumentary system disease', 'musculoskeletal system disease', 'nervous system disease', 'reproductive system disease', 'respiratory system disease', 'thoracic disease', 'urinary system disease', 'disease of cellular proliferation', 'benign neoplasm', 'cancer', 'pre-malignant neoplasm', 'disease of mental health', 'cognitive disorder', 'developmental disorder of mental health', 'dissociative disorder', 'factitious disorder', 'gender identity disorder', 'impulse control disorder', 'personality disorder', 'sexual disorder', 'sleep disorder', 'somatoform disorder', 'substance-related disorder', 'disease of metabolism', 'acquired metabolic disease', 'inherited metabolic disorder', 'genetic disease', 'physical disorder', 'syndrome']
        curs.execute("SELECT td.name, ti.score FROM tinx_disease td, tinx_importance ti WHERE ti.protein_id = %s AND ti.disease_id = td.id ORDER BY ti.score DESC", (id,))
        for txi in curs:
          if txi['name'] not in bad_diseases:
            p['tinx_importances'].append({'disease': txi['name'], 'score': txi['score']})
        if not p['tinx_importances']: del(p['tinx_importances'])
        # gene_attribute counts
        if get_ga_counts:
          p['gene_attribute_counts'] = {}
          curs.execute("SELECT gat.name AS type, COUNT(*) AS attr_count FROM gene_attribute_type gat, gene_attribute ga WHERE gat.id = ga.gat_id AND ga.protein_id = %s GROUP BY type", (id,))
          for gact in curs:
            p['gene_attribute_counts'][gact['type']] = gact['attr_count']
          if not p['gene_attribute_counts']: del(p['gene_attribute_counts'])
        # KEGG Nearest Tclin(s)
        p['kegg_nearest_tclins'] = []
        curs.execute("SELECT p.name, p.geneid, p.uniprot, p.description, n.* FROM protein p, kegg_nearest_tclin n WHERE p.id = tclin_id AND n.protein_id = %s", (id,))
        for knt in curs:
          p['kegg_nearest_tclins'].append(knt)
        if not p['kegg_nearest_tclins']: del(p['kegg_nearest_tclins'])
        
    return p

  def get_protein_dto(self, dtoid):
    curs = self._conn.cursor(dictionary=True)
    curs.execute("SELECT name, parent FROM dto WHERE id = %s", (dtoid,))    
    row = curs.fetchone()
    # leaf node in path
    #path = ["%s~%s"%(dtoid, row['name'])]
    path = [row['name']]
    if row['parent']:
      # add path to the parent
      path = self.get_protein_dto(row['parent']) + path
    return path

  def get_target4tdlcalc(self, id):
    '''
    Function  : Get a target with only associated data required for TDL calculation.
    Arguments : An integer
    Returns   : Dictionary containing target data.
    Scope     : Public
    '''
    with closing(self._conn.cursor(dictionary=True, buffered=True)) as curs:
      self._logger.debug("ID: %s" % id)
      curs.execute("SELECT * FROM target WHERE id = %s", (id,))
      t = curs.fetchone()
      if not t: return False
      # Drug Activities
      t['drug_activities'] = []
      curs.execute("SELECT * FROM drug_activity WHERE target_id = %s", (id,))
      for da in curs:
        t['drug_activities'].append(da)
      if not t['drug_activities']: del(t['drug_activities'])
      # Cmpd Activity
      t['cmpd_activities'] = []
      curs.execute("SELECT * FROM cmpd_activity WHERE target_id = %s", (id,))
      for ca in curs:
        t['cmpd_activities'].append(ca)
      if not t['cmpd_activities']: del(t['cmpd_activities'])
      #
      # Protein associated data needed for TDL calculation
      #
      t['components'] = {}
      t['components']['protein'] = []
      p = {}
      p['tdl_infos'] = {}
      p['generifs'] = []
      curs.execute("SELECT * FROM t2tc WHERE target_id = %s", (id,))
      t2tc = curs.fetchone() # for now, all targets just have a single protein
      p['id'] = t2tc['protein_id']
      curs.execute("SELECT * FROM tdl_info WHERE itype = 'JensenLab PubMed Score' AND protein_id = %s", (p['id'],))
      pms = curs.fetchone()
      p['tdl_infos']['JensenLab PubMed Score'] = {'id': pms['id'], 'value': str(pms['number_value'])}
      curs.execute("SELECT * FROM tdl_info WHERE itype = 'Experimental MF/BP Leaf Term GOA' AND protein_id = %s", (p['id'],))
      efl_goa = curs.fetchone()
      if efl_goa:
        p['tdl_infos']['Experimental MF/BP Leaf Term GOA'] = {'id': efl_goa['id'], 'value': '1'}
      curs.execute("SELECT * FROM tdl_info WHERE itype = 'Ab Count' AND protein_id = %s", (p['id'],))
      abct = curs.fetchone()
      p['tdl_infos']['Ab Count'] = {'id': abct['id'], 'value': str(abct['integer_value'])}
      curs.execute("SELECT * FROM generif WHERE protein_id = %s", (p['id'],))
      for gr in curs:
        p['generifs'].append({'id': gr['id'], 'pubmed_ids': gr['pubmed_ids'], 'text': gr['text']})
      if not p['generifs']: del(p['generifs'])
    t['components']['protein'].append(p)
      
    return t

  def get_target_count(self, idg=False, past_id=None):
    '''
    Function  : Get count of TCRD targets
    Arguments : Optional arg:
                idg: Get only IDG-Eligible targets [Default = False]
    Returns   : Integer
    Example   : ct = dba.get_target_count()
    Scope     : Public
    Comments  : The value of idg is ignored if family is set.
    '''
    with closing(self._conn.cursor()) as curs:
      if idg:
        if past_id:
          sql = "SELECT count(*) FROM target WHERE id > %s AND idg"
          curs.execute(sql, (past_id,))
        else:
          sql = "SELECT count(*) FROM target WHERE idg"
          curs.execute(sql)
      else:
        if past_id:
          sql = "SELECT count(*) FROM target WHERE id > %s"
          curs.execute(sql, (past_id,))
        else:
          sql = "SELECT count(*) FROM target"
          curs.execute(sql)
      ct = curs.fetchone()[0]
    return ct

  def get_targets(self, idg=False, include_annotations=False, past_id=None, get_ga_counts=False):
    '''
    Function  : Generator function to get TCRD targets
    Arguments : Two optional args:
                idg: Get only targets [Default = False]
                include_annotations: See get_target()
    Returns   : One target dictionary - as per get_target() - at a time
    Example   : for target in dba.get_targets():
                  do something with target
    Scope     : Public
    '''
    with closing(self._conn.cursor(buffered=True)) as curs:
      if idg:
        if past_id:
          sql = "SELECT id FROM target WHERE WHERE id > %s AND idg"
          curs.execute(sql, (past_id,))
        else:
          sql = "SELECT id FROM target WHERE idg"
          curs.execute(sql)
      else:
        if past_id:
          sql = "SELECT id FROM target WHERE id > %s"
          curs.execute(sql, (past_id,))
        else:
          sql = "SELECT id FROM target"
          curs.execute(sql)
      for i in curs:
        #self._logger.debug("ID: %s" % type(i))
        t = self.get_target(i[0], include_annotations, get_ga_counts)
        yield t

  def get_tdl_target_count(self, tdl, idg=False):
    '''
    Function  : Get count of TCRD targets by TDL
    Arguments : A TDL string: Tclin, Tchem, Tbio or Tdark
                Optional arg:
                idg: Get only IDG targets [Default = False]
    Returns   : Integer
    Example   : ct = dba.get_tdl_target_count()
    Scope     : Public
    Comments  : 
    '''
    with closing(self._conn.cursor()) as curs:
      if idg:
        sql = "SELECT count(*) FROM target WHERE tdl = %s AND idg"
        curs.execute(sql, (tdl,))
      else:
        sql = "SELECT count(*) FROM target WHERE tdl = %s "
        curs.execute(sql, (tdl,))
      ct = curs.fetchone()[0]
    return ct

  def get_tdl_targets(self, tdl, idg=False, include_annotations=False, get_ga_counts=False):
    '''
    Function  : Generator function to get TCRD targets by TDL
    Arguments : A TDL string: Tclin, Tchem, Tbio or Tdark
                Two optional args:
                idg: Get only IDG Phase 2 targets [Default = False]
                include_annotations: See get_target()
    Returns   : One target dictionary - as per get_target() - at a time
    Example   : for target in dba.get_tdl_targets():
                  do something with target
    Scope     : Public
    Comments  : The value of idg is ignored if family is set.
    '''
    with closing(self._conn.cursor()) as curs:
      if idg:
        sql = "SELECT id FROM target WHERE tdl = %s AND idg"
        curs.execute(sql, (tdl,))
      else:
        sql = "SELECT id FROM target WHERE tdl = %s"
        curs.execute(sql, (tdl,))
      for i in curs:
        #self._logger.debug("ID: %s" % type(i))
        t = self.get_target(i[0], include_annotations, get_ga_counts)
        yield t

  def get_targets4tdlcalc(self):
    '''
    Function  : Generator function to get TCRD targets for TDL calculation
    Arguments : N/A
    Returns   : One target dictionary - as per get_target4tdlcalc() - at a
    time, with data needed for TDL claculation
    Example   : for target in dba.get_targets4tdlcalc():
                  # returns 
    Scope     : Public
    '''
    with closing(self._conn.cursor(buffered=True)) as curs:
      sql = "SELECT id FROM target"
      curs.execute(sql)
      for i in curs:
        #self._logger.debug("ID: %s" % type(i))
        t = self.get_target4tdlcalc(i[0])
        yield t

  def get_target_ids(self):
    '''
    Function  : Get all TCRD target ids
    Arguments : N/A
    Returns   : A list of integers
    Scope     : Public
    '''
    ids = []
    sql = "SELECT id FROM target"
    with closing(self._conn.cursor()) as curs:
      curs.execute(sql)
      for i in curs:
        #self._logger.debug("ID: %s" % type(i))
        ids.append(i[0])
    return ids
        

  def get_tdl_target_count(self, tdl, idg=False):
    '''
    Function  : Get count of TCRD targets by TDL
    Arguments : A TDL string: Tclin, Tchem, Tbio or Tdark
                Optional arg:
                idg: Get only IDG targets [Default = False]
    Returns   : Integer
    Example   : ct = dba.get_tdl_target_count()
    Scope     : Public
    Comments  : 
    '''
    with closing(self._conn.cursor()) as curs:
      if idg:
        sql = "SELECT count(*) FROM target WHERE tdl = %s AND idg"
        curs.execute(sql, (tdl,))
      else:
        sql = "SELECT count(*) FROM target WHERE tdl = %s "
        curs.execute(sql, (tdl,))
      ct = curs.fetchone()[0]
    return ct

  def find_targets(self, q, idg=False, include_annotations=False, get_ga_counts=False):
    '''
    Function  : Get target(s) by various query criteria
    Arguments : A distionary containing query criteria and two optional booleans.
    Returns   : A List of dictionaries containing target data.
    Examples  : Find target(s) by HGNC Gene Symbol:
                targets = dba.find_targets({'sym': 'HRH3'}, include_annotations=True)
                Find target(s) by name (Swissprot Accession):
                targets = dba.find_targets({'name': '5HT1A_HUMAN'}, include_annotations=True)
                Find target(s) by UniProt Accession:
                targets = dba.find_targets({'uniprot': 'Q9UP38'}, include_annotations=True)
                Find target(s) by NCBI Gene ID:
                targets = dba.find_targets({'geneid': 167359}, include_annotations=True)
                Find target(s) by STRING ID:
                targets = dba.find_targets({'stringid': 'ENSP00000300161'}, include_annotations=True)
    Scope     : Public
    Comments  : By default, this searches all targets. To restrict the seach to IDG family
                targets, call with idg=True
                By default, this returns target and target component (ie. protein and
                nucleic_acid) data only. To get all associated annotations, call with
                include_annotations=True
    '''
    if idg:
      sql = "SELECT t.id FROM target t, t2tc, protein p WHERE t.id = t2tc.target_id AND t2tc.protein_id = p.id AND t.idg"
    else:
      sql ="SELECT target_id FROM t2tc, protein p WHERE t2tc.protein_id = p.id"
    if 'sym' in q:
      sql += " AND p.sym = %s"
      params = (q['sym'],)
      # Look at aliases
      #sql ="SELECT distinct target_id FROM t2tc, protein p, alias a WHERE t2tc.protein_id = p.id AND p.id = a.protein_id AND a.name = %s"
    elif 'name' in q:
      sql += " AND p.name = %s"
      params = (q['name'],)
    elif 'uniprot' in q:
      sql += " AND p.uniprot = %s"
      params = (q['uniprot'],)
    elif 'geneid' in q:
      sql += " AND p.geneid = %s"
      params = (q['geneid'],)
    elif 'stringid' in q:
      sql += " AND p.stringid = %s"
      params = (q['stringid'],)
    else:
      self.warning("Invalid query parameters sent to find_targets(): ", q)
      return False
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%(str(params[0])))

    targets = []
    with closing(self._conn.cursor(buffered=True)) as curs:
      curs.execute(sql, params)
      for row in curs:
        targets.append( self.get_target(row[0], include_annotations, get_ga_counts) )
    return targets

  def find_targets_by_xref(self, q, idg=False, include_annotations=False, get_ga_counts=False):
    '''
    Function  : Get target(s) by xref type and value.
    Arguments : A distionary containing query criteria and two optional booleans.
    Returns   : A List of dictionaries containing target data.
    Examples  : Find target(s) by RefSeq xref:
                targets = dba.find_targets_by_xref({'xtype': 'RefSeq', 'value': 'NM_123456'}, include_annotations=True)
    Scope     : Public
    Comments  : By default, this searches all targets. To restrict the seach to IDG family
                targets, call with idg=True
                By default, this returns target and target component (ie. protein and
                nucleic_acid) data only.  To get all associated annotations, call with
                include_annotations=True
    '''
    targets = []
    if 'xtype' in q and 'value' in q:
      tids = []
      # first look by target xrefs
      if idg:
        sql = "SELECT t.id FROM target t, xref x WHERE t.id = x.target_id AND t.idg AND x.protein_id IS NULL AND x.xtype = %s AND x.value = %s"
      else:
        sql = "SELECT target_id FROM xref WHERE protein_id IS NULL AND xtype = %s AND value = %s"
      params = (q['xtype'], q['value'])
      with closing(self._conn.cursor()) as curs:
        curs.execute(sql, params)
        for row in curs:
          tids.append(row[0])
      # then look by component xrefs
      if idg:
        sql ="SELECT t.id FROM target t, t2tc, protein p, xref x WHERE t.id = t2tc.target_id AND t.idg AND t2tc.protein_id = p.id and p.id = x.protein_id AND x.xtype = %s AND x.value = %s"
      else:
        sql ="SELECT t2tc.target_id FROM t2tc, protein p, xref x WHERE t2tc.protein_id = p.id and p.id = x.protein_id AND x.xtype = %s AND x.value = %s"
      params = (q['xtype'], q['value'])
      with closing(self._conn.cursor()) as curs:
        curs.execute(sql, params)
        for row in curs:
          tids.append(row[0])

      if tids:
        if len(tids) > 1:
          # get unique ids
          tmpset = set(tids)
          tids = list(tmpset)
      else:
        return False # No target found

      for id in tids:
        targets.append( self.get_target(id, include_annotations, get_ga_counts) )

    else:
      self.warning("Invalid query parameters sent to find_targets_by_xref(): ", q)
      return False

    return targets

  def find_targets_by_alias(self, q, idg=False, include_annotations=False, get_ga_counts=False):
    '''
    Function  : Get target(s) by (symbol or UniProt) alias.
    Arguments : A distionary containing query criteria and two optional booleans.
    Returns   : A List of dictionaries containing target data.
    Examples  : 
    Scope     : Public
    Comments  : By default, this searches all targets. To restrict the seach to IDG family
                targets, call with idg=True
                By default, this returns target and target component (ie. protein and
                nucleic_acid) data only.  To get all associated annotations, call with
                include_annotations=True
    '''
    if 'type' not in q or 'value' not in q:
      self.warning("Invalid query parameters sent to find_targets_by_alias(): ", q)
      return False

    tids = []
    targets = []
    if idg:
      sql = "SELECT t.id FROM target t, protein p, t2tc, alias a WHERE t.id = t2tc.target_id AND t2tc.protein_id = p.id AND p.id = a.protein_id AND t.idg AND a.type = %s AND a.value = %s"
    else:
      sql = "SELECT t.id FROM target t, protein p, t2tc, alias a WHERE t.id = t2tc.target_id AND t2tc.protein_id = p.id AND p.id = a.protein_id AND a.type = %s AND a.value = %s"
    params = (q['type'], q['value'])
    with closing(self._conn.cursor()) as curs:
      curs.execute(sql, params)
      for row in curs:
        tids.append(row[0])
    if tids:
      # get unique ids
      tmpset = set(tids)
      tids = list(tmpset)
    else:
      return False # No target found
    for id in tids:
      targets.append( self.get_target(id, include_annotations, get_ga_counts) )
    
    return targets

  def get_nhprotein(self, id, include_annotations=False):
    '''
    Function  : Get an nhprotein by id.
    Arguments : An integer and an optional boolean.
    Returns   : Dictionary containing nhprotein data.
    Example   : nhprotein = dba->get_nhprotein(42, include_annotations=True) ;
    Scope     : Public
    Comments  : By default, this returns nhprotein data only. To get all
                associated annotations, call with include_annotations=True
    '''
    with closing(self._conn.cursor(dictionary=True)) as curs:
      curs.execute("SELECT * FROM nhprotein WHERE id = %s", (id,))
      nhp = curs.fetchone()
      if not nhp:
        return False
      
      if include_annotations:
        # phenotypes
        nhp['phenotypes'] = []
        curs.execute("SELECT * FROM phenotype WHERE nhprotein_id = %s", (id,))
        for pt in curs:
          nhp['phenotypes'].append(pt)
        if not nhp['phenotypes']: del(nhp['phenotypes'])
    return nhp

  def get_nhprotein_count(self):
    '''
    Function  : Get count of TCRD nhproteins
    Arguments : NA
    Returns   : Integer
    Example   : ct = dba.get_nhprotein_count()
    Scope     : Public
    Comments  : 
    '''
    with closing(self._conn.cursor()) as curs:
      sql = "SELECT count(*) FROM nhprotein"
      curs.execute(sql)
      ct = curs.fetchone()[0]
    return ct

  def get_nhproteins(self, species=None):
    '''
    Function  : Generator function to get TCRD nhproteins
    Arguments : Optional arg
                species: Get nhproteins for a given spesies [Default = None]
    Returns   : One nhprotein dictionary at a time
    Example   : for nhp in dba.get_nhproteins():
                  do something with nhp
    Scope     : Public
    '''
    with closing(self._conn.cursor(dictionary=True)) as curs:
      if species:
        sql = "SELECT * FROM nhprotein WHERE species = %s"
        curs.execute(sql, (species,))
      else:
        sql = "SELECT * FROM nhprotein"
        curs.execute(sql)
      for nhp in curs:
        yield nhp

  def find_nhproteins(self, q, species=None):
    '''
    Function  : Get nhprotein(s) by various query criteria
    Arguments : A dictionary containing query criteria.
                Optional arg
                species: Get nhproteins for a given spesies [Default = None]
    Returns   : A List of dictionaries containing nhprotein data.
    Examples  : Find nhproteins by HGNC Gene Symbol:
                nhproteins = dba.find_nhproteins({'sym': 'HRH3'})
                Find nhproteins by name (Swissprot Accession):
                nhproteins = dba.find_nhproteins({'name': '5HT1A_HUMAN'})
                Find nhproteins by UniProt Accession:
                nhproteins = dba.find_nhproteins({'uniprot': 'Q9UP38'})
                Find nhproteins by NCBI Gene ID:
                nhproteins = dba.find_nhproteins({'geneid': 167359})
    Scope     : Public
    Comments  : 
    '''
    sql = "SELECT * FROM nhprotein WHERE "
    if 'sym' in q:
      sql += "sym = %s"
      params = (q['sym'],)
    elif 'name' in q:
      sql += "name = %s"
      params = (q['name'],)
    elif 'uniprot' in q:
      sql += "uniprot = %s"
      params = (q['uniprot'],)
    elif 'geneid' in q:
      sql += "geneid = %s"
      params = (q['geneid'],)
    else:
      self.warning("Invalid query parameters sent to find_nhproteins(): ", q)
      return False
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%(str(params[0])))
    if species:
      sql += " AND species = %s"
      params = params + (species,)
    nhproteins = []
    with closing(self._conn.cursor(dictionary=True)) as curs:
      curs.execute(sql, params)
      for row in curs:
        nhproteins.append(row)
    return nhproteins

  def get_xref_values(self, xtype):
    '''
    Function  : Get
    Arguments : A string containing a xref.xtype
    Returns   : An array of strings
    Example   :
    Scope     : Public
    Comments  :
    '''
    if not xtype:
      self.warning("No xtype sent to get_xref_values(): ")
      return False
    vals = []
    sql = "SELECT DISTINCT value FROM xref WHERE xtype = %s"
    params = (xtype,)
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
        for row in curs:
          vals.append(row[0])
      except mysql.Error, e:
        self._conn.rollback()
        msg = "MySQL Error: %s" % str(e)
        #self.error(msg)
        self._logger.error(msg)
        return False
    return vals

  def get_target_features(self, idg=False):
    '''
    Function  : Get target features
    Arguments : N/A
    Returns   : A dictionary of arrays of strings
    Example   :
    Scope     : Public
    Comments  : Dict keys are annotation types: Classifications, Domains, Expressions, Phenotypes, Diseases, Pathways, GOAs, Features
    '''
    features = {}
    # Classifications
    if idg:
      sql = "SELECT DISTINCT pc.pcid, pc.name FROM panther_class pc, p2pc, target t, t2tc, protein p WHERE t.id = t2tc.target_id AND t2tc.protein_id = p.id AND p.id = p2pc.protein_id AND pc.id = p2pc.panther_class_id AND t.id IN (SELECT id FROM target WHERE idg)"
    else:
      sql = "SELECT DISTINCT pc.pcid, pc.name FROM panther_class pc, p2pc WHERE pc.id = p2pc.panther_class_id"
    classifications = []
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql)
        for row in curs:
          classifications.append("%s:%s" % (row[0], row[1]))
      except mysql.Error, e:
        self._conn.rollback()
        msg = "MySQL Error: %s" % str(e)
        self._logger.error(msg)
        return False
    features['Classifications'] = classifications
    # Domains
    if idg:
      sql = "SELECT DISTINCT x.value FROM xref x, target t, t2tc, protein p WHERE xtype = 'Pfam' AND t.id = t2tc.target_id AND t2tc.protein_id = p.id AND p.id = x.protein_id AND t.id IN (SELECT id FROM target WHERE idg)"
    else:
      sql = "SELECT DISTINCT value FROM xref WHERE xtype = 'Pfam'"
    domains = []
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql)
        for row in curs:
          domains.append(row[0])
      except mysql.Error, e:
        self._conn.rollback()
        msg = "MySQL Error: %s" % str(e)
        #self.error(msg)
        self._logger.error(msg)
        return False
    if idg:
      sql = "SELECT DISTINCT x.value FROM xref x, target t, t2tc, protein p WHERE xtype = 'InterPro' AND t.id = t2tc.target_id AND t2tc.protein_id = p.id AND p.id = x.protein_id AND t.id IN (SELECT id FROM target WHERE idg)"
    else:
      sql = "SELECT DISTINCT value FROM xref WHERE xtype = 'InterPro'"
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql)
        for row in curs:
          domains.append(row[0])
      except mysql.Error, e:
        self._conn.rollback()
        msg = "MySQL Error: %s" % str(e)
        #self.error(msg)
        self._logger.error(msg)
        return False
    if idg:
      sql = "SELECT DISTINCT x.value FROM xref x, target t, t2tc, protein p WHERE xtype = 'PROSITE' AND t.id = t2tc.target_id AND t2tc.protein_id = p.id AND p.id = x.protein_id AND t.id IN (SELECT id FROM target WHERE idg)"
    else:
      sql = "SELECT DISTINCT value FROM xref WHERE xtype = 'PROSITE'"
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql)
        for row in curs:
          domains.append(row[0])
      except mysql.Error, e:
        self._conn.rollback()
        msg = "MySQL Error: %s" % str(e)
        #self.error(msg)
        self._logger.error(msg)
        return False
    features['Domains'] = domains
    # Expressions
    if idg:
      sql = "SELECT DISTINCT e.etype, e.tissue FROM expression e, target t, t2tc, protein p WHERE t.id = t2tc.target_id AND t2tc.protein_id = p.id AND p.id = e.protein_id AND t.id IN (SELECT id FROM target WHERE idg)"
    else:
      sql = "SELECT DISTINCT etype, tissue FROM expression"
    expressions = []
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql)
        for row in curs:
          expressions.append("%s:%s" % (row[0], row[1]))
      except mysql.Error, e:
        self._conn.rollback()
        msg = "MySQL Error: %s" % str(e)
        #self.error(msg)
        self._logger.error(msg)
        return False
    features['Expressions'] = expressions
    # Phenotypes
    if idg:
      sql = "SELECT DISTINCT pt.ptype, pt.trait, pt.term_id, pt.term_name FROM phenotype pt, target t, t2tc, protein p WHERE t.id = t2tc.target_id AND t2tc.protein_id = p.id AND p.id = pt.protein_id AND t.id IN (SELECT id FROM target WHERE idg)"
    else:
      sql = "SELECT DISTINCT ptype, trait, term_id, term_name FROM phenotype"
    phenotypes = []
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql)
        for row in curs:
          if row[1]:
            phenotypes.append("%s:%s" % (row[0], row[1]))
          else:
            phenotypes.append("%s:%s:%s" % (row[0], row[2], row[3]))
      except mysql.Error, e:
        self._conn.rollback()
        msg = "MySQL Error: %s" % str(e)
        self._logger.error(msg)
        return False
    features['Phenotypes'] = phenotypes
    # Diseases
    if idg:
      sql = "SELECT DISTINCT dtype, name FROM disease td, WHERE target_id IN (SELECT id FROM target WHERE idg)"
    else:
      sql = "SELECT DISTINCT dtype, name FROM disease"
    diseases = []
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql)
        for row in curs:
          diseases.append("%s:%s" % (row[0], row[1]))
      except mysql.Error, e:
        self._conn.rollback()
        msg = "MySQL Error: %s" % str(e)
        #self.error(msg)
        self._logger.error(msg)
        return False
    features['Diseases'] = diseases
    # Pathways
    if idg:
      sql = "SELECT DISTINCT pw.pwtype, pw.name FROM pathway pw, target t, t2tc, protein p  WHERE t.id = t2tc.target_id AND t2tc.protein_id = p.id AND p.id = pw.protein_id AND t.id IN (SELECT id FROM target WHERE idg)"
    else:
      sql = "SELECT DISTINCT pwtype, name FROM pathway"
    pathways = []
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql)
        for row in curs:
          pathways.append("%s:%s" % (row[0], row[1]))
      except mysql.Error, e:
        self._conn.rollback()
        msg = "MySQL Error: %s" % str(e)
        #self.error(msg)
        self._logger.error(msg)
        return False
    features['Pathways'] = pathways
    # GO Terms
    if idg:
      sql = "SELECT DISTINCT g.go_term FROM goa g, target t, t2tc, protein p WHERE t.id = t2tc.target_id AND t2tc.protein_id = p.id AND p.id = g.protein_id AND t.id IN (SELECT id FROM target WHERE idg)"
    else:
      sql = "SELECT DISTINCT go_term FROM goa"
    goas = []
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql)
        for row in curs:
          goas.append(row[0])
      except mysql.Error, e:
        self._conn.rollback()
        msg = "MySQL Error: %s" % str(e)
        #self.error(msg)
        self._logger.error(msg)
        return False
    features['GOAs'] = goas
    # UniProt Features
    if idg:
      sql = "SELECT DISTINCT f.type FROM feature f, target t, t2tc, protein p WHERE t.id = t2tc.target_id AND t2tc.protein_id = p.id AND p.id = g.protein_id AND t.id IN (SELECT id FROM target WHERE idg)"
    else:
      sql = "SELECT DISTINCT type FROM feature"
    upfeats = []
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql)
        for row in curs:
          upfeats.append(row[0])
      except mysql.Error, e:
        self._conn.rollback()
        msg = "MySQL Error: %s" % str(e)
        #self.error(msg)
        self._logger.error(msg)
        return False
    features['Features'] = upfeats

    return features

  def get_xref_types(self):
    '''
    Function  : Get xref_types
    Arguments :
    Returns   : An array of strings
    Example   :
    Scope     : Public
    Comments  :
    '''
    xtypes = []
    sql = "SELECT name FROM xref_type"
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql)
        for row in curs:
          xtypes.append(row[0])
      except mysql.Error, e:
        self._conn.rollback()
        msg = "MySQL Error: %s" % str(e)
        #self.error(msg)
        self._logger.error(msg)
        return False

    return xtypes

  def get_tissues(self, etype=None):
    '''
    Function  : Get distict expression.tissue, optionally for a given etype
    Arguments :
    Returns   : An array of strings
    Example   :
    Scope     : Public
    Comments  :
    '''
    tissues = []
    if etype:
      if etype == 'JensenLab Experiment':
        sql = "SELECT DISTINCT tissue FROM expression WHERE etype LIKE 'JensenLab Experiment%' ORDER BY tissue"
      else:
        sql = "SELECT DISTINCT tissue FROM expression WHERE etype = '%s'" % etype
    else:
      sql = "SELECT DISTINCT tissue FROM expression"
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql)
        for row in curs:
          tissues.append(row[0])
      except mysql.Error, e:
        self._conn.rollback()
        msg = "MySQL Error: %s" % str(e)
        #self.error(msg)
        self._logger.error(msg)
        return False

    return tissues

  def get_pathways(self, pwtype=None):
    '''
    Function  : Get distinct pathway.names, optionally for a given pwtype
    Arguments :
    Returns   : An array of strings
    Example   :
    Scope     : Public
    Comments  :
    '''
    pathways = []
    if pwtype:
      sql = "SELECT DISTINCT name FROM pathway WHERE pwtype = '%s'" % pwtype
    else:
      sql = "SELECT DISTINCT name FROM pathway"
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql)
        for row in curs:
          pathways.append(row[0])
      except mysql.Error, e:
        self._conn.rollback()
        msg = "MySQL Error: %s" % str(e)
        #self.error(msg)
        self._logger.error(msg)
        return False

    return pathways

  def get_pathway_targets(self, pwtype, name):
    '''
    Function  : Get protein_ids associated with a given pathway
    Arguments : Two strings: a pwtype and a name
    Returns   : An array of integers
    Example   :
    Scope     : Public
    Comments  :
    '''
    pids = []
    sql = "SELECT protein_id from pathway where pwtype = '%s' AND name = '%s'" % (pwtype, name)
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql)
        for row in curs:
          pids.append(row[0])
      except mysql.Error, e:
        self._conn.rollback()
        msg = "MySQL Error: %s" % str(e)
        #self.error(msg)
        self._logger.error(msg)
        return False

    return pids

  def get_diseases(self, dtype=None):
    '''
    Function  : Get distinct disease.did, optionally for a given dtype
    Arguments :
    Returns   : An array of strings
    Example   :
    Scope     : Public
    Comments  :
    '''
    dids = []
    if dtype:
      sql = "SELECT DISTINCT did FROM disease WHERE did IS NOT NULL AND did != '' AND dtype = '%s'" % dtype
    else:
      sql = "SELECT DISTINCT did FROM disease WHERE did IS NOT NULL AND did != ''"
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql)
        for row in curs:
          dids.append(row[0])
      except mysql.Error, e:
        self._conn.rollback()
        msg = "MySQL Error: %s" % str(e)
        #self.error(msg)
        self._logger.error(msg)
        return False

    return dids

  def get_disease_targets(self, did):
    '''
    Function  : Get target_ids associated with a given disease.did
    Arguments : Two strings: a pwtype and a name
    Returns   : An array of integers
    Example   :
    Scope     : Public
    Comments  :
    '''
    tids = []
    sql = "SELECT DISTINCT target_id from disease where did = '%s'" % did
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql)
        for row in curs:
          tids.append(row[0])
      except mysql.Error, e:
        self._conn.rollback()
        msg = "MySQL Error: %s" % str(e)
        #self.error(msg)
        self._logger.error(msg)
        return False

    return tids

  def get_phenotypes(self, ptype=None):
    '''
    Function  : Get distinct phenotype.trait, optionally for a given ptype
    Arguments :
    Returns   : An array of strings
    Example   :
    Scope     : Public
    Comments  :
    '''
    traits = []
    if ptype:
      sql = "SELECT DISTINCT trait FROM phenotype WHERE ptype = '%s'" % ptype
    else:
      sql = "SELECT DISTINCT trait FROM phenotype"
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql)
        for row in curs:
          traits.append(row[0])
      except mysql.Error, e:
        self._conn.rollback()
        msg = "MySQL Error: %s" % str(e)
        #self.error(msg)
        self._logger.error(msg)
        return False

    return traits

  def get_nearest_kegg_tclins(self, pid, dir):
    if not pid or not dir:
      self.warning("Invalid parameters sent to get_nearest_kegg_tclin(): ", init)
      return False
    results = []
    # Downstream
    if dir == 'downstream':
      min_dist = None
      sql = "SELECT MIN(kd.distance) AS min_distance FROM target t, t2tc, protein p, kegg_distance kd WHERE t.id = t2tc.target_id AND t2tc.protein_id = p.id AND p.id = kd.pid2 AND kd.pid1 = %s AND t.tdl = 'Tclin'"
      with closing(self._conn.cursor()) as curs:
        try:
          curs.execute(sql, (pid,))
          min_dist = curs.fetchone()[0]
        except mysql.Error, e:
          self._conn.rollback()
          msg = "MySQL Error: %s" % str(e)
          self._logger.error(msg)
          self._logger.debug("SQLpat: %s"%sql)
          self._logger.debug("SQLparams: %d"%pid)
          return False
        if not min_dist:
          return None
      sql = "SELECT p.id AS protein_id, kd.distance FROM target t, t2tc, protein p, kegg_distance kd WHERE t.id = t2tc.target_id AND t2tc.protein_id = p.id AND p.id = kd.pid2 AND kd.pid1 = %s AND kd.distance = %s AND t.tdl = 'Tclin'"
      with closing(self._conn.cursor(dictionary=True)) as curs:
        try:
          curs.execute(sql, (pid, min_dist))
          for d in curs:
            results.append(d)
        except mysql.Error, e:
          self._conn.rollback()
          msg = "MySQL Error: %s" % str(e)
          self._logger.error(msg)
          self._logger.debug("SQLpat: %s"%sql)
          self._logger.debug("SQLparams: %d, %d"%(pid, min_dist))
          return False
    # Upstream
    elif dir == 'upstream':
      min_dist = None
      sql = "SELECT MIN(kd.distance) AS min_distance FROM target t, t2tc, protein p, kegg_distance kd WHERE t.id = t2tc.target_id AND t2tc.protein_id = p.id AND p.id = kd.pid1 AND kd.pid2 = %s AND t.tdl = 'Tclin'"
      with closing(self._conn.cursor()) as curs:
        try:
          curs.execute(sql, (pid,))
          min_dist = curs.fetchone()[0]
        except mysql.Error, e:
          self._conn.rollback()
          msg = "MySQL Error: %s" % str(e)
          self._logger.error(msg)
          self._logger.debug("SQLpat: %s"%sql)
          self._logger.debug("SQLparams: %d"%pid)
          return False
      if not min_dist:
        return None
      sql = "SELECT p.id AS protein_id, kd.distance FROM target t, t2tc, protein p, kegg_distance kd WHERE t.id = t2tc.target_id AND t2tc.protein_id = p.id AND p.id = kd.pid1 AND kd.pid2 = %s AND kd.distance = %s AND t.tdl = 'Tclin'"
      with closing(self._conn.cursor(dictionary=True)) as curs:
        try:
          curs.execute(sql, (pid, min_dist))
          for d in curs:
            results.append(d)
        except mysql.Error, e:
          self._conn.rollback()
          msg = "MySQL Error: %s" % str(e)
          self._logger.error(msg)
          self._logger.debug("SQLpat: %s"%sql)
          self._logger.debug("SQLparams: %d, %d"%(pid, min_dist))
          return False
    else:
      self.warning("Invalid parameters sent to get_nearest_kegg_tclin(): direction must be 'upstream' or 'downstream'")
      return False
    
    return results

  def get_common_kegg_pathway(self, pid1, pid2):
    pwname = ''
    sql = "SELECT name FROM pathway WHERE pwtype = 'KEGG' and protein_id = %s and name in (select name from pathway where pwtype = 'KEGG' and protein_id = %s)"
    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, (pid1, pid2))
        pwname = curs.fetchone()[0]
      except mysql.Error, e:
        msg = "MySQL Error: %s" % str(e)
        #self.error(msg)
        self._logger.error(msg)
        return False
    return pwname

  def get_complex_goas(self):
    goas = []
    sql = "SELECT * FROM goa WHERE go_term LIKE '%complex'"
    self._logger.error("Executing SQL: %s"%sql)
    with closing(self._conn.cursor(dictionary=True)) as curs:
      try:
        curs.execute(sql)
        for d in curs:
          goas.append(d)
      except mysql.Error, e:
        msg = "MySQL Error: %s" % str(e)
        #self.error(msg)
        self._logger.error(msg)
        return False
    return goas

  def get_orthologs_dbid2id(self):
    dbid2id = {}
    sql = "SELECT * FROM ortholog"
    self._logger.error("Executing SQL: %s"%sql)
    with closing(self._conn.cursor(dictionary=True)) as curs:
      try:
        curs.execute(sql)
        for d in curs:
          dbid2id[d['db_id']] = d['id']
      except mysql.Error, e:
        msg = "MySQL Error: %s" % str(e)
        #self.error(msg)
        self._logger.error(msg)
        return False
    return dbid2id

  def get_ortholog(self, q):
    if 'taxid' not in q:
      self.warning("Invalid query parameters sent to get_ortholog(): ", q)
      return False
    if 'symbol' in q:
      sql = "SELECT * FROM ortholog WHERE symbol = %s AND taxid = %s"
      params = (q['symbol'], q['taxid'])
    elif 'geneid' in q:
      sql = "SELECT * FROM ortholog WHERE geneid = %s AND taxid = %s"
      params = (q['geneid'], q['taxid'])
    else:
      self.warning("Invalid query parameters sent to get_ortholog(): ", q)
      return False
    with closing(self._conn.cursor(dictionary=True)) as curs:
      curs.execute(sql, params)
      ortholog = curs.fetchone()
    return ortholog

  def get_db2do_map(self, db):
    '''
    This maps xref values from a given database (E.g. OMIM, MeSH, etc.) to all associated DOIDs.
    '''
    # First get  all xref IDs from the given source database
    dbids = []
    with closing(self._conn.cursor()) as curs:
      curs.execute("SELECT DISTINCT value FROM do_xref WHERE db = %s", (db,))
      for row in curs:
        dbids.append(row[0])
    # Then get all DOIDs for each source database ID
    dbid2doids = defaultdict(list) # maps each source database ID to all DOIDs in TCRD
    with closing(self._conn.cursor()) as curs:
      for dbid in dbids:
        curs.execute("SELECT doid FROM do_xref WHERE db = %s AND value = %s", (db, dbid))
        for row in curs:
          dbid2doids[dbid].append(row[0])
    return dbid2doids

  #
  # Update Methods
  #
  def upd_target(self, id, col, val):
    '''
    Function  :
    Arguments :
    Returns   :
    Example   :
    Scope     : Public
    Comments  :
    '''
    sql = 'UPDATE target SET %s' % col
    sql += ' = %s WHERE id = %s'
    params = (val, id)
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s, %d"%params)

    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
        self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        msg = "MySQL Error: %s" % str(e)
        #self.error(msg)
        self._logger.error(msg)
        return False
    return True

  def upd_protein(self, id, col, val):
    '''
    Function  :
    Arguments :
    Returns   :
    Example   :
    Scope     : Public
    Comments  :
    '''
    sql = 'UPDATE protein SET %s' % col
    sql += ' = %s WHERE id = %s'
    params = (val, id)
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s, %d"%params)

    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
        self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        msg = "MySQL Error: %s" % str(e)
        #self.error(msg)
        self._logger.error(msg)
        self._logger.error("Value is: %s"%val)
        return False
    return True

  def upd_tdl_info(self, id, col, val):
    '''
    Function  :
    Arguments :
    Returns   :
    Example   :
    Scope     : Public
    Comments  :
    '''
    sql = 'UPDATE tdl_info SET %s' % col
    sql += ' = %s WHERE id = %s'
    params = (val, id)
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s, %d"%params)

    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
        self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        msg = "MySQL Error: %s" % str(e)
        #self.error(msg)
        self._logger.error(msg)
        return False
    return True

  def do_update(self, init):
    '''
    Function  : Update a single table.col with val by row id
    Arguments : A dictionary with keys table, id, col and val
    Returns   : Boolean indicating success or failure
    Example   :
    Scope     : Public
    Comments  :
    '''
    if 'table' in init and 'id' in init and 'col' in init and 'val' in init:
      params = [init['val'], init['id']]
    else:
      self.warning("Invalid parameters sent to do_update(): ", init)
      return False
    sql = 'UPDATE %s SET %s' % (init['table'], init['col'])
    sql += ' = %s WHERE id = %s'
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %s"%", ".join([str(p) for p in params]))

    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
        self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        msg = "MySQL Error: %s" % str(e)
        #self.error(msg)
        self._logger.error(msg)
        return False
    return True

  #
  # Delete Methods
  #
  def del_protein_xrefs(self, id, xtype=False):
    '''
    Function  : Delete xrefs for a given protein
    Arguments : A proteinid and an optional xtype
    Returns   : Boolean indicating success or failure
    Example   : rv = dba.del_protein_xrefs(42, 'Ensembl')
    Scope     : Public
    Comments  :
    '''
    if not id:
      self.warning("No protein_id sent to del_protein_xrefs(): ")
      return False
    if xtype:
      sql = "DELETE FROM xref WHERE protein_id = %s AND xtype = %s"
      params = (id, xtype)
      self._logger.debug("SQLpat: %s"%sql)
      self._logger.debug("SQLparams: %d, %s"%params)
    else:
      sql = "DELETE FROM xref WHERE protein_id = %s"
      params = (id,)
      self._logger.debug("SQLpat: %s"%sql)
      self._logger.debug("SQLparams: %d"%params)

    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
        self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        msg = "MySQL Error: %s" % str(e)
        #self.error(msg)
        self._logger.error(msg)
        return False
    return True

  def del_protein_tdl_infos(self, id, itype=False):
    '''
    Function  : Delete tdl_infos for a given protein
    Arguments : A protein id and an optional itype
    Returns   : Boolean indicating success or failure
    Example   : rv = dba.del_protein_tdl_infos(42, 'PubMed Count')
    Scope     : Public
    Comments  :
    '''
    if not id:
      self.warning("No protein_id sent to del_protein_tdl_infos(): ")
      return False
    if itype:
      sql = "DELETE FROM tdl_info WHERE protein_id = %s AND itype = %s"
      params = (id, itype)
      self._logger.debug("SQLpat: %s"%sql)
      self._logger.debug("SQLparams: %d, %s"%params)
    else:
      sql = "DELETE FROM tdl_info WHERE protein_id = %s"
      params = (id,)
      self._logger.debug("SQLpat: %s"%sql)
      self._logger.debug("SQLparams: %d"%params)

    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
        self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        msg = "MySQL Error: %s" % str(e)
        #self.error(msg)
        self._logger.error(msg)
        return False
    return True

  def del_protein_expressions(self, id, etype=False):
    '''
    Function  : Delete expression(s) for a given protein
    Arguments : A protein id and an optional etype
    Returns   : Boolean indicating success or failure
    Example   : rv = dba.del_protein_expressions(42, 'UniProt Tissue Specificity')
    Scope     : Public
    Comments  :
    '''
    if not id:
      self.warning("No protein_id sent to del_protein_expressions(): ")
      return False
    if etype:
      sql = "DELETE FROM expression WHERE protein_id = %s AND etype = %s"
      params = (id, etype)
      self._logger.debug("SQLpat: %s"%sql)
      self._logger.debug("SQLparams: %d, %s"%params)
    else:
      sql = "DELETE FROM expression WHERE protein_id = %s"
      params = (id,)
      self._logger.debug("SQLpat: %s"%sql)
      self._logger.debug("SQLparams: %d"%params)

    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
        self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        msg = "MySQL Error: %s" % str(e)
        #self.error(msg)
        self._logger.error(msg)
        return False
    return True

  def del_generifs(self, protein_id):
    '''
    Function  : Delete generifs for a given protein
    Arguments : A protein id
    Returns   : Boolean indicating success or failure
    Example   : rv = dba.del_generifs(42)
    Scope     : Public
    Comments  :
    '''
    if protein_id:
      sql = "DELETE FROM generif WHERE protein_id = %s"
      params = (protein_id,)
    else:
      self.warning("No protein_id sent to del_genefifs(): ")
      return False
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %d"%params)

    with closing(self._conn.cursor()) as curs:
      try:
        rv = curs.execute(sql, params)
        self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        msg = "MySQL Error: %s" % str(e)
        #self.error(msg)
        self._logger.error(msg)
        return False
    return True

  def del_goas(self, protein_id):
    '''
    Function  : Delete goas for a given protein
    Arguments : A protein id
    Returns   : Boolean indicating success or failure
    Example   : rv = dba.del_goas(42)
    Scope     : Public
    Comments  :
    '''
    if protein_id:
      sql = "DELETE FROM goa WHERE protein_id = %s"
      params = (protein_id,)
    else:
      self.warning("No protein_id sent to del_goas(): ")
      return False
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %d"%params)

    with closing(self._conn.cursor()) as curs:
      try:
        rv = curs.execute(sql, params)
        self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        msg = "MySQL Error: %s" % str(e)
        #self.error(msg)
        self._logger.error(msg)
        return False
    return True

  def del_target(self, id):
    '''
    Function  : Delete a target and all associated data
    Arguments : A target id
    Returns   : Boolean indicating success or failure
    Example   : rv = dba.del_target(42)
    Scope     : Public
    Comments  :
    '''
    if not id:
      self.warning("No id sent to del_target(): ")
      return False

    sql = "SELECT protein_id FROM t2tc WHERE target_id = %s"
    params = (id,)
    pids = []
    with closing(self._conn.cursor()) as curs:
      curs.execute(sql, params)
      for row in curs:
        pids.append(row[0])
    sql = "DELETE FROM target WHERE id = %s"
    params = (id,)
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %d"%params)
    with closing(self._conn.cursor()) as curs:
      try:
        rv = curs.execute(sql, params)
        self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        msg = "MySQL Error: %s" % str(e)
        #self.error(msg)
        self._logger.error(msg)
        return False
    sql = "DELETE FROM protein WHERE id = %s"
    self._logger.debug("SQLpat: %s"%sql)
    for pid in pids:
      params = (pid,)
      self._logger.debug("SQLparams: %d"%params)
      with closing(self._conn.cursor()) as curs:
        try:
          rv = curs.execute(sql, params)
          self._conn.commit()
        except mysql.Error, e:
          self._conn.rollback()
          msg = "MySQL Error: %s" % str(e)
          #self.error(msg)
          self._logger.error(msg)
          return False
    return True

  def del_target_tdl_infos(self, tid, itype=False):
    '''
    Function  : Delete tdl_infos for a given target
    Arguments : A target id and an optional itype
    Returns   : Boolean indicating success or failure
    Example   : rv = dba.del_target_tdl_infos(42, 'DrugDB Count')
    Scope     : Public
    Comments  :
    '''
    if not tid:
        self.warning("No target_id sent to del_target_tdl_infos(): ")
        return False
    if itype:
        sql = "DELETE FROM tdl_info WHERE target_id = %s AND itype = %s"
        params = (tid, itype)
        self._logger.debug("SQLpat: %s"%sql)
        self._logger.debug("SQLparams: %d, %s"%params)
    else:
        sql = "DELETE FROM tdl_info WHERE target_id = %s"
        params = (tid,)
        self._logger.debug("SQLpat: %s"%sql)
        self._logger.debug("SQLparams: %d"%params)

    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
        self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        msg = "MySQL Error: %s" % str(e)
        #self.error(msg)
        self._logger.error(msg)
        return False
    return True

  def del_target_drug_activity(self, tid):
    '''
    Function  : Delete drug_activity for a given target
    Arguments : A target id
    Returns   : Boolean indicating success or failure
    Example   : rv = dba.del_target_drug_activity(42)
    Scope     : Public
    Comments  :
    '''
    if not tid:
      self.warning("No target_id sent to del_target_drug_activity(): ")
      return False
    sql = "DELETE FROM drug_activity WHERE target_id = %s"
    params = (tid,)
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %d"%params)

    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
        self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        msg = "MySQL Error: %s" % str(e)
        #self.error(msg)
        self._logger.error(msg)
        return False
    return True

  def del_target_cmpd_activity(self, tid):
    '''
    Function  : Delete cmpd_activity for a given target
    Arguments : A target id
    Returns   : Boolean indicating success or failure
    Example   : rv = dba.del_target_cmpd_activity(42)
    Scope     : Public
    Comments  :
    '''
    if not tid:
      self.warning("No target_id sent to del_target_cmpd_activity(): ")
      return False
    sql = "DELETE FROM cmpd_activity WHERE target_id = %s"
    params = (tid,)
    self._logger.debug("SQLpat: %s"%sql)
    self._logger.debug("SQLparams: %d"%params)

    with closing(self._conn.cursor()) as curs:
      try:
        curs.execute(sql, params)
        self._conn.commit()
      except mysql.Error, e:
        self._conn.rollback()
        msg = "MySQL Error: %s" % str(e)
        #self.error(msg)
        self._logger.error(msg)
        return False
    return True


  #
  # Private Methods
  #
  def _connect(self, host, port, db, user, passwd):
    '''
    Function  : Connect to database
    Arguments : N/A
    Returns   : N/A
    Scope     : Private
    Comments  : Database connection object is stored as private instance varibale
    '''
    self._conn = mysql.connect(host=host, port=port, db=db, user=user, passwd=passwd,
                               charset='utf8') #  init_command='SET NAMES UTF8'
    logging.info("Connection: %s" % self._conn)

  def _get_auth(self, pw_file):
    '''
    Function  : Get database password from a file.
    Arguments : Path to file
    Returns   : Database password
    Scope     : Private
    Comments  :
    '''
    f = open(pw_file, 'r')
    pw = f.readline().strip()
    return pw

  def _cache_info_types(self):
    if hasattr(self, '_info_types'):
        return
    else:
      with closing(self._conn.cursor()) as curs:
        curs.execute("SELECT name, data_type FROM info_type")
        self._info_types = {}
        for it in curs:
          k = it[0]
          t = it[1]
          if t == 'String':
            v = 'string_value'
          elif t == 'Integer':
            v = 'integer_value'
          elif t == 'Number':
            v = 'number_value'
          elif t == 'Boolean':
            v = 'boolean_value'
          elif t == 'Date':
            v = 'date_value'
          self._info_types[k] = v

  def _cache_xref_types(self):
    if hasattr(self, '_xref_types'):
        return
    else:
      with closing(self._conn.cursor()) as curs:
        curs.execute("SELECT name FROM xref_type")
        self._xref_types = []
        for xt in curs:
          self._xref_types.append(xt[0])

  def _cache_expression_types(self):
    if hasattr(self, '_expression_types'):
        return
    else:
      with closing(self._conn.cursor()) as curs:
        curs.execute("SELECT name, data_type FROM expression_type")
        self._expression_types = {}
        for ex in curs:
          k = ex[0]
          t = ex[1]
          if t == 'String':
            v = 'string_value'
          elif t == 'Number':
            v = 'number_value'
          elif t == 'Boolean':
            v = 'boolean_value'
          self._expression_types[k] = v

  def _cache_phenotype_types(self):
    if hasattr(self, '_gene_phenotype_types'):
        return
    else:
      with closing(self._conn.cursor()) as curs:
        curs.execute("SELECT name FROM phenotype_type")
        self._phenotype_types = []
        for row in curs:
          self._phenotype_types.append(row[0])

  def _cache_gene_attribute_types(self):
    if hasattr(self, '_gene_attribute_types'):
        return
    else:
      with closing(self._conn.cursor()) as curs:
        curs.execute("SELECT id, name FROM gene_attribute_type")
        self._gene_attribute_types = {}
        for row in curs:
          self._gene_attribute_types[row[1]] = row[0]


def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])

if __name__ == '__main__':
  #dba = DBAdaptor({'dbname': 'tcrdev', 'dbname': 'tcrdev', 'loglevel': logging.DEBUG, 'logfile': './TCRD-DBA.log'})
  #dba = DBAdaptor({'dbname': 'tcrdev', 'dbname': 'tcrdev', 'loglevel': logging.DEBUG})
  #dba.test()
  #dbi = dba.get_dbinfo()
  #print( "DBInfo: %s\n" % dbi )

  dba = DBAdaptor({'dbname': 'tcrdev'})

  # print( "\nTotal number of targets: %d" % dba.get_target_count(idg=False) )
  # print( "Number of IDG targets: %d" % dba.get_target_count() )
  # print( "Number of GPCR targets: %d" % dba.get_target_count(family='GPCR') )

  #print( "\nNumber of Tdark targets: %d" % dba.get_tdl_target_count('Tdark', idg=False) )
  #print( "Number of Tdark IDG targets: %d" % dba.get_tdl_target_count('Tdark') )
  #print( "Number of Tdark GPCR targets: %d" % dba.get_tdl_target_count('Tdark', family='GPCR') )

  #print( dba.get_info_types() )

  # tid = 42
  # target = dba.get_target(tid)
  # if target:
  #   print( json.dumps(target, sort_keys=True, indent=2) )
  #   #for k,v in target.items():
  #   #  print( k,':', v )
  # else:
  #   print( "No target with id", tid )

  # Find target(s) by xref
  targets = dba.find_targets_by_xref({'xtype': 'Ensembl', 'value': 'ENSP00000000233'}, idg=False)
  if targets:
    for t in targets:
      print( json.dumps(t, sort_keys=True, indent=2) )
  else:
    print( "No target(s) with xref Ensembl:ENSP00000000233" )

  # print( "IDG Family targets in TCRD: %s" % dba.get_target_count() )

  # print( "\nTgray Nuclear Receptors:" )
  # for target in dba.get_tdl_targets('Tgray', family='NR'):
  #   print( target['name'] )

  # start_time = time.time()
  # ct = 0
  # for target in dba.get_targets(idg=False, include_annotations=True):
  #   ct += 1
  # elapsed = time.time() - start_time
  # print( "\n%d targets processed. Elapsed time: %s" % (ct, secs2str(elapsed)) )
