#!/usr/bin/env python
# Time-stamp: <2020-03-12 11:30:26 smathias>
"""
"""
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2020, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "1.0.0"

import os,sys,time
import csv
from collections import defaultdict
import slm_tcrd_functions as slmf

PROGRAM = os.path.basename(sys.argv[0])
INFILES = { 'v1': '../data/TDLevol/TCRDv1.5.8_TDLs.csv',
            'v2': '../data/TDLevol/TCRDv2.4.2_TDLs.csv',
            'v3': '../data/TDLevol/TCRDv3.1.5_TDLs.csv',
            'v4': '../data/TDLevol/TCRDv4.1.0_TDLs.csv',
            'v5': '../data/TDLevol/TCRDv5.4.4_TDLs.csv',
            'v6': '../data/TDLevol/TCRDv6.4.0_TDLs.csv' }
TDLEvol = defaultdict(dict)
UP2Sym = defaultdict(dict)
OUTFILE = '../data/TDLevol/TDLEvol.csv'

def main():
  for ver,fn in INFILES.items():
    line_ct = slmf.wcl(fn)
    print "\nProcessing {} lines in file {}".format(line_ct, fn)
    ct = 0
    with open(fn, 'r') as ifh:
      csvreader = csv.reader(ifh)
      for row in csvreader:
        # name, uniprot, sym, geneid, tdl
        ct += 1
        up = row[1]
        sym = row[2]
        tdl = row[4]
        TDLEvol[up][ver] = tdl
        UP2Sym[up] = sym
    print "{} lines processed.".format(ct)
    print "{} entries now in TDLEvol.".format(len(TDLEvol))

    ct = 0
    header = ['UniProt', 'HGNC Symbol', 'v1 TDL', 'v2 TDL', 'v3 TDL', 'v4 TDL', 'v5 TDL', 'v6 TDL']
    ct += 1
    with open(OUTFILE, 'w') as csvout:
      csvwriter = csv.writer(csvout, quotechar='"', quoting=csv.QUOTE_MINIMAL)
      csvwriter.writerow(header)
      for up,tdld in TDLEvol.items():
        outrow = [up, UP2Sym[up]]
        for ver in ['v1', 'v2', 'v3', 'v4', 'v5', 'v6']:
          if ver in tdld:
            outrow.append(tdld[ver])
          else:
            outrow.append('')
        csvwriter.writerow(outrow)
        ct += 1
    print "\nWrote {} line to output file {}.".format(ct, OUTFILE)
  return True


if __name__ == '__main__':
  print "\n{} (v{}) [{}]:".format(PROGRAM, __version__, time.strftime("%c"))
  start_time = time.time()
  main()
  elapsed = time.time() - start_time
  print "\n{}: Done. Elapsed time: {}\n".format(PROGRAM, slmf.secs2str(elapsed))
