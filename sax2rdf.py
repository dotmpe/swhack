#! /usr/bin/python
"""
  A parser for RDF/XML built on the sax2 interface;
  derived from a parser for RDF/XML built on the xmllib XML parser.

  To do: Passing on namesapce bindings!
       (dwc: @@huh?)
       (tbl: The bind call in the RDF stream API is used to pass
        on the prefixes found, as hints only for generating readable output code)

  - Add parsing of RDF bags

 parses DAML_ONT_NS or List_NS lists, generates List_NS

 References:

 Python/XML HOWTO
                The Python/XML Special Interest Group
                                   xml-sig@python.org 
                               (edited by amk1@bigfoot.com)
 http://py-howto.sourceforge.net/xml-howto/xml-howto.html

 http://www.megginson.com/SAX/applications.html#python.parsers
 http://www.python.org/sigs/xml-sig/

 How to on xmllib:
 http://www.python.org/doc/howto/xml/node7.html


 RDF grammar http://www.w3.org/TR/rdf-syntax-grammar/ esp sections 6 and 7
    
##################################### SAX pointers
 First hit on Python SAX parser
 http://www.gca.org/papers/xmleurope2000/papers/s28-04.html#N84395

 Howto use SAX in python:
 http://www.python.org/doc/howto/xml/SAX.html

"""

import string
import sys

import uripath
from why import BecauseOfData
import isXML
import diag
from webAccess import urlopenForRDF   # http://www.w3.org/2000/10/swap/

import xml.sax # PyXML stuff
               #   http://sourceforge.net/projects/pyxml
               # Connolly uses the debian python2-xml 0.6.5-2 package
               #  http://packages.debian.org/testing/interpreters/python2-xml.html
               # and suggests TimBL try the win32 distribution from
               # the PyXML sourceforge project
               # http://prdownloads.sourceforge.net/pyxml/PyXML-0.6.5.win32-py2.1.exe
               # TimBL points outhe does not use windows env't but cygwin and
               #   giuesses he should compile python2-xml for cygwin.
import xml.sax._exceptions
from xml.sax.handler import feature_namespaces

import RDFSink
from RDFSink import FORMULA,  ANONYMOUS, NODE_MERGE_URI

# States:

STATE_OUTERMOST =   "outermost level"     # Before <rdf:RDF>
STATE_NOT_RDF =     "not RDF"     # Before <rdf:RDF>
STATE_NO_SUBJECT =  "no context"  # @@@@@@@@@ use numbers for speed
STATE_DESCRIPTION = "Description (have subject)" #
STATE_LITERAL =     "within literal"
STATE_VALUE =       "plain value"
STATE_NOVALUE =     "no value"     # We already have an object, another would be error
STATE_LIST =        "within list"

RDF_NS_URI = "http://www.w3.org/1999/02/22-rdf-syntax-ns#" # As per the spec
RDF_Specification = "http://www.w3.org/TR/REC-rdf-syntax/" # Must come in useful :-)

DAML_ONT_NS = "http://www.daml.org/2000/10/daml-ont#"  # DAML early version
DPO_NS = "http://www.daml.org/2001/03/daml+oil#"  # DAML plus oil
OWL_NS = "http://www.w3.org/2002/07/owl#"   # OWL 

List_NS = RDF_NS_URI     # Changed 200308

XML_NS_URI = "http://www.w3.org/XML/1998/namespace"

from diag import verbosity, progress, tracking


_nextId = 0        # For generation of arbitrary names for anonymous nodes


coreSyntaxTerms = ['RDF', 'ID', 'about', 'parseType', 'resource', 'nodeID', 'datatype'] 
syntaxTerms = coreSyntaxTerms + ['Description', 'li']
oldTerms = ['aboutEach', 'aboutEachPrefix', 'bagID'] 

nodeElementExceptions = {}
for a in coreSyntaxTerms + oldTerms + ['li',]:
    nodeElementExceptions[RDF_NS_URI + a] = True
propertyElementExceptions = {}
for a in coreSyntaxTerms + oldTerms + ['Description',]:
    propertyElementExceptions[RDF_NS_URI + a] = True
propertyAttributeExceptions = {}
for a in syntaxTerms + oldTerms:
    propertyAttributeExceptions[RDF_NS_URI + a] = True


class RDFHandler(xml.sax.ContentHandler):
    """RDF Parser using SAX API for XML parsing
"""

    def __init__(self, sink, openFormula, thisDoc, baseURI=None, flags="", why=None):
        self.testdata = ""
	self.flags = flags
        self._stack =[]  # Stack of states
        self._nsmap = [] # stack of namespace bindings
	self._delayedStatement = None
        self.sink = sink
        self._thisDoc = thisDoc
	if baseURI != None: self._base = baseURI
	else: self._base = thisDoc
        self._state = STATE_OUTERMOST  # Maybe should ignore RDF outside <rdf:RDF>??
        if openFormula==None:
            self._context = sink.newFormula(thisDoc + "#_formula")
	else:
	    self._context = openFormula
        self._formula = self._context  # Root formula

	self._reason = why	# Why the parser w
	self._reason2 = None	# Why these triples
	if diag.tracking: self._reason2 = BecauseOfData(sink.newSymbol(thisDoc), because=self._reason)

        self._subject = None
        self._predicate = None
	self._datatype = None
	self._language = None
	self._nodeIDs = {}
        self._items = [] # for <rdf:li> containers
        self._genPrefix = uripath.join(thisDoc, "#_rdfxg")    # allow parameter override?
	self.sink.setGenPrefix(self._genPrefix)
        self._litDepth = 0
	self.merge = self.sink.newSymbol(NODE_MERGE_URI)
        self.sink.startDoc()
        version = "$Id$"
        self.sink.makeComment("RDF parsed by "+version[1:-1])

	if "D" in self.flags:  # Assume default namespace declaration
	    self.sink.setDefaultNamespace(self._thisDoc+"#")
	    self._nsmap = [ { "": "#"} ]


    def characters(self, data):
        if self._state == STATE_VALUE or \
           self._state == STATE_LITERAL:
            self.testdata = self.testdata + data
        

    def flush(self):
        data = self.testdata
        if data:
            self.testdata = ""
#            print '# flushed data:', `data`

    def processingInstruction(self, name, data):
        self.flush()
        #print 'processing:',name,`data`

    def uriref(self, str):
        """ Generate uri from uriref in this document
        unicode strings OK.
        """

        return uripath.join(self._base, str)

    def newBlankNode(self):
	columnNumber = self._p.getColumnNumber()
	lineNumber = self._p.getLineNumber()
	bnodeID = self._thisDoc + "#_L%iC%i" % (lineNumber, columnNumber)
	return self.sink.newBlankNode(self._context, uri=bnodeID,
				why=self._reason2) #for debugging: encode file/line info

    def idAboutAttr(self, attrs):  #MS1.0 6.5 also proprAttr 6.10
        """ set up subject and maybe context from attributes
        """
        self._subject = None
        self._state = STATE_DESCRIPTION
        self._items.append(0)
        properties = []
        
        for name, value in attrs.items():
            ns, ln = name
            if ns:
                if string.find("ID about aboutEachPrefix bagID type", ln)>0:
                    if ns != RDF_NS_URI:
                        print ("# Warning -- %s attribute in %s namespace not RDF NS." %
                               name, ln)
                        ns = RDF_NS_URI  # Allowed as per dajobe: ID, bagID, about, resource, parseType or type
                uri = (ns + ln)
            if ns == RDF_NS_URI or ns == None:   # Opinions vary sometimes none but RDF_NS is common :-(
                if ln == "ID":
                    if not isXML.isName(value):
                        raise  BadSyntax(sys.exc_info(), 'An ID must be a Name %s' % value)
                    if self._subject:
                        print "# oops - subject already", self._subject
                        raise BadSyntax(sys.exc_info(), ">1 subject")
                    self._subject = self.sink.newSymbol(self.uriref("#" + value))
                elif ln == "about":
                    if self._subject: raise BadSyntax(sys.exc_info(), ">1 subject")
                    self._subject = self.sink.newSymbol(self.uriref(value))
                elif ln == "nodeID":
                    if self._subject: raise BadSyntax(sys.exc_info(), ">1 subject")
                    if not isXML.isNCName(value):
                        raise  BadSyntax(sys.exc_info(), 'A nodeID must be a NCName %s' % value)
		    s = self._nodeIDs.get(value, None)
		    if s == None:
			s = self.newBlankNode()
			self._nodeIDs[value] = s
                    self._subject = s
                elif ln == "aboutEachPrefix":
                    if value == " ":  # OK - a trick to make NO subject
                        self._subject = None
                    else: raise ooops # can't do about each prefix yet
                elif ln == "bagID":
                    if not isXML.isName(value):
                        raise  BadSyntax(sys.exc_info(), 'A bagID must be a Name %s' % value)
                    c = self._context #@@dwc: this is broken, no?
                    self._context = FORMULA, self.uriref("#" + value) #@@ non-ascii
                elif ln == "parseType":
                    pass  #later - object-related
                elif ln == "resource":
                    pass  #later
                elif ln == "datatype":
                    pass  #later
                else:
                    if not ns:
                        if "L" not in self.flags:  # assume local?
			    raise BadSyntax(sys.exc_info(), "No namespace on property attribute %s" % ln)
			properties.append((self._thisDoc + "#" + ln, value))
		    else:
			properties.append((uri, value))# If no uri, syntax error @@
#                    self.sink.makeComment("xml2rdf: Ignored attribute "+uri)
	    elif ns == XML_NS_URI:
		pass	# lang already done, others ignored

            else:  # Property attribute propAttr #MS1.0 6.10
                properties.append((uri, value)) 
#                print "@@@@@@ <%s> <%s>" % properties[-1]

        if self._subject == None:
            self._subject = self.newBlankNode()
        for pred, obj in properties:
	    if pred == RDF_NS_URI + "type":
		self.sink.makeStatement(( self._context,
					self.sink.newSymbol(pred),
					self._subject,
					self.sink.newSymbol(self.uriref(obj)) ), why=self._reason2)
	    else:
		dt = self._datatype
		if dt == None: lang = self._language
		else: lang = None
		self.sink.makeStatement(( self._context,
					self.sink.newSymbol(pred),
					self._subject,
					self.sink.newLiteral(obj, dt, lang) ), why=self._reason2)

            

    def _nodeElement(self, tagURI, attrs):  #MS1.0 6.2
        if tagURI == RDF_NS_URI + "Description":
            self.idAboutAttr(attrs)  # Set up subject and context                

        elif tagURI in nodeElementExceptions:
            raise ValueError, "%s as typednode not implemented" % tagURI
        else:  # Unknown tag within STATE_NO_SUBJECT: typedNode #MS1.0 6.13
            c = self._context   # (Might be changed in idAboutAttr) #@@DC: huh?
            self.idAboutAttr(attrs)
            assert c != None
            assert self._subject != None
            self.sink.makeStatement((  c,
                                       self.sink.newSymbol(RDF_NS_URI+"type"),
                                       self._subject,
                                       self.sink.newSymbol(tagURI) ), why=self._reason2)
        self._state = STATE_DESCRIPTION

    def _propertyAttr(self, ns, name, value):
	"Parse a propertrAttr production.  7.2.25"
	if verbosity() > 50: progress("_propertyAttr ns=5s  name=%s  value=%s"%
			    (ns, name, value))
	if self._subject == None:  # Property as attribute
	    self._subject = self.newBlankNode()

	    self.sink.makeStatement((self._context,
				    self._predicate,
				    self._subject,
				    self._subject ), why=self._reason2)

	if not ns:
	    if "L" not in self.flags:  # assume local?
		raise BadSyntax(sys.exc_info(), "No namespace on property attribute %s=%s" % (name, value))
	    ns = self._thisDoc + "#"

	pred = ns + name
	if pred == RDF_NS_URI + "type":  # special case
	    obj = self.sink.newSymbol(self.uriref(value)) # SYN#7.2.11 step 2/3
	else:
	    obj = self.sink.newLiteral(value, self._datatype, self._language)

	self.sink.makeStatement((self._context,
				    self.sink.newSymbol(self.uriref(pred)),
				    self._subject,
				    obj), why=self._reason2)
	self._state = STATE_NOVALUE  # NOT looking for value
	return
    
                

    def startPrefixMapping(self, prefix, uri):
        """Performance note:
        We make a new dictionary for every binding.
        This makes lookup quick and easy, but
        it takes extra space and more time to
        set up a new binding."""

        #print "startPrefixMapping with prefix=", prefix, "uri=", `uri`
        prefix = prefix or ""
        uri = self.uriref(uri)

        if self._nsmap:
            b = self._nsmap[-1].copy()
        else:
            b = {}
        b[prefix] = uri
        self._nsmap.append(b)

        self.sink.bind(prefix, uri)

    def endPrefixMapping(self, prefix):
        del self._nsmap[-1]

    def startElementNS(self, name, qname, attrs):
        """ Handle start tag.
        """
        
        self.flush()
	self.bnode = None
        
        tagURI = ((name[0] or "") + name[1])

        if verbosity() > 80:
	    indent = ". " * len(self._stack) 
            if not attrs:
                progress(indent+'# State was', self._state, ', start tag: <' + tagURI + '>')
            else:
                str = '# State =%s, start tag= <%s ' %( self._state, tagURI)
                for name, value in attrs.items():
                    str = str + "  " + `name` + '=' + '"' + `value` + '"'
                progress(indent + str + '>')


        self._stack.append([self._state, self._context, self._predicate,
				self._subject, self._delayedStatement, self._base])
				
	self._delayedStatement = None

	self._base = uripath.join(self._base, attrs.get((XML_NS_URI, "base"), self._base))
	x = self._base.find("#")
	if x >= 0: self._base = self._base[:x] # See rdf-tests/rdfcore/xmlbase/test013.rdf
	
	self._language = attrs.get((XML_NS_URI, "lang"), None)

	value = attrs.get((RDF_NS_URI, "datatype"), None)
	if value != None: self._datatype = self.sink.newSymbol(self.uriref(value))
	else: self._datatype = None

        if self._state == STATE_OUTERMOST:
            if tagURI == RDF_NS_URI + "RDF":
                self._state = STATE_NO_SUBJECT
            else:
		if "R" not in self.flags:
		    self._state = STATE_NOT_RDF           # Ignore random XML without rdf:RDF
		else:
		    self._nodeElement(tagURI, attrs)	# Parse it as RDF.
		# http://www.w3.org/2000/10/rdf-tests/rdfcore/rdf-element-not-mandatory/test001.rdf
		    
        elif self._state == STATE_NOT_RDF:
            if tagURI == RDF_NS_URI + "RDF" and "T" in self.flags:
                self._state = STATE_NO_SUBJECT
            else:
                pass                    # Ignore embedded RDF

        elif self._state == STATE_NO_SUBJECT:  #MS1.0 6.2 obj :: desription | container
            self._nodeElement(tagURI, attrs)
		
        elif self._state == STATE_DESCRIPTION:   # Expect predicate (property) PropertyElt
            #  propertyElt #MS1.0 6.12
            #  http://www.w3.org/2000/03/rdf-tracking/#rdf-containers-syntax-ambiguity
            if tagURI == RDF_NS_URI + "li":
                item = self._items[-1] + 1
                self._predicate = self.sink.newSymbol("%s_%s" % (RDF_NS_URI, item))
                self._items[-1] = item
            else:
                if tagURI in propertyElementExceptions:
                    raise BadSyntax(sys.exc_info(), 'Invalid predicate URI: %s' % tagURI) 
                self._predicate = self.sink.newSymbol(tagURI)

            self._state = STATE_VALUE  # May be looking for value but see parse type
#	    self._datatype = None
#	    self._language = None
            self.testdata = ""         # Flush value data
            
            # print "\n  attributes:", `attrs`
	    properties = []
	    gotSubject = 0
            for name, value in attrs.items():
                ns, name = name

                if name == "ID":
                    print "# Warning: ID=%s on statement ignored" %  (value) # I consider these a bug
		    raise ValueError("ID attribute?  Reification not supported.")
                elif name == "parseType":
#		    x = value.find(":")
#		    if x>=0: pref = value[:x]
#		    else: pref = ""
#		    nsURI = self._nsmap[-1].get(pref, None)
                    if value == "Resource":
                        c = self._context
                        s = self._subject
#                        self._subject = self.sink.newBlankNode(self._context, why=self._reason2)
                        self.idAboutAttr(attrs) #@@ not according to current syntax @@@@@@@@@@@
                        self.sink.makeStatement(( c, self._predicate, s, self._subject), why=self._reason2)
                        self._state = STATE_DESCRIPTION  # Nest description
                        
                    elif value == "Quote":
                            c = self._context
                            s = self._subject
                            self.idAboutAttr(attrs)  # set subject and context for nested description
			    self._subject = self.sink.newFormula()  # Forget anonymous genid - context is subect
                            if self._predicate is self.merge: # magic :-(
				self._stack[-1][3] = self._subject  # St C P S retrofit subject of outer level!
				self._delayedStatement = 1 # flag
                            else:
				self._delayedStatement = c, self._predicate, s, self._subject
                            self._context = self._subject
                            self._subject = None
                            self._state = STATE_NO_SUBJECT  # Inside quote, there is no subject
                        
                    elif (value=="Collection" or
			value[-11:] == ":collection"):  # Is this a daml:collection qname?

			self._state = STATE_LIST  # Linked list of obj's
                    elif value == "Literal" or "S" in self.flags:  # Strictly, other types are literal SYN#7.2.20
                        self._state = STATE_LITERAL # That's an XML subtree not a string
                        self._litDepth = 1
                        self.testdata = "@@sax2rdf.py bug@@" # buggy implementation
			self._datatype = self.sink.newSymbol("http://www.w3.org/1999/02/22-rdf-syntax-ns#XMLLiteral")
			raise RuntimeError("This version of sax2rdf.py does not support parseType=Literal.")
		    else:
			raise SyntaxError("Unknown parse type '%s'" % value )
                elif name == "nodeID":
		    assert not gotSubject
                    if not isXML.isNCName(value):
                        raise  BadSyntax(sys.exc_info(), 'A nodeID must be a NCName %s' % value)
		    obj = self._nodeIDs.get(value, None)
		    if obj == None:
			obj = self.newBlankNode()
			self._nodeIDs[value] = obj
                    self.sink.makeStatement((self._context,
                                             self._predicate,
                                             self._subject,
                                             obj ), why=self._reason2)
                    self._state = STATE_NOVALUE  # NOT looking for value
		    self._subject = obj
		    gotSubject = 1
                elif name == "resource":
		    assert not gotSubject
		    x = self.sink.newSymbol(self.uriref(value)) 
                    self.sink.makeStatement((self._context,
                                             self._predicate,
                                             self._subject,
                                             x ), why=self._reason2)
                    self._state = STATE_NOVALUE  # NOT looking for value
		    self._subject = x
		    gotSubject = 1
                elif name == "datatype":
		    pass # Already set
                elif ns == XML_NS_URI or name[:3] == "xml":  #  Ignore (lang is already done)
		    pass # see rdf-tests/rdfcore/unrecognised-xml-attributes/test002.rdf
                else:
		    properties.append((ns, name, value)) # wait till subject is clear
	    if not gotSubject and properties:
		obj = self.newBlankNode()
		self.sink.makeStatement((self._context,
					    self._predicate,
					    self._subject,
					    obj ), why=self._reason2)
		self._state = STATE_NOVALUE  # NOT looking for value
		self._subject = obj
	    
	    for ns, name, value in properties:
		self._propertyAttr(ns, name, value)
		
        elif self._state == STATE_LIST:   # damlCollection :: objs - make list
            # Subject and predicate are set and dangling. 
            c = self._context
            s = self._subject  # The tail of the list so far
            p = self._predicate
            pair = self.newBlankNode()        # The new pair
            self.sink.makeStatement(( c,   # Link in new pair
                                      p,
                                      s,
                                      pair ), why=self._reason2) 
            self.idAboutAttr(attrs)  # set subject (the next item) and context 
            if tagURI != RDF_NS_URI + "Description":
                self.sink.makeStatement((c,
                                         self.sink.newSymbol(RDF_NS_URI
                                                             +"type"),
                                         self._subject,
                                         self.sink.newSymbol(tagURI) ),
                                        why=self._reason2)

            self.sink.makeStatement(( c,
                                      self.sink.newSymbol(List_NS + "first"),
                                      pair,
                                      self._subject), why=self._reason2) # new item
	    if "S" in self.flags: # Strictly to spec
		self.sink.makeStatement(( c,
					self.sink.newSymbol(RDF_NS_URI + "type"),
					self.sink.newSymbol(List_NS + "List"),
					self._subject), why=self._reason2) # new item
            
            self._stack[-1][2] = self.sink.newSymbol(List_NS + "rest")  # Leave dangling link   #@check
            self._stack[-1][3] = pair  # Underlying state tracks tail of growing list

         
        elif self._state == STATE_VALUE:   # Value :: Obj in this case #MS1.0 6.17  6.2
            c = self._context
            p = self._predicate
            s = self._subject
            self._nodeElement(tagURI, attrs)   # Parse the object thing's attributes
            self.sink.makeStatement((c, p, s, self._subject), why=self._reason2)
            
            self._stack[-1][0] = STATE_NOVALUE  # When we return, cannot have literal now

        elif self._state == STATE_NOVALUE:
	    str = ""
	    for e in self._stack: str = str + `e`+"\n"
            raise BadSyntax(sys.exc_info(), """Expected no value, found name=%s; qname=%s, attrs=%s
            in nested context:\n%s""" %(name, qname, attrs, str))

        elif self._state == STATE_LITERAL:
            self._litDepth = self._litDepth + 1
            #@@ need to capture the literal
        else:
            raise RuntimeError, ("Unknown state in RDF parser", self._stack) # Unknown state

# aboutEachprefix { <#> forall r . { r startsWith ppp } l:implies ( zzz } ) 
# aboutEach { <#> forall r . { ppp rdf:li r } l:implies ( zzz } )


    def endElementNS(self, name, qname):
	"""Handle end element event
	"""
        if verbosity() > 80:
	    indent = "- " * len(self._stack) 
	    progress(indent+'# End %s, State was'%name[1], self._state, ", delayed was ", `self._delayedStatement`)

	if self._delayedStatement == 1:
		if verbosity() > 80: progress("Delayed subject "+`self._subject`)
		self._stack[-1][3] = self._stack[-1][3].close()
        if self._state == STATE_LITERAL:
            self._litDepth = self._litDepth - 1
            if self._litDepth == 0:
                buf = self.testdata
                self.sink.makeStatement(( self._context,
                                          self._predicate,
                                          self._subject,
                                          self.sink.newLiteral(buf) ), why=self._reason2)
                self.testdata = ""
            else:
                return # don't pop state
            
        elif self._state == STATE_VALUE:
            buf = self.testdata
	    if self._datatype == None:    # RDFCore changes 2003 - can't have dt and lang
		lang = self._language
	    else:
		lang = None

	    obj = self.sink.newLiteral(buf, self._datatype, lang)
            self.sink.makeStatement(( self._context,
                                       self._predicate,
                                       self._subject,
				       obj), why=self._reason2)
            self.testdata = ""
            
        elif self._state == STATE_LIST:
            self.sink.makeStatement(( self._context,
                                      self.sink.newSymbol(List_NS + "rest"),
                                      self._subject,
                                      self.sink.newSymbol(List_NS + "nil") ), why=self._reason2)
        elif self._state == STATE_DESCRIPTION:
            self._items.pop()
        elif self._state == STATE_NOVALUE or \
             self._state == STATE_NO_SUBJECT or \
             self._state == STATE_OUTERMOST or \
             self._state == STATE_NOT_RDF: # akuchlin@mems-exchange.org 2002-09-11
            pass
        else:
            raise RuntimeError, ("Unknown RDF parser state '%s' in end tag" % self._state, self._stack)
	    
#	c1 = self._context
#	if self._subject is c1 and self_context is not c1:
#	    self._subject = self._subject.close() # close before use

        l =  self._stack.pop() #
        self._state = l[0]
        self._context = l[1]
        self._predicate = l[2]
        self._subject = l[3]

	if self._delayedStatement != None:
	    if self._delayedStatement == 1:
		pass
#		progress("Delayed subject "+`self._subject`)
#		self._subject = self._subject.close()
	    else:
		c, p, s, o = self._delayedStatement
		o = o.close()
		self.sink.makeStatement((c, p, s, o), why=self._reason2)
		self._delayedStatement = None

	self._delayedStatement = l[4]
	self._base = l[5]

        self.flush()
        # print '\nend tag: </' + tag + '>'

    def endDocument(self, f=None):
        self.flush()
        self.sink.endDoc(self._formula)


class RDFXMLParser(RDFHandler):
    """XML/RDF parser based on sax XML interface"""

    flagDocumentation = """
    Flags to control RDF/XML INPUT (after --rdf=) follow:
        S  - Strict spec. Unknown parse type treated as Literal instead of error.
        T  - take foreign XML as transparent and parse any RDF in it
             (default it is to ignore unless rdf:RDF at top level)
	L  - If non-rdf attributes have no namespace prefix, assume in local <#> namespace
	D  - Assume default namespace decalred as local document is assume xmlns=""

    Note: The parser (sax2rdf) does not support reification, bagIds, or parseType=Literal.
          It does support the rest of RDF inc. datatypes, xml:lang, and nodeIds.

"""

    def __init__(self, sink, openFormula, thisDoc=None,  flags="", why=None):
        RDFHandler.__init__(self, sink, openFormula, thisDoc, flags=flags)
	assert thisDoc != None, "Need document URI at the moment, sorry"
        p = xml.sax.make_parser()
        p.setFeature(feature_namespaces, 1)
        p.setContentHandler(self)
        self._p = p
	self.reason = why

    def feed(self, data):
        self._p.feed(data)

    def load(self, uri, baseURI=""):
	progress("obsolete: use llyn.load()")
	"""Parse a document identified bythe URI, return the top level formula"""
        if uri:
            _inputURI = uripath.join(baseURI, uri) # Make abs from relative
            f = urlopenForRDF(_inputURI)
        else:
            _inputURI = uripath.join(baseURI, "STDIN") # Make abs from relative
            f = sys.stdin
        return self.loadStream(f)
#	return self._formula

    def loadStream(self, stream):
        s = xml.sax.InputSource()
        s.setByteStream(stream)
        try:
            self._p.parse(s)
        except xml.sax._exceptions.SAXException, e:
            # was: raise SyntaxError() which left no info as to what had happened
	    columnNumber = self._p.getColumnNumber()
	    lineNumber = self._p.getLineNumber()
	    where = "parsing XML at column %i in line %i of <%s>\n\t" % (
			    columnNumber, lineNumber, self._thisDoc)
            raise SyntaxError(where + sys.exc_info()[1].__str__())
        # self.close()  don't do a second time - see endDocument
	return self._formula

    def close(self):
        self._p.reset()
        self.flush()
        self.sink.endDoc(self._formula)
	return self._formula

class BadSyntax(SyntaxError):
    def __init__(self, info, message):
	self._info = info
	self._message = message

    def __str__(self):
	return self._message


def test(args = None):
    import sys, getopt
    import notation3
    
    from time import time

    if not args:
        args = sys.argv[1:]

    opts, args = getopt.getopt(args, 'st')
    klass = RDFHandler
    do_time = 0
    for o, a in opts:
        if o == '-s':
            klass = None #@@ default handler for speed comparison?
        elif o == '-t':
            do_time = 1

    if args:
        file = args[0]
    else:
        file = 'test.xml'

    if file == '-':
        f = sys.stdin
    else:
        try:
            f = open(file, 'r')
        except IOError, msg:
            print file, ":", msg
            sys.exit(1)

    x = klass(notation3.ToN3(sys.stdout.write), "file:/test.rdf") # test only!
    p = xml.sax.make_parser()
    from xml.sax.handler import feature_namespaces
    p.setFeature(feature_namespaces, 1)
    p.setContentHandler(x)
    p.setErrorHandler(xml.sax.ErrorHandler())
    s = xml.sax.InputSource()
    t0 = time()
    try:
        if do_time:
            #print "parsing:", f
            s.setByteStream(f)
            p.parse(s)
        else:
            data = f.read()
            #print "data:", data
            if f is not sys.stdin:
                f.close()
            for c in data:
                p.feed(c, 1)
            p.close()
    except RuntimeError, msg:
        t1 = time()
        print msg
        if do_time:
            print 'total time: %g' % (t1-t0)
        sys.exit(1)
    t1 = time()
    if do_time:
        print 'total time: %g' % (t1-t0)


if __name__ == '__main__':
    test()

