# $Id$


PYTHON=python

YAPPS=yapps2.py

TESTIN=test/sameDan.n3

HTMLS= term.html formula.html pretty.html myStore.html check.html query.html RDFSink.html cwm.html cwm_crypto.html cwm_list.html cwm_math.html cwm_maths.html cwm_os.html cwm_string.html cwm_time.html cwm_times.html diag.html llyn.html notation3.html reify.html sax2rdf.html rdflib2rdf.html tab2n3.html thing.html toXML.html uripath.html xml2infoset.html why.html doc/changes.html

SOURCES = cwm.py notation3.py query.py llyn.py uripath.py diag.py RDFSink.py reify.py why.py myStore.py webAccess.py OrderedSequence.py term.py formula.py pretty.py cwm_list.py cwm_string.py cwm_os.py cwm_time.py isodate.py cwm_math.py cwm_trigo.py cwm_times.py cwm_maths.py toXML.py update.py sax2rdf.py rdflib_user.py rdfxml.py __init__.py decimal.py isXML.py
DOC=doc/CwmHelp.htm

TESTS = test/Makefile test/regression.n3 test/list/detailed.tests test/ql/detailed.tests test/math/detailed.tests test/norm/detailed.tests test/cwm/detailed.tests test/ntriples/detailed.tests test/delta/detailed.tests test/syntax/detailed.tests test/reify/detailed.tests test/testmeta.n3 test/retest.py

VERSION = 0.8.1
TARNAME = cwm-$(VERSION)

TARBALL_STUFF = README LICENSE LICENSE.rdf LICENSE.n3

.SUFFIXES: .html .py .g .rdf .n3

.g.py:
	$(PYTHON) $(YAPPS) $< $@

.n3.rdf:
	$(PYTHON) cwm.py $<  --rdf > $@

.py.html:
	pydoc -w `echo $< | sed -e 's/\.py//'`

.DELETE_ON_ERROR : swap

#all: yappstest yappsdoc math.rdf log.rdf db.rdf os.rdf string.rdf crypto.rdf


tested :  updated package
	(cd test; make pre-release)
	echo "Test worked, now can make release"

updated :
	cvs -q update -d

filelist: $(SOURCES) $(TESTS)
	(cd test; $(MAKE) filelist)

doc.made : cwm.py notation3.py sax2rdf.py toXML.py
	(cd doc; make)

release : doc.made cwm.tar.gz message.txt
	cvs commit -F message.txt
	rm message.txt


package: math.rdf maths.rdf log.rdf db.rdf os.rdf string.rdf crypto.rdf time.rdf times.rdf LICENSE.rdf  $(HTMLS)


# Can't make dependencies on *.py :-(

# cwm.py notation3.py llyn.py  RDFSink.py toXML.py
cwm.tar.gz:  $(HTMLS) $(SOURCES) $(TESTS) $(TARBALL_STUFF) tested filelist
	cvs -q update
	tar -czf  cwm.tar.gz $(HTMLS) $(SOURCES) $(TESTS) $(TARBALL_STUFF) `cat test/testfilelist | sed -e 's/^/test\//'`
	rm -rf ,cwm-tarball-test
	mkdir ,cwm-tarball-test
	cd ,cwm-tarball-test && tar -xzf ../cwm.tar.gz
	cd ,cwm-tarball-test/test && $(MAKE)
	cd ,cwm-tarball-test && rm -rf *
	cd ,cwm-tarball-test && tar -xzf ../cwm.tar.gz
	mv ,cwm-tarball-test $(TARNAME)
	rm cwm.tar.gz
	tar -czf $(TARNAME).tar.gz $(TARNAME)
	mv $(TARNAME) ,cwm-tarball-test
	head -n -1 .htaccess > ,htaccess
	echo 'RewriteRule ^cwm.tar.gz$ ' $(TARNAME) '[L]' >> ,htaccess
	mv ,htaccess .htaccess
	cvs add $(TARNAME).tar.gz
#LX/*.py LX/*/*.py  LX/*/*.P dbork/*.py ply/*.py *.py

setup_tarball: $(SOURCES) tested $(HTMLS) $(TESTS) $(TARBALL_STUFF) filelist
	-rm -rf swap
	mkdir swap
	cd swap; for A in $(SOURCES); do ln "../$$A"; done
	echo "cwm.py" > MANIFEST
	echo "setup.py" >> MANIFEST
	for A in $(TARBALL_STUFF) $(HTMLS) $(TESTS); do echo "$$A" >> MANIFEST; done
	for A in $(SOURCES); do echo swap/"$$A" >> MANIFEST; done
	cat test/testfilelist | sed -e 's/^/test\//' >> MANIFEST
	python setup.py sdist
	-python setup.py bdist_rpm
	-python setup.py bdist_wininst
	rm -rf swap
	cp dist/cwm-$(VERSION).tar.gz .
	-rm -rf ,cwm-$(VERSION)-test
	mkdir ,cwm-$(VERSION)-test
	cd ,cwm-$(VERSION)-test && tar -xzf ../cwm-$(VERSION).tar.gz
	cd ,cwm-$(VERSION)-test/cwm-$(VERSION)/test && $(MAKE)
	head -n 1 .htaccess > ,htaccess
	echo 'RewriteRule ^cwm.tar.gz$ ' $(TARNAME) '[L]' >> ,htaccess
	mv ,htaccess .htaccess
	cvs add $(TARNAME).tar.gz	

yappstest: rdfn3_yapps.py rdfn3_yappstest.py
	$(PYTHON) rdfn3_yappstest.py <$(TESTIN) >,xxx.kif

rdfn3_yapps.py: rdfn3.g
	$(PYTHON) $(YAPPS) rdfn3.g $@

yappsdoc: rdfn3-gram.html relaxNG-gram.html

rdfn3-gram.html: rdfn3.g gram2html.py
	$(PYTHON) gram2html.py rdfn3.g "RDF Notation3 Grammar" >$@

relaxNG-gram.html: relaxNG.g gram2html.py
	$(PYTHON) gram2html.py relaxNG.g "Relax NG non-XML Grammar" >$@

kifExpr.py: kifExpr.g

kifExpr.html: kifExpr.g gram2html.py
	$(PYTHON) gram2html.py kifExpr.g "KIF Expression Grammar" >$@

kifForm.py: kifForm.g

kifForm.html: kifExpr.g gram2html.py
	$(PYTHON) gram2html.py kifForm.g "KIF Form Grammar" >$@

SemEnglish.html: SemEnglish.g gram2html.py
	$(PYTHON) gram2html.py SemEnglish.g "SemEnglish Grammar (from Seth)" >$@

log.rdf: log.n3
	$(PYTHON) cwm.py log.n3 --rdf > log.rdf


#ends

