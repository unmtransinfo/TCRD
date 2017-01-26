#!/usr/bin/env python
# Time-stamp: <2017-01-13 11:57:41 smathias>
"""Load IDG Phase 2 flags into TCRD.

Usage:
    load-IDG2Flags.py [--debug=<int> | --quiet] [--dbhost=<str>] [--dbname=<str>] [--logfile=<file>] [--loglevel=<int>]
    load-IDG2Flags.py | --help

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
  -d --debug DEBUGL    : set debugging output level (0-3) [default: 0]
  -? --help            : print this message and exit 
"""
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2016-2017, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "2.0.0"

import sys
from docopt import docopt
from TCRD import DBAdaptor
import logging
from progressbar import *

PROGRAM = os.path.basename(sys.argv[0])
IDG2 = set(['PRKAG1', 'PRKAB1', 'ADCK2', 'ADCK5', 'ALPK3', 'COQ8B', 'ALPK2', 'BCKDK', 'CAMKV', 'CDKL3', 'CDKL4', 'CDKL1', 'CDKL2', 'CDK15', 'CDK17', 'CDK11B', 'CDK14', 'CDK18', 'CLK4', 'CDK10', 'CLK3', 'CSNK2A2', 'DGKH', 'DYRK3', 'DYRK1B', 'DYRK4', 'EEF2K', 'DYRK2', 'ERN2', 'FASTK', 'GK2', 'HIPK4', 'ITPKA', 'CSNK1G3', 'CSNK1G2', 'PRKACG', 'CSNK1G1', 'ITPK1', 'PSKH2', 'CAMK1D', 'TK2', 'PRKACB', 'PNCK', 'CAMK1G', 'CAMKK1', 'PSKH1', 'PHKA1', 'RPS6KC1', 'PRKCQ', 'LMTK3', 'MARK4', 'MAST3', 'LRRK1', 'MAP3K14', 'LTK', 'MAP3K10', 'MAST4', 'MAST2', 'MAPK15', 'MAPK4', 'MKNK2', 'CDC42BPG', 'CDC42BPB', 'NEK11', 'NEK5', 'NEK10', 'NIM1K', 'NEK4', 'NEK6', 'NRK', 'NEK7', 'SCYL1', 'NRBP2', 'PIK3C2G', 'PAK5', 'PANK3', 'PIK3C2B', 'PAK3', 'PAK6', 'SCYL3', 'PDIK1L', 'PIP4K2C', 'PIP5K1A', 'PLK5', 'PHKG1', 'PHKG2', 'PI4KA', 'PIP5K1B', 'PKMYT1', 'PKN3', 'PRPF4B', 'TP53RK', 'PRKRA', 'PRKY', 'PXK', 'RIOK1', 'RIOK3', 'RPS6KL1', 'SBK2', 'SCYL2', 'SBK3', 'SGK494', 'POMK', 'SGK223', 'SRPK3', 'STK32C', 'STK33', 'STK32B', 'STK40', 'STK17A', 'STK36', 'STK32A', 'STK38L', 'STKLD1', 'STK3', 'STK31', 'TESK2', 'TESK1', 'TBCK', 'TLK1', 'TPK1', 'TLK2', 'TSSK6', 'TSSK1B', 'TTBK2', 'TSSK4', 'TTBK1', 'TSSK3', 'UCK1', 'ULK4', 'UCK2', 'WNK2', 'VRK2', 'WEE2', 'HTR3B', 'HTR3E', 'HTR3D', 'CHRNB2', 'HTR3C', 'CHRND', 'CHRNB1', 'CHRNA10', 'CHRNA2', 'CHRNA9', 'CHRNG', 'ASIC4', 'ASIC5', 'BEST4', 'CACNA2D1', 'CACNA2D3', 'CACNA2D4', 'CACNB1', 'CACNB2', 'CACNB3', 'CACNA2D2', 'CACNG6', 'CACNA1F', 'CACNB4', 'CACNG1', 'CACNG5', 'CACNG3', 'CACNG7', 'CACNG4', 'CACNG8', 'CLCNKA', 'CLIC6', 'CLIC2', 'CLCA4', 'CLCC1', 'CLCA3P', 'CNGA4', 'CLCN6', 'CLIC5', 'CLCA2', 'CLIC3', 'CATSPER4', 'CATSPER2', 'FAM26F', 'FAM26D', 'FAM26E', 'FXYD3', 'FXYD7', 'FXYD6P3', 'GABRA6', 'GABRG3', 'GABRR3', 'GABRB1', 'GABRG1', 'GABRP', 'GABRA5', 'GABRR1', 'GPR89A', 'GLRA3', 'GLRA4', 'GLRB', 'GPR89A', 'GRID1', 'GRIK3', 'HCN3', 'KCND1', 'KCNK4', 'KCNK7', 'KCNS1', 'KCNS2', 'KCNIP1', 'KCNJ15', 'KCNMB4', 'KCNK16', 'ITPR2', 'KCNH6', 'KCNH7', 'KCNH8', 'KCNK12', 'KCNMB3', 'KCNA6', 'KCNG2', 'KCNN1', 'KCNAB2', 'KCNIP4', 'KCNC4', 'KCNG3', 'KCNH4', 'KCNS3', 'KCNAB3', 'KCNG4', 'KCNA7', 'KCNT1', 'KCNJ14', 'KCNJ18', 'KCNV1', 'LRRC52', 'LRRC55', 'LRRC38', 'PANX3', 'PANX2', 'PLLP', 'PKD1L2', 'PKD2L2', 'PKD1L3', 'SLC26A1', 'SCN3B', 'SCN7A', 'SCNN1D', 'SCN2B', 'SCNN1B', 'TMC5', 'TMC7', 'TMEM38B', 'TMC3', 'TMC4', 'TTYH2', 'TTYH1', 'HTR1E', 'HTR5A', 'ADGRD1', 'ADGRE2', 'ADGRF5', 'ADGRG4', 'ADGRG7', 'ADGRB2', 'ADGRF2', 'ADGRF4', 'CHRM5', 'ADGRF1', 'ADGRG3', 'ADGRG5', 'ADGRD2', 'ADGRE1', 'ADGRE3', 'ADGRF3', 'ADGRG2', 'ADGRB3', 'ADGRA1', 'ADGRE4P', 'ADGRL3', 'CELSR2', 'GPR137', 'FZD10', 'GPR32P1', 'GALR3', 'GPR139', 'GPR149', 'GPR171', 'GPR174', 'GPR142', 'GPR151', 'GPR156', 'GPRC5D', 'GPR153', 'GPR33', 'GPR25', 'GPR45', 'GPR75', 'GPR88', 'GNRHR2', 'GPR150', 'GPR18', 'GPR62', 'GPR82', 'GPR87', 'GPR101', 'GPR173', 'GPRC5C', 'GPR32', 'GPR63', 'GPRC5B', 'GPR12', 'GPR135', 'GPR141', 'GPR146', 'GPR152', 'GPR157', 'GPR160', 'GPR42', 'GPR52', 'GPR143', 'GPR162', 'GPR26', 'GPR21', 'GPR61', 'GPR20', 'GPR27', 'GPR31', 'GPR34', 'GPR39', 'GPR4', 'GPR6', 'GPR78', 'GPR85', 'GPR19', 'GPR22', 'HCAR1', 'HCAR3', 'MAS1L', 'LPAR6', 'MRGPRX4', 'MRGPRG', 'MRGPRX2', 'MTNR1A', 'MRGPRE', 'MRGPRX3', 'NPBWR1', 'NPBWR2', 'NPY6R', 'NPY2R', 'NPY5R', 'OPN1MW2', 'OXGR1', 'P2RY10', 'OXER1', 'RRH', 'P2RY11', 'PROKR1', 'QRFPR', 'GPRC5A', 'RXFP3', 'RXFP4', 'S1PR4', 'SSTR4', 'SUCNR1', 'TAS2R31', 'TAS2R14', 'TAAR3', 'TAS2R10', 'TAS2R41', 'TAS2R43', 'TAS2R50', 'TAAR2', 'TAAR8', 'TAS2R19', 'TAS2R7', 'TAS2R9', 'TAS2R13', 'TAS2R20', 'TAS2R40', 'TAS2R60', 'TAS2R3', 'TAS2R4', 'TAS2R5', 'TAS2R16', 'TAS2R8', 'TAAR9', 'TAS2R39', 'TAS2R1', 'TAS2R30', 'TAS2R42', 'TAS2R46', 'TPRA1', 'AVPR1B', 'VN1R17P', 'VN1R3', 'VN1R5', 'VN1R1', 'VN1R4', 'VN1R2'])

def load():
  args = docopt(__doc__, version=__version__)
  debug = int(args['--debug'])
  if debug:
    print "\n[*DEBUG*] ARGS:\n%s\n"%repr(args)
    
  loglevel = int(args['--loglevel'])
  if args['--logfile']:
    logfile = args['--logfile']
  else:
    logfile = "%s.log" % PROGRAM
  logger = logging.getLogger(__name__)
  logger.setLevel(loglevel)
  if not debug:
    logger.propagate = False # turns off console logging when debug is 0
  fh = logging.FileHandler(logfile)
  fmtr = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
  fh.setFormatter(fmtr)
  logger.addHandler(fh)

  dba_params = {'dbhost': args['--dbhost'], 'dbname': args['--dbname'], 'logger_name': __name__}
  dba = DBAdaptor(dba_params)
  dbi = dba.get_dbinfo()
  logger.info("Connected to TCRD database %s (schema ver %s; data ver %s)", args['--dbname'], dbi['schema_ver'], dbi['data_ver'])
  if not args['--quiet']:
    print "Connected to TCRD database %s (schema ver %s; data ver %s)" % (args['--dbname'], dbi['schema_ver'], dbi['data_ver'])
  
  # Dataset
  dataset_id = dba.ins_dataset( {'name': 'IDG Phase 2 Flags', 'source': 'IDG-KMC generated data by Steve Mathias at UNM.', 'app': PROGRAM, 'app_version': __version__, 'comments': 'Flags set from list of targets in the RFA.'} )
  if not dataset_id:
    print "WARNING: Error inserting dataset See logfile %s for details." % logfile
    sys.exit(1)
  # Provenance
  rv = dba.ins_provenance({'dataset_id': dataset_id, 'table_name': 'target', 'column_name': 'idg2'})
  if not rv:
    print "WARNING: Error inserting provenance. See logfile %s for details." % logfile
    sys.exit(1)

  pbar_widgets = ['Progress: ', Percentage(), ' ', Bar(marker='#',left='[',right=']'), ' ', ETA()]
  tct = len(IDG2)
  print '\nLoading IDG Phase 2 flags for {} gene symbols'.format(tct)
  pbar = ProgressBar(widgets=pbar_widgets, maxval=tct).start()
  notfnd = []
  multfnd = []
  ct = 0
  upd_ct = 0
  dba_err_ct = 0
  for sym in IDG2:
    ct += 1
    targets = dba.find_targets({'sym': sym}, idg=False, include_annotations=False)
    if not targets:
      notfnd.append(sym)
      continue
    if len(targets) > 1:
      multfnd.append(sym)
    for t in targets:
      rv = dba.upd_target(t['id'], 'idg2', 1)
      if rv:
        upd_ct += 1
      else:
        dba_err_ct += 1
    pbar.update(ct)
  pbar.finish()

  print "{} symbols processed".format(ct)
  print "{} targets updated with IDG2 flags".format(upd_ct)
  if notfnd:
    print "No target found for %d symbols: %s" % (len(notfnd), ", ".join(notfnd))
  if multfnd:
    print "Multiple targets found for %d symbols: %s" % (len(multfnd), ", ".join(multfnd))
  if dba_err_ct > 0:
    print "WARNING: %d database errors occured. See logfile %s for details." % (dba_err_ct, logfile)
  

def secs2str(t):
  return "%d:%02d:%02d.%03d" % reduce(lambda ll,b : divmod(ll[0],b) + ll[1:], [(t*1000,),1000,60,60])

if __name__ == '__main__':
  print "\n%s (v%s) [%s]:\n" % (PROGRAM, __version__, time.strftime("%c"))
  start_time = time.time()
  load()
  elapsed = time.time() - start_time
  print "\n%s: Done. Elapsed time: %s\n" % (PROGRAM, secs2str(elapsed))

