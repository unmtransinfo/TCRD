#!/usr/bin/env python

import sys,time,re
import obo

PROGRAM = os.path.basename(sys.argv[0])
ECO_OBO_FILE = '../data/eco.obo'

def mk_eco_map():
  print "\nParsing Evidence Ontology file {}".format(ECO_OBO_FILE)
  parser = obo.Parser(ECO_OBO_FILE)
  eco = {}
  for stanza in parser:
    eco[stanza.tags['id'][0].value] = stanza.tags
  regex = re.compile(r'GOECO:([A-Z]{2,3})')
  eco_map = {}
  for e,d in eco.items():
    if not e.startswith('ECO:'):
      continue
    if 'xref' in d:
      for x in d['xref']:
        m = regex.match(x.value)
        if m:
          eco_map[e] = m.group(1)
  return eco_map
  

if __name__ == '__main__':
  print "\n%s (v%s) [%s]:" % (PROGRAM, __version__, time.strftime("%c"))
  start_time = time.time()
  eco = parse_eco()
  elapsed = time.time() - start_time
  print "\n%s: Done. Total elapsed time: %s\n" % (PROGRAM, slmf.secs2str(elapsed))
