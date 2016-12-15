#!/usr/bin/env python
"""
A parser for OBO format files.

This parser is a quick and dirty implementation developed and tested to
parse a few OBO files. For example, it works on the evidenceontology
eco.obo and Disease Ontology doid.obo files. It may, or more likely may
not, work on other OBO files.

Usage example::

    >>> import obo
    >>> parser = obo.Parser(open("eco.obo"))
    >>> eco = {}
    >>> for stanza in parser:
    >>>     eco[stanza.tags["id"][0]] = stanza.tags

"""
__author__    = "Steve Mathias"
__email__     = "smathias @salud.unm.edu"
__org__       = "Translational Informatics Division, UNM School of Medicine"
__copyright__ = "Copyright 2015, Steve Mathias"
__license__   = "Creative Commons Attribution-NonCommercial (CC BY-NC)"
__version__   = "0.1.0"
__all__ = ["ParseError", "Stanza", "Parser", "Value"]

from cStringIO import StringIO
import re
import tokenize
from slm_utils import open_anything
from slm_utils import ParseError

class Value(object):
  """Class representing an OBO value and its modifiers.

  This class has two member variables:
    'value' is the value itself
    'modifiers' is a tuple of the corresponding modifiers. These are not
    parsed in any way.
  """

  __slots__ = ["value", "modifiers"]

  def __init__(self, value, modifiers=()):
    self.value = str(value)
    if modifiers:
      self.modifiers = tuple(modifiers)
    else:
      self.modifiers = None

  def __str__(self):
    """Returns the value itself (without modifiers)"""
    return str(self.value)

  def __repr__(self):
    """Returns a Python representation of this object"""
    return "%s(%r, %r)" % (self.__class__.__name__, self.value, self.modifiers)


class Stanza(object):
  """Class representing an OBO stanza.

  An OBO stanza looks like this::

    [name]
    tag: value
    tag: value
    tag: value

  Values may optionally have modifiers, see the OBO specification
  for more details. This class has two member variables:
  stores the stanza name in the
  'name' is the stanza name
  'tags' is a dict of tag: list(value(s)) pairs. This is because
  theoretically there could be more than a single value associated
  to a tag in the OBO file format.
  Given a valid stanza, you can do stuff like this:

    >>> stanza.name
    "Term"
    >>> print stanza.tags["id"]
    ['ECO:0000001']
    >>> print stanza.tags["name"]
    ['evidence']
  """

  __slots__ = ["name", "tags"]

  def __init__(self, name, tags=None):
    self.name = name
    if tags:
      self.tags = dict(tags)
    else:
      self.tags = dict()

  def __repr__(self):
    """Returns a Python representation of this object"""
    return "%s(%r, %r)" % (self.__class__.__name__, self.name, self.tags)


class Parser(object):
  """The OBO parser class."""

  def __init__(self, file_handle):
    """Creates an OBO parser that reads the given file-like object.
    If you want to create a parser that reads an OBO file, do this:

      >>> import obo
      >>> parser = obo.Parser(open("eco.obo"))

    Only the headers are read when creating the parser. You can
    access these right after construction as follows:

      >>> parser.headers["format-version"]
          ['1.2']

    To read the stanzas in the file, you must iterate over the
    parser. The iterator yields Stanza objects.
    """
    self.file_handle = open_anything(file_handle)
    self.line_re = re.compile(r"\s*(?P<tag>[^:]+):\s*(?P<value>.*)")
    self.lineno = 0
    self.headers = {}
    self._extra_line = None
    self._read_headers()

  def _lines(self):
    """Iterates over the lines of the file, removing
    comments and trailing newlines and merging multi-line
    tag-value pairs into a single line"""
    while True:
      self.lineno += 1
      line = self.file_handle.readline()
      if not line:
        break
    
      line = line.strip()
      if not line:
        yield line
        continue

      if line[0] == '!':
        continue
      if line[-1] == '\\':
        # This line is continued in the next line
        lines = [line[:-1]]
        finished = False
        while not finished:
          self.lineno += 1
          line = self.file_handle.readline()
          if line[0] == '!':
            continue
          line = line.strip()
          if line[-1] == '\\':
            lines.append(line[:-1])
          else:
            lines.append(line)
            finished = True
        line = " ".join(lines)
      else:
        in_quotes = False
        escape = False
        comment_char_index = None
        for index, char in enumerate(line):
          if escape:
            escape = False
            continue
          if char == '"':
            in_quotes = not in_quotes
          elif char == '\\' and in_quotes:
            escape = True
          elif char == '!' and not in_quotes:
            comment_char_index = index
            break
        if comment_char_index is not None:
          line = line[0:comment_char_index].strip()
          
      yield line

  def _parse_line(self, line):
    """Parses a single line consisting of a tag-value pair
    and optional modifiers. Returns the tag name and the
    value as a Value object."""
    match = self.line_re.match(line)
    if not match:
      return False
    tag, value_and_mod = match.group("tag"), match.group("value")

    # If the value starts with a quotation mark, we parse it as a
    # Python string -- luckily this is the same as an OBO string
    if value_and_mod and value_and_mod[0] == '"':
      gen = tokenize.generate_tokens(StringIO(value_and_mod).readline)
      for toknum, tokval, _, (_, ecol), _ in gen:
        if toknum == tokenize.STRING:
          value = eval(tokval)
          mod = (value_and_mod[ecol:].strip(), )
          break
        raise ParseError("cannot parse string literal", self.lineno)
    else:
      value = value_and_mod
      mod = None

    value = Value(value, mod)
    return tag, value

  def _read_headers(self):
    """Reads the headers from the OBO file"""
    for line in self._lines():
      if not line or line[0] == '[':
        # We have reached the end of headers
        self._extra_line = line
        return
      key, value = self._parse_line(line)
      if key in self.headers:
        self.headers[key].append(value.value)
      else:
        self.headers[key] = [value.value]

  def stanzas(self):
    """Iterates over the stanzas in this OBO file,
    yielding a Stanza object for each stanza."""
    stanza = None
    if self._extra_line and self._extra_line[0] == '[':
      stanza = Stanza(self._extra_line[1:-1])
    for line in self._lines():
      if not line:
        continue
      if line[0] == '[':
        if stanza:
          yield stanza
        stanza = Stanza(line[1:-1])
        continue
      tag, value = self._parse_line(line)
      try:
        stanza.tags[tag].append(value)
      except KeyError:
        stanza.tags[tag] = [value]

  def __iter__(self):
    return self.stanzas()


def test():
  test_file = '/home/app/TCRD/data/eco.obo'
  print "Parsing file", test_file
  parser = Parser(test_file)
  ct = 0
  for _ in parser:
    ct += 1
    if ct % 100 == 0:
      print "  %d stanzas processed" % ct
  print "Successfully parsed %d stanzas" % ct


if __name__ == "__main__":
  import sys
  sys.exit(test())
