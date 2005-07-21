#!/usr/bin/env python
"""
Builtins for doing SPARQL queries in CWM

$Id$

"""

from term import LightBuiltIn, Function, ReverseFunction, MultipleFunction,\
    MultipleReverseFunction, typeMap, LabelledNode, \
    CompoundTerm, N3Set, List, EmptyList, NonEmptyList, \
    Symbol, Fragment, Literal, Term, AnonymousNode, HeavyBuiltIn
import diag
progress = diag.progress

from RDFSink import RDFSink
from set_importer import Set

import uripath

from toXML import XMLWriter

try:
    from decimal import Decimal
except ImportError:
    from local_decimal import Decimal

from term import ErrorFlag as MyError

SPARQL_NS = 'http://yosi.us/2005/sparql'


def toBool(val, dt=None):
    if dt == 'boolean':
        if val == 'false' or val == 'False' or val == '0':
            return False
        return toBool(val)
    if dt in typeMap:
        return bool(typeMap[dt](val))
    return bool(val)


class BI_truthValue(LightBuiltIn):
    def eval(self, subj, obj, queue, bindings, proof, query):
        if isinstance(subj, Literal):
##            print '%s makes %s' % (subj, toBool(str(subj), subj.datatype.fragid))
##            print '%s makes %s' % (obj, toBool(str(obj), obj.datatype.fragid))
##            print 'I got here on %s, %s, returning %s' % (subj, obj, toBool(str(subj), subj.datatype.fragid) is toBool(str(obj), obj.datatype.fragid))
            return toBool(str(subj), subj.datatype.fragid) is toBool(str(obj), obj.datatype.fragid)
        raise TypeError

class BI_typeErrorIsTrue(LightBuiltIn):
    """
Subject is anything (must be bound. 1 works well)
Object is a formula containing the test as its only triple

    """
    def eval(self, subj, obj, queue, bindings, proof, query):
        if len(obj) != 1:
            raise TypeError
        statement = obj.statements[0]
        try:
            return statement.predicate().eval(statement.subject(), statement.object(), queue, bindings, proof, query)
        except:
            return True

class BI_typeErrorReturner(LightBuiltIn, Function):
    def evalObj(self, subj, queue, bindings, proof, query):
        if len(subj) != 1:
            raise TypeError
        statement = subj.statements[0]
        try:
            return statement.predicate().evalObj(statement.subject(), queue, bindings, proof, query)
        except:
            return MyError()

class BI_equals(LightBuiltIn, Function, ReverseFunction):
    def eval(self, subj, obj, queue, bindings, proof, query):
        xsd = self.store.integer.resource
        if isinstance(subj, Symbol) and isinstance(obj, Symbol):
            return subj is obj
        if isinstance(subj, Fragment) and isinstance(obj, Fragment):
            return subj is obj
        if isinstance(subj, Literal) and isinstance(obj, Literal):
            if subj.datatype == xsd['boolean'] or obj.datatype == xsd['boolean']:
                return (toBool(str(subj), subj.datatype.resource is xsd and subj.datatype.fragid or None) ==
                        toBool(str(obj), obj.datatype.resource is xsd and obj.datatype.fragid or None))
            if not subj.datatype and not obj.datatype:
                return str(subj) == str(obj)
            if subj.datatype.fragid in typeMap and obj.datatype.fragid in typeMap:
                return subj.value() == obj.value()
            if subj.datatype != obj.datatype:
                raise TypeError(subj, obj)
            return str(subj) == str(obj)
        raise TypeError(subj, obj)
                
        

    def evalSubj(self, obj, queue, bindings, proof, query):
        return obj

    def evalObj(self,subj, queue, bindings, proof, query):
        return subj


class BI_lessThan(LightBuiltIn):
    def evaluate(self, subject, object):
        return (subject < object)

class BI_greaterThan(LightBuiltIn):
    def evaluate(self, subject, object):
        return (subject > object)

class BI_notGreaterThan(LightBuiltIn):
    def evaluate(self, subject, object):
        return (subject <= object)

class BI_notLessThan(LightBuiltIn):
    def evaluate(self, subject, object):
        return (subject >= object)


class BI_notEquals(LightBuiltIn):
    def eval(self, subj, obj, queue, bindings, proof, query):
        return not self.store.newSymbol(SPARQL_NS)['equals'].eval(subj, obj, queue, bindings, proof, query)

class BI_dtLit(LightBuiltIn, Function, ReverseFunction):
    def evalObj(self,subj, queue, bindings, proof, query):
        subj = [a for a in subj]
        if len(subj) != 2:
            raise TypeError
        subject, datatype = subj
        if not isinstance(subj, Literal) or not isinstance(datatype, LabelledNode):
            raise TypeError
        if subj.datatype:
            raise TypeError('%s must not have a type already' % subj)
        return self.store.newLiteral(str(subj), dt=datatype)

    def evalSubj(self, obj, queue, bindings, proof, query):
        if not isinstance(obj, Literal):
            raise TypeError
        return self.store.newList([self.store.newLiteral(str(obj)), obj.datatype])


#############################
#############################
#    Builtins useful from within cwm, not within SPARQL
#
#############################
#############################

    

class BI_query(LightBuiltIn, Function):
    def evalObj(self,subj, queue, bindings, proof, query):
        from query import applySparqlQueries
        RESULTS_NS = 'http://www.w3.org/2005/06/sparqlResults#'
        ns = self.store.newSymbol(SPARQL_NS)
        assert isinstance(subj, List)
        subj = [a for a in subj]
        assert len(subj) == 2
        source, query = subj
        F = self.store.newFormula()
        applySparqlQueries(source, query, F)
        if query.contains(obj=ns['ConstructQuery']):
            return F
        if query.contains(obj=ns['SelectQuery']):
            node = query.the(pred=self.store.type, obj=ns['SelectQuery'])
            print 'I got to here'
            outputList = []
            prefixTracker = RDFSink()
            prefixTracker.setDefaultNamespace(RESULTS_NS)
            prefixTracker.bind('', RESULTS_NS)
            xwr = XMLWriter(outputList.append, prefixTracker)
            xwr.makePI('xml version="%s"' % '1.0')
            xwr.startElement(RESULTS_NS+'sparql', [], prefixTracker.prefixes)
            xwr.startElement(RESULTS_NS+'head', [], prefixTracker.prefixes)
            vars = []
            for triple in query.the(subj=node, pred=ns['select']):
                vars.append(triple.object())
                xwr.emptyElement(RESULTS_NS+'variable', [(RESULTS_NS+'name', str(triple.object()))], prefixTracker.prefixes)

            xwr.endElement()
            xwr.startElement(RESULTS_NS+'results', [], prefixTracker.prefixes)
            for resultFormula in F.each(pred=self.store.type, obj=ns['Result']):
                xwr.startElement(RESULTS_NS+'result', [], prefixTracker.prefixes)
                for var in vars:
                    xwr.startElement(RESULTS_NS+'binding', [(RESULTS_NS+'name', str(var))],  prefixTracker.prefixes)
                    binding = resultFormula.the(pred=ns['bound'], obj=var)
                    if binding:
                        if isinstance(binding, LabelledNode):
                            xwr.startElement(RESULTS_NS+'uri', [],  prefixTracker.prefixes)
                            xwr.data(binding.uriref())
                            xwr.endElement()
                        elif isinstance(binding, (AnonymousNode, List)):
                            xwr.startElement(RESULTS_NS+'bnode', [],  prefixTracker.prefixes)
                            xwr.data(binding.uriref())
                            xwr.endElement()
                        elif isinstance(binding, Literal):
                            props = []
                            if binding.datatype:
                                props.append((RESULTS_NS+'datatype', binding.datatype.uriref()))
                            if binding.lang:
                                props.append(("http://www.w3.org/XML/1998/namespace#lang", binding.lang))
                            xwr.startElement(RESULTS_NS+'literal', props,  prefixTracker.prefixes)
                            xwr.data(str(binding))
                            xwr.endElement()
                    else:
                        xwr.emptyElement(RESULTS_NS+'unbound', [], prefixTracker.prefixes)
                    xwr.endElement()

                xwr.endElement()
            xwr.endElement()
            xwr.endElement()
            xwr.endDocument()
            return self.store.newLiteral(''.join(outputList))
        if query.contains(obj=ns['AskQuery']):
            node = query.the(pred=self.store.type, obj=ns['AskQuery'])
            outputList = []
            prefixTracker = RDFSink()
            prefixTracker.setDefaultNamespace(RESULTS_NS)
            prefixTracker.bind('', RESULTS_NS)
            xwr = XMLWriter(outputList.append, prefixTracker)
            xwr.makePI('xml version="%s"' % '1.0')
            xwr.startElement(RESULTS_NS+'sparql', [], prefixTracker.prefixes)
            xwr.startElement(RESULTS_NS+'head', [], prefixTracker.prefixes)
            vars = []
#            for triple in query.the(subj=node, pred=ns['select']):
#                vars.append(triple.object())
#                xwr.emptyElement(RESULTS_NS+'variable', [(RESULTS_NS+'name', str(triple.object()))], prefixTracker.prefixes)

            xwr.endElement()
            xwr.startElement(RESULTS_NS+'boolean', [], prefixTracker.prefixes)
            if F.the(pred=self.store.type, obj=ns['Success']):
                xwr.data('true')
            else:
                xwr.data('false')
            xwr.endElement()
                

            xwr.endElement()
            xwr.endDocument()
            return self.store.newLiteral(''.join(outputList))

class BI_semantics(HeavyBuiltIn, Function):
    """ The semantics of a resource are its machine-readable meaning, as an
    N3 forumula.  The URI is used to find a represnetation of the resource in bits
    which is then parsed according to its content type."""
    def evalObj(self, subj, queue, bindings, proof, query):
        store = subj.store
        if isinstance(subj, Fragment): doc = subj.resource
        else: doc = subj
        F = store.any((store._experience, store.semantics, doc, None))
        if F != None:
            if diag.chatty_flag > 10: progress("Already read and parsed "+`doc`+" to "+ `F`)
            return F

        if diag.chatty_flag > 10: progress("Reading and parsing " + doc.uriref())
        inputURI = doc.uriref()
        F = self.store.load(inputURI, contentType="x-application/sparql")
        if diag.chatty_flag>10: progress("    semantics: %s" % (F))
	if diag.tracking:
	    proof.append(F.collector)
        return F.canonicalize()

def register(store):
    ns = store.newSymbol(SPARQL_NS)
    ns.internFrag('equals', BI_equals)
    ns.internFrag('lessThan', BI_lessThan)
    ns.internFrag('greaterThan', BI_greaterThan)
    ns.internFrag('notGreaterThan', BI_notGreaterThan)
    ns.internFrag('notLessThan', BI_notLessThan)
    ns.internFrag('notEquals', BI_notEquals)
    ns.internFrag('typeErrorIsTrue', BI_typeErrorIsTrue)
    ns.internFrag('typeErrorReturner', BI_typeErrorReturner)
    ns.internFrag('truthValue', BI_truthValue)
    ns.internFrag('query', BI_query)
    ns.internFrag('semantics', BI_semantics)