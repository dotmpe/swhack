# An attempt to se how one can get into MS Outlook from Python
# Ideal - to export to RDF.

# Refs:
# http://www.oreilly.com/catalog/pythonwin32/chapter/ch12.html

# Derived from
# $Id$
# <http://www.w3.org/Tools/1998/07contactlog/contactlog.py>
#
# This code sort of works, at least to demonstrate python/Outlook
# integration. I got through two of the categories of stylized
# data that I keep in my Pilot Address book (caller-id info,
# and business cards; the others are email, post, etc.)
# Then I got bored.
# Especially watch out for stuff marked with @@.
#
# But I'm documenting it carefully,
# because I've been looking for these clues for
# *months* and I don't want to lose them.
# And I'm releasing it. Share and Enjoy.

# Dan Connolly
# <connolly@w3.org>
# http://www.w3.org/People/Connolly/

# Copyright � 1998 World Wide Web Consortium,
# (Massachusetts Institute of Technology, Institut National de
# Recherche en Informatique et en Automatique, Keio University). All
# Rights Reserved. 
#
# Permission to use, copy, modify, and distribute this software
# and its documentation for any purpose and without fee or
# royalty is hereby granted, per the terms and conditions in
#
# W3C IPR SOFTWARE NOTICE
# http://www.w3.org/COPYRIGHT
# September 1997 

# This module depends on standard and built-in python modules, per
# Python Library Reference
#                        April 14, 1998
#                        Release 1.5.1
# http://www.python.org/doc/lib/lib.html

import string, StringIO

# It also uses the win32com package
# maintained by Mark Hammond
# http://www.python.org/windows/win32com/
#
# specifically, as documented in
# PythonWin Help
# Help file built: 04/26/98
# available in http://www.python.org/windows/win32all/win32all.exe

# Here we bind to the the actual Outlook 98 runtime,
# whose interface is documented in a
# Microsoft help file, "Microsoft Outlook Visual Basic"
#
# I found the help file via the Microsoft Knowledge Base:
#
# "OL98: How to Install Visual Basic Help"
# Last reviewed: April 1, 1998
# Article ID: Q183220
# http://support.microsoft.com/support/kb/articles/q183/2/20.asp

from win32com.client import gencache



# The following lines are generated by makepy
#
#Outlook 98 Type Library
# {00062FFF-0000-0000-C000-000000000046}, lcid=0, major=8, minor=5
# Use these commands in Python code to auto generate .py support
#outlook = gencache.EnsureModule('{00062FFF-0000-0000-C000-000000000046}', 0, 8, 5)

# Try python /Python16/win32com/client/makepy.py -i -d to get the magic numbers:
# This is for Outlook 2000 9.0:
outlook = gencache.EnsureModule('{00062FFF-0000-0000-C000-000000000046}', 0, 9, 0)

# The only namespace supported in Outlook '98
# see "Microsoft Outlook Visual Basic"
MAPI = "MAPI"


# Hard-coded configuration
# probably should use sys.argv, but I didn't bother...
Inf = "C:\\winnt\\profiles\\connolly\\desktop\\980728pilot-addr.txt"

# for other folks to do testing, here are a couple lines from that file:
_test_data = \
"""Last Name	First Name	Job Title	Company	Business Phone	Home Phone	Business Fax	Other Phone	E-mail	Street Address	City	State	Zip/Postal Code	Country	Location	Birthday	User Field 1	User Field 2	User Field 3	Private	Categories
"AAbrahamson"	"Dr. David M"			"+353-1-608-1716"				"cavid@cs.tcd.ie"	"Trinity College"	"Dublin 2, Ireland"						"1996-11"		"lunch 96-11-13 ISO HTML Boston lunch"	"0"	"Business Card"
"""

def main():
	oapp = outlookToN3()

	_version = "$Id$"[1:-1]
	print "# Outlook data extractde by"
	print "#   ", _version
	print
	
	print "# Calendar:"
	oapp.getFolder(outlook.constants.olFolderCalendar)
	
	print "# Contacts:"
	oapp.getFolder(outlook.constants.olFolderContacts)

	print "# ENDS"
	


# DWC: outlook.Application is the Application class, per
# the type library and help file cited above.
#
# It integrates completely seamlessly into the python
# object model.
#
# Hence, for methods such as GetNamespace, see
# the help file. I found the following article quite
# helpful as well. The examples are in visual basic, but
# the translation to python is straightforward.
#
# The Microsoft Outlook 97 Automation Server Programming Model
#  Last Updated: June 26, 1998 
# http://www.microsoft.com/OutlookDev/Articles/Outprog.htm
#

def _toString(x):
	""" In N3 everything is represented as a string (at the moment), so we need
	to turn everything into a string withoyt Python encoding.
	"""
	if type(x) is type(' '): return '"'+x+'"'
	if type(x) is type(6): return '"'+`x`+'"'
	return `x`   # @@@ unhandled things

class outlookToN3(outlook.Application):
	def findContact(self, filter):
		_mapi = self.GetNamespace(MAPI)

#		_c = outlook.OlDefaultFolders.olFolderContacts
		_c = outlook.constants.olFolderContacts
#		contacts = _mapi.GetDefaultFolder(outlook.OlDefaultFolders.olFolderContacts)
		contacts = _mapi.GetDefaultFolder(outlook.constants.olFolderContacts)

		return contacts.Items.Find(filter)

	def getFolder(self, what):
		_mapi = self.GetNamespace(MAPI)
		_c = outlook.constants.olFolderCalendar
		# Result is of type MAPIFolder
		cal = _mapi.GetDefaultFolder(what)
		print "\n# Folder %i:" % what
		self._getItem(cal)
		
		list = cal.Items
		n = len(list)
		print " util:item "
		for i in range(n):
			item = list[i+1] # GetFirst()
			self._getItem(item)
			if i<n-1: print ","
		print "."
			
	def _getItem(self, item):
		gkeys = item._prop_map_get_.keys()
		pkeys = item._prop_map_put_.keys()		
		print "\n  [ ",
		for k in range(len(gkeys)):
			key = gkeys[k]
			_w = (key in pkeys)		# Is this writable?
			if not _w : pass # print "              # Read only:", key
			else:
				if key == "End":
					pass  # Breakpoint me! @@ ;-)
				x = item.__getattr__(key)
				if x != "":
					print "%-32s  %s" % (key, _toString(x)),
					if k < len(gkeys)-1: print ";\n    ",
		print " . ]"
		
	def incomingCall(self, name, num, isotime):
		# convert caller-id format: 333-555-1212
		# to Outlook format: (333) 555-1212
		if len(num) == 12:
			num = "(%s) %s" % (num[:3], num[4:])
			
		ji = self.CreateItem(outlook.OlItemType.olJournalItem)
		ji.Type = "Phone call" # set icon?
		
		# stuff the original caller-id data away somewhere
		# I'm not confident this UserProperties code
		# works... wierdness around byRef args or something.
		# I could never
		# find the userproperties for a journal item
		# in the Outlook GUI to check one way or the other.
		p = ji.UserProperties.Add("CallerIDName", outlook.OlUserPropertyType.olText)
		p.Value = name
		p = ji.UserProperties.Add("CallerIDNumber", outlook.OlUserPropertyType.olText)
		p.Value = num

		#@@ mobile, other phone numbers...
		contact = self.findContact('[Business Phone] = "%s" or [Home Phone] = "%s"' % (num, num))
		
		if contact:
			if contact.FullName:
					name = contact.FullName
			ji.Companies = contact.CompanyName
		else:
			contact = self.CreateItem(outlook.OlItemType.olContactItem)
			contact.FullName = name
			contact.BusinessTelephoneNumber = num
			contact.Save()

		ji.Recipients.Add(name)

		
		t = iso2vb(isotime)
		ji.Start = t
		
		ji.Subject = "Call from %s %s" % (name or num, t)
		ji.Save()
		#ji.Display() #@@
		return ji, contact

	def testAdd(self):
		self.logBusinessCard(
			"Aardvark", "Adam", "Mr.", "Acme", "555-1234", "555-5678", "AARDVARK@ACME.COM",
			"Wood St", "Anytown", "AK", "12345", "USA", "", None)
		
	def logBusinessCard(self,
		family,given,title,company,work,fax,email,
		street,city,state,zip,country,isodate,note):
		
		contact = self.findContact(
				'[Last Name] = "%s" and [First Name] = "%s" and [Company] = "%s"' % (family, given, company))
		if not contact:
			print "@@ new contact"
#			contact = self.CreateItem(outlook.OlItemType.olContactItem)
			contact = self.CreateItem(outlook.constants.olContactItem)
			contact.LastName = family
			contact.FirstName = given
			contact.CompanyName = company
		contact.JobTitle = title
		contact.BusinessTelephoneNumber = work
		contact.BusinessFaxNumber = fax
		contact.BusinessAddressStreet = street
		contact.BusinessAddressCity = city
		contact.BusinessAddressState = state
		contact.BusinessAddressPostalCode = zip
		contact.BusinessAddressCountry = country

		#@@ don't clobber email
		contact.Email1Address = email
			

		if isodate:
			ji = self.CreateItem(outlook.OlItemType.olJournalItem)
			ji.Start = iso2vb(isodate)
			ji.Type = "Conversation" # or perhaps meeting?
			ji.Recipients.Add(contact.FullName)
			ji.Companies = company
			ji.Body = note
			ji.Subject = "Business Card %s %s" % (contact.FullName, company)
			#ji.Display() #@@
			#@@ include scanned image of card?

			ji.Save()
		else:
			ji = None
			if note:
				if contact.Body:
					contact.Body = contact.Body + '\n' + note
				else:
					contact.Body = note
		contact.Save()
		
		return ji, contact
		
	def addPilotAddress(self, row):
		family,given,title,company,work,home,fax,other,email, \
			street,city,state,zip,country,airport,birthday, \
			updated,expired,note,private,category = row
		if category == "Caller-id":
			ji, c = self.incomingCall(family, work, updated)
			if note:
				ji.Body = note
			#@@ translate private to Sensitivity
			ji.Save()
			
			if given or title or company or home \
				or fax or other or email or street \
				or city or state or zip or country or airport \
				or birthday or expired:
				print "@@info besides family, work, updated, note, private:",\
					row
		elif category == "Business Card":
			if updated[-5:] == " card":
				updated = updated[:-5]
			ji, c = self.logBusinessCard(family,given,title,company,
				work,fax,email,
				street,city,state,zip,country,updated,note)
			ji.Display() #@@debugging
			c.Display()
			#@@ other fields: home phone, airport?
			# birthday, expired, private	
		else:
			print "@@category not yet supported:", category, family, given, company

def iso2vb(isotime):
	# YYYY-MM-DDTHH:MM:SS
	# raises ??? exception when parts are missing?
	year = isotime[:4]
	month = isotime[5:7]
	day = isotime[8:10] or '1' ## @# only month given
	hour = isotime[11:13]
	minute = isotime[14:16]
	second = isotime[17:19]
	ret = month + '/' + day + '/' + year
	if hour and minute:
		ret = ret + ' ' + hour + ':' + minute
		if second:
			ret = ret + ':' + second
	print "@@convdate: ", isotime, ret
	return ret

	
def nextrow(fp):
	# A simple state-machine implementation of Windows
	# tab-delimited file format with quoted fields.
	# I'm not sure if this really
	# does CRLF's right.
	# There are faster ways to do this, I'm sure...
	s = 'start'
	row = ()
	field = ""
	while 1:
		c = fp.read(1)
		if not c:
			if field or len(row):
				raise IOError, "bad end of file"
			return None
		if s == 'start':
			if c == "\n":
				row = row + (field,)
				return row
			elif c == "\t":
				row = row + (field,)
				field = ''
			elif c == '"':
				s = 'quoted'
			else:
				field = field + c
		elif s == 'quoted':
			if c == '"':
				s = 'start'
			elif c == "\\":
				s = 'escaped'
			else:
				field = field + c
		elif s == 'escaped':
			field = field + c
			s = 'quoted'
		else:
			raise RuntimeError, 'bad case'
			
		
if __name__ == '__main__': main()

