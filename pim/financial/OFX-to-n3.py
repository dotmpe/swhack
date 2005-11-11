#!/usr/bin/python
"""fromOFX.py -- interpret OFX format as RDF

USAGE:
  python fromOFX.py  [options]  foo.ofx > foo.rdf

  options:
    --base uri
    --noprotocol    Supress SEQUENCE and DTSTAMP
    --noalarm       Supress VALARMs

REFERENCES

 

  Python Style Guide
  Author: Guido van Rossum
  http://www.python.org/doc/essays/styleguide.html

  
LICENSE

Workspace: http://www.w3.org/2000/10/swap/pim/financial/

Copyright 2002-2003 World Wide Web Consortium, (Massachusetts
Institute of Technology, European Research Consortium for
Informatics and Mathematics, Keio University). All Rights
Reserved. This work is distributed under the W3C(R) Software License
  http://www.w3.org/Consortium/Legal/2002/copyright-software-20021231
in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR
A PARTICULAR PURPOSE.


"""

__version__ = "$Id$"


from warnings import warn
import codecs, quopri


UID_PREFIX = 'uid:'  # Must Be absolute. (Was '#' - timbl) ('uuid:' ?)

from swap.myStore import load, Namespace
from swap.diag import chatty_flag, progress

import sys

def main():
    fyi("Reading OFX document")
    doc = sys.stdin.read()
    fyi("Parsing OFX document")
    contentLines(doc)

def fyi(s):
    pass
#    sys.stderr.write(s+"\n")
    
CR = chr(13)
LF = chr(10)
CRLF = CR + LF
SPACE = chr(32)
TAB = chr(9)

def contentLines(doc):
    "Process the content as a singel buffer"
    version = "$Id$"[1:-1]
    print """# Generated by %s""" % version
    print """@prefix ofx: <http://www.w3.org/2000/10/swap/pim/ofx#>.
@prefix ofxh: <http://www.w3.org/2000/10/swap/pim/ofx-headers#>.

<> ofxh:headers [
"""

    for ch in doc:
	if ch in CRLF: break  # Find delimiter used in the file
    if ch == CR and LF in doc: ch = CRLF
    lines = doc.split(ch)
    header = {}
    stack = []
    ln = 0
    while 1:
	ln = ln + 1
	line = lines[ln]
	colon = line.find(":")
	if colon < 0:
	    if line == "": break #
	    raise SyntaxError("No colon in header line, line %i: %s" % (
						ln, line))
	hname, value = line[:colon], line[colon+1:]
#	fyi("Header line %s:%s" % (hname, value))
	print "  ofxh:%s \"%s\";" % (hname, value)  #@@ do n3 escaping
	header[hname] = value
    print "];\n"
    
    assert header["ENCODING"] == "USASCII"  # Our assumption
    
    while ln+1 < len(lines):
	ln = ln + 1
	line = lines[ln]
	if line == "": continue # Possible on last line
	if line[0] != "<": raise SyntaxError("No < on line %i: %s" %(
				ln, line))
	i = line.find(">")
	if i < 0: raise SyntaxError("No > on line %i: %s" %(
				ln, line))
	tag = line[1:i]
	if line[1] == "/": # End tag
	    tag = tag[1:]
	    tag2 = stack.pop()
	    if tag != tag2: raise SyntaxError(
		"Found </%s> when </%s> expected.\nStack: %s" % 
		(tag, tag2, stack))
	    print "%s];  # %s" % ("  "*len(stack), tag)
	elif line[i+1:] == "":  # Start tag
	    print "%s ofx:%s [" %("  "*len(stack), tag)
	    stack.append(tag)
	else:  #  Data tag
	    print  "%s ofx:%s \"%s\";" % ("  "*len(stack), tag, line[i+1:])
	    
    if stack: raise SyntaxError("Unclosed tags: %s" % stack)
    print "."
    

def _test():
    import sys
    from pprint import pprint
    import doctest, fromOFX
    doctest.testmod(fromOFX)

    lines = contentLines(open(sys.argv[1]))
    #print lines
    c, lines = findComponents(lines)
    assert lines == []
    pprint(c)
    #unittest.main()

if __name__ == '__main__':
    import sys
    if sys.argv[1:2] == ['--test']:
        del sys.argv[1]
        _test()
    else:
        main()



