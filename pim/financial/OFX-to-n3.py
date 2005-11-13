#!/usr/bin/python
"""OFX-to-n3.py -- interpret OFX format as RDF

Converts OFX format (as in downloaded back statements etc
USAGE:
  python fromOFX.py < foo.ofx > foo.rdf
  
  The conversion is only syntactic.  The OFX modelling is
  pretty weel thought out, so taking it as defining an effecive
  RDF ontolofy seems to make sense. Rules can then be used to
  define mapping into your favorite ontology.
  
DESIGN NOTES
  
  The properties have even been left in upper
  case, although I wouldn't do that again next time.
  The SGML/XML tree is converted into a tree of blank nodes.
  This is made easier by the rule that OFX does not allow empty elements
  or mixed content.
    
  OFX actually defines a request-response protocol using HTTP and
  SGML (v1.*) or  XML (v2.*).
  I have only had access to downloaded statements which look like HTTP
  responses carrying SGML, so that is what this handles.

REFERENCES

This converts data from the  common proprietary format whcih seems
to be in use.  The spec i found is a later XML-based version, which will
be much simpler. Alas the spec not served directly on the web.
"Open" Financial Exchange
   Specification 2.0 
   April 28, 2000 (c) 2000 Intuit Inc., Microsoft Corp.
 
We try to stick to:
Python Style Guide
  Author: Guido van Rossum
  http://www.python.org/doc/essays/styleguide.html

   
LICENSE OF THIS CODE

Workspace: http://www.w3.org/2000/10/swap/pim/financial/

Copyright 2002-2003 World Wide Web Consortium, (Massachusetts
Institute of Technology, European Research Consortium for
Informatics and Mathematics, Keio University). All Rights
Reserved. This work is distributed under the W3C(R) Software License
  http://www.w3.org/Consortium/Legal/2002/copyright-software-20021231
in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR
A PARTICULAR PURPOSE.

This is or was http://www.w3.org/2000/10.swap/pim/financial/OFX-to-n3.py
"""

__version__ = "$Id$"
thisSource = "http://www.w3.org/2000/10.swap/pim/financial/OFX-to-n3.py"

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
	while " " in hname:
	    i = hname.find(" ")
	    hname = hname[:i] + hname[i+1:]
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



