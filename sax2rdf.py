#! /usr/bin/python
"""
  A parser for RDF/XML built on the sax2 interface;
  derived from a parser for RDF/XML built on the xmllib XML parser.

  To do: Passing on namesapce bindings!
       (dwc: @@huh?)
       (tbl: The bind call in the RDF stream API is used to pass
        on the prefixes found, as hints only for generating readable output code)

  - Add parsing of RDF bags

 parses DAML_ONT_NS or DPO_NS lists, generates DPO_NS

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
    
##################################### SAX pointers
 First hit on Python SAX parser
 http://www.gca.org/papers/xmleurope2000/papers/s28-04.html#N84395

 Howto use SAX in python:
 http://www.python.org/doc/howto/xml/SAX.html

"""

import urlparse  # Comes with python 1.6, lacks file<->url mapping
import urllib   # Opening resources in load()
import string

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

import notation3 # http://www.w3.org/2000/10/swap/notation3.py

# States:

STATE_NOT_RDF =     "not RDF"     # Before <rdf:RDF>
STATE_NO_SUBJECT =  "no context"  # @@@@@@@@@ use numbers for speed
STATE_DESCRIPTION = "Description (have subject)" #
STATE_LITERAL =     "within literal"
STATE_VALUE =       "plain value"
STATE_NOVALUE =     "no value"
STATE_LIST =        "within list"

FORMULA = notation3.FORMULA
RESOURCE = notation3.RESOURCE
LITERAL = notation3.LITERAL

RDF_NS_URI = notation3.RDF_NS_URI # As per the spec
RDF_Specification = "http://www.w3.org/TR/REC-rdf-syntax/" # Must come in useful :-)
DAML_ONT_NS = "http://www.daml.org/2000/10/daml-ont#"  # DAML early version
DPO_NS = "http://www.daml.org/2001/03/daml+oil#"  # DAML plus oil
chatty = 0

RDF_IS = RESOURCE, RDF_NS_URI + "is"   # Used with quoting


class RDFHandler(xml.sax.ContentHandler):

    def __init__(self, sink, thisURI, **kw):
        self.testdata = ""
        self._stack =[]  # Stack of states
        self._nsmap = [] # stack of namespace bindings

        self.sink = sink
        self._thisURI = thisURI
        self._state = STATE_NOT_RDF  # Maybe should ignore RDF poutside <rdf:RDF>??
        self._context = FORMULA, thisURI + "#_formula"  # Context of current statements, change in bags
        self._subject = None
        self._predicate = None
        self._items = [] # for <rdf:li> containers
        self._genPrefix = "#_g"    # @@@ allow parameter override
        self._nextId = 0        # For generation of arbitrary names for anonymous nodes
        self.sink.startDoc()
        version = "$Id$"
        self.sink.makeComment("RDF parsed by "+version[1:-1])


#@@    def load(self, uri, _baseURI=""):
#        if uri:
#            _inputURI = urlparse.urljoin(_baseURI, uri) # Make abs from relative
#            netStream = urllib.urlopen(_inputURI)
#            self.feed(netStream.read())     # @ May be big - buffered in memory!
#            self.close()
#        else:
#            _inputURI = urlparse.urljoin(_baseURI, "STDIN") # Make abs from relative
#            self.feed(sys.stdin.read())     # May be big - buffered in memory!
#            self.close()


    def characters(self, data):
        if self._state == STATE_VALUE:
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
        """ 
        return urlparse.urljoin(self._thisURI,
                                str.encode('utf-8')) # fails on non-ascii; do %xx encoding?

    def idAboutAttr(self, attrs):  #6.5 also proprAttr 6.10
        """ set up subject and maybe context from attributes
        """
        self._subject = None
        self._state = STATE_DESCRIPTION
        self._subject = None
        self._items.append(0)
        properties = []
        
        for name, value in attrs.items():
            ns, ln = name
            if ns:
                if string.find("ID about aboutEachPrefix bagID type", ln)>0:
                    if ns != RDF_NS_URI:
                        print ("# Warning -- %s attribute in %s namespace not RDF NS." %
                               name, ln)
                        ns = RDF_NS_URI  # @@HACK!
                uri = (ns + ln).encode('utf-8')
#               raise NoNS   # @@@ Actually, XML spec says we should get these: parser is wrong
            if ns == RDF_NS_URI or ns == None:   # Opinions vary sometimes none but RDF_NS is common :-(
                
                if ln == "ID":
                    if self._subject:
                        print "# oops - subject already", self._subject
                        raise syntaxError # ">1 subject"
                    self._subject = self.uriref("#" + value)
                elif ln == "about":
                    if self._subject: raise syntaxError # ">1 subject"
                    self._subject = self.uriref(value)
                elif ln == "aboutEachPrefix":
                    if value == " ":  # OK - a trick to make NO subject
                        self._subject = None
                    else: raise ooops # can't do about each prefix yet
                elif ln == "bagid":
                    c = self._context #@@dwc: this is broken, no?
                    self._context = FORMULA, self.uriref("#" + value) #@@ non-ascii
                elif ln == "parseType":
                    pass  #later - object-related
                elif ln == "value":
                    pass  #later
                elif ln == "resource":
                    pass  #later
                else:
                    if not ns:
                        print "#@@@@@@@@@@@@ No namespace on property attribute", ln
                        raise self.syntaxError 
                    properties.append((uri, value))# If no uri, syntax error @@
#                    self.sink.makeComment("xml2rdf: Ignored attribute "+uri)
            else:  # Property attribute propAttr #6.10
                properties.append((uri, value)) 
#                print "@@@@@@ <%s> <%s>" % properties[-1]

        if self._subject == None:
            self._subject = self._generate()
        for pred, obj in properties:
            self.sink.makeStatement(( self._context,
                                      (RESOURCE, pred),
                                      (RESOURCE, self._subject),
                                      (LITERAL, obj) ))

            
    def _generate(self):
            generatedId = self._genPrefix + `self._nextId`  #
            self._nextId = self._nextId + 1
            self.sink.makeStatement(( self._context,
                                      (RESOURCE, notation3.N3_forSome_URI),
                                      self._context,
                                      (RESOURCE, generatedId) )) #  Note this is anonymous node
            return generatedId

    def _obj(self, tagURI, attrs):  # 6.2
        if tagURI == RDF_NS_URI + "Description":
            self.idAboutAttr(attrs)  # Set up subject and context                

        elif tagURI == RDF_NS_URI + "li":
            raise ValueError, "rdf:li as typednode not implemented"
        else:  # Unknown tag within STATE_NO_SUBJECT: typedNode #6.13
            c = self._context   # (Might be change in idAboutAttr)
            self.idAboutAttr(attrs)
            if c == None: raise roof
            if self._subject == None:raise roof
            self.sink.makeStatement((  c,
                                       (RESOURCE, RDF_NS_URI+"type"),
                                       (RESOURCE, self._subject),
                                       (RESOURCE, tagURI) ))
        self._state = STATE_DESCRIPTION
                

    def startPrefixMapping(self, prefix, uri):
        """Performance note:
        We make a new dictionary for every binding.
        This makes lookup quick and easy, but
        it takes extra space and more time to
        set up a new binding."""

        #print "startPrefixMapping with prefix=", prefix, "uri=", `uri`
        prefix = prefix or ""
        uri = uri.encode('utf-8') # reduce XML's unicode to URI's US-ASCII
        #print "startPrefixMapping uri encoded as=", `uri`

        if self._nsmap:
            b = self._nsmap[-1].copy()
        else:
            b = {}
        b[prefix] = uri
        self._nsmap.append(b)

        self.sink.bind(prefix, (RESOURCE, uri))

    def endPrefixMapping(self, prefix):
        del self._nsmap[-1]

    def startElementNS(self, name, qname, attrs):
        """ Handle start tag.
        """
        
        self.flush()
        
        tagURI = ((name[0] or "") + name[1]).encode('utf-8')

        if chatty:
            if not attrs:
                print '# State =', self._state, 'start tag: <' + tagURI + '>'
            else:
                print '# state =', self._state, 'start tag: <' + tagURI,
                for name, value in attrs.items():
                    print "    " + name + '=' + '"' + value + '"',
                print '>'


        self._stack.append([self._state, self._context, self._predicate, self._subject])

        if self._state == STATE_NOT_RDF:
            if tagURI == RDF_NS_URI + "RDF":
                self._state = STATE_NO_SUBJECT
            else:
                pass                    # Some random XML

        elif self._state == STATE_NO_SUBJECT:  # 6.2 obj :: desription | container
            self._obj(tagURI, attrs)
            
        elif self._state == STATE_DESCRIPTION:   # Expect predicate (property) PropertyElt
            #  propertyElt #6.12
            #  http://www.w3.org/2000/03/rdf-tracking/#rdf-containers-syntax-ambiguity
            if tagURI == RDF_NS_URI + "li":
                item = self._items[-1] + 1
                self._predicate = "%s_%s" % (RDF_NS_URI, item)
                self._items[-1] = item
            else:
                self._predicate = tagURI

            self._state = STATE_VALUE  # May be looking for value but see parse type
            self.testdata = ""         # Flush value data
            
            # print "\n  attributes:", `attrs`

            for name, value in attrs.items():
                ns, name = name
                if name == "ID":
                    print "# Warning: ID=%s on statement ignored" %  (value) # I consider these a bug
                elif name == "parseType":
                    if value == "Literal":
                        self._state = STATE_LITERAL # That's an XML subtree not a string
                        
                    elif value == "Resource":
                        c = self._context
                        s = self._subject
                        self.idAboutAttr(attrs)  # set subject and context for nested description @@dwc thinks this is buggy
                        self.sink.makeStatement(( c,
                                                  (RESOURCE, self._predicate),
                                                  (RESOURCE, s),
                                                  (RESOURCE, self._subject) ))
                        self._state = STATE_DESCRIPTION  # Nest description
                        
                    elif value[-6:] == ":quote":
                        nsURI = self._nsmap[-1].get(pref, None)
                        if nsURI == Logic_NS: 
                            c = self._context
                            s = self._subject
                            self.idAboutAttr(attrs)  # set subject and context for nested description
                            if self._predicate == RDF_NS_URI+"is": # magic :-( @@notation3.py switched to Logic_NS here, I think.
                                self._subject = s  # Forget anonymous genid - context is subect
                                print "#@@@@@@@@@@@@@ decided subject is ",`s`[-10:-1]
                            else:
                                self.sink.makeStatement(( c,
                                                          (RESOURCE, self._predicate),
                                                          (RESOURCE, s),
                                                          (RESOURCE, self._subject) ))
                            self._context = FORMULA, self._subject
                            self._subject = None
                            self._state = STATE_NO_SUBJECT  # Nest context
                        
                    elif value[-11:] == ":collection":  # Is this a daml:collection qname?
                        pref = value[:-11]
                        nsURI = self._nsmap[-1].get(pref, None)
                        if (nsURI == DAML_ONT_NS
                                               or nsURI == DPO_NS): 
                            self._state = STATE_LIST  # Linked list of obj's
                                #print "########### Start list"
                        #print "############ parsetype pref=",pref ,"nslist",nslist

                elif name == "resource":
                    self.sink.makeStatement((self._context,
                                             (RESOURCE, self._predicate),
                                             (RESOURCE, self._subject),
                                             (RESOURCE, self.uriref(value)) ))
                    self._state = STATE_NOVALUE  # NOT looking for value
                elif name == "value":
                    self.sink.makeStatement((self._context,
                                             (RESOURCE, self._predicate),
                                             (RESOURCE, self._subject),
                                             (LITERAL,  value) ))
                    self._state = STATE_NOVALUE  # NOT looking for value
                else:
                    self.sink.makeComment("# Warning: Ignored attribute %s on %s" % (
                        name, tagURI))
                    
        elif self._state == STATE_LIST:   # damlCollection :: objs - make list
            # Subject and predicate are set and dangling. 
            c = self._context
            s = self._subject  # The tail of the list so far
            p = self._predicate
            pair = self._generate()        # The new pair
            self.sink.makeStatement(( c,   # Link in new pair
                                      (RESOURCE, p),
                                      (RESOURCE, s),
                                      (RESOURCE, pair) )) 
            self.idAboutAttr(attrs)  # set subject (the next item) and context 
            self.sink.makeStatement(( c,
                                      (RESOURCE, DPO_NS + "first"),
                                      (RESOURCE, pair),
                                      (RESOURCE, self._subject) )) # new item
            
            self._stack[-1][2] = DPO_NS + "rest"  # Leave dangling link
            self._stack[-1][3] = pair  # Underlying state tracks tail of growing list

         
        elif self._state == STATE_VALUE:   # Value :: Obj in this case # 6.17  6.2
            c = self._context
            p = self._predicate
            s = self._subject
            self._obj(tagURI, attrs)   # Parse the object thing's attributes
            self.sink.makeStatement(( c, # Link to new object
                                      (RESOURCE, p),
                                      (RESOURCE, s),
                                      (RESOURCE, self._subject) ))
            
            self._stack[-1][0] = STATE_NOVALUE  # When we return, cannot have literal now

        elif self._state == STATE_NOVALUE:
            print "\n@@ Expected no value, found ", name, qname, attrs, "\n Stack: ",self._stack
            raise ValueError # Found tag, expected empty
        else:
            raise RuntimeError # Unknown state

# aboutEachprefix { <#> forall r . { r startsWith ppp } l:implies ( zzz } ) 
# aboutEach { <#> forall r . { ppp rdf:li r } l:implies ( zzz } )


    def endElementNS(self, name, qname):
        
        if self._state == STATE_VALUE:
            buf = self.testdata
            self.sink.makeStatement(( self._context,
                                       (RESOURCE, self._predicate),
                                       (RESOURCE, self._subject),
                                       (LITERAL,  buf) ))
            self.testdata = ""
            
        elif self._state == STATE_LIST:
            self.sink.makeStatement(( self._context,
                                      (RESOURCE, DPO_NS + "rest"),
                                      (RESOURCE, self._subject),
                                      (RESOURCE, DPO_NS + "nil") ))
        elif self._state == STATE_DESCRIPTION:
            self._items.pop()

        l =  self._stack.pop() # [self._state, self._context, self._subject])
        self._state = l[0]
        self._context = l[1]
        self._predicate = l[2]
        self._subject = l[3]
        self.flush()
        # print '\nend tag: </' + tag + '>'

    def endDocument(self):
        self.flush()
        self.sink.endDoc()


class RDFXMLParser(RDFHandler):
    def __init__(self, sink, thisURI, **kw):
        RDFHandler.__init__(self, sink, thisURI)
        p = xml.sax.make_parser()
        p.setFeature(feature_namespaces, 1)
        p.setContentHandler(self)
        self._p = p

    def feed(self, data):
        self._p.feed(data)

    def load(self, uri, _baseURI=""):
        if uri:
            _inputURI = urlparse.urljoin(_baseURI, uri) # Make abs from relative
            f = urllib.urlopen(_inputURI)
        else:
            _inputURI = urlparse.urljoin(_baseURI, "STDIN") # Make abs from relative
            f = sys.stdin
        self.loadStream(f)

    def loadStream(self, stream):
        s = xml.sax.InputSource()
        s.setByteStream(stream)
        try:
            self._p.parse(s)
        except xml.sax._exceptions.SAXException, e:
            raise SyntaxError()
        self.close()

    def close(self):
        self._p.reset()
        self.flush()
        self.sink.endDoc()



def test(args = None):
    import sys, getopt
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

