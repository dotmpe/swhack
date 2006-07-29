#!/usr/bin/python
"""Correlate GPS data with Photo metadata

options:

--help      -h
--gpsData   -g   file   Input file directory with gpsData.n3
--verbose   -v

is or was http://www.w3.org/2000/10/swap/pim/day.py
"""

# Regular python library
import os, sys, time
from math import sin, cos, tan, sqrt
from urllib import urlopen

# SWAP  http://www.w3.org/2000/10/swap
from swap import myStore, diag, uripath, notation3, isodate
from swap.myStore import Namespace, formula, symbol, intern, bind, load
from swap.diag import progress
#import uripath
from swap.uripath import refTo, base

from swap.notation3 import RDF_NS_URI
import swap.notation3    	# N3 parsers and generators
from swap import  isodate  # for isodate.fullString

# import toXML 		#  RDF generator

# PyGarmon  http://www
#from garmin import Win32SerialLink, Garmin, UnixSerialLink, degrees, TimeEpoch, \
#    TrackHdr



RDF = Namespace(RDF_NS_URI)
# RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")
GPS = Namespace("http://hackdiary.com/ns/gps#")
bind("gps", "http://hackdiary.com/ns/gps#")  # Suggest as prefix in RDF file
WGS =  Namespace("http://www.w3.org/2003/01/geo/wgs84_pos#")
bind("wgs84",  "http://www.w3.org/2003/01/geo/wgs84_pos#")

EXIF = Namespace("http://www.w3.org/2000/10/swap/pim/exif#")
FILE = Namespace("http://www.w3.org/2000/10/swap/pim/file#")

monthName= ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


rdf_type = RDF.type


def compareByTime(a, b):
    if a[0] < b[0]: return -1
    if a[0] > b[0]: return +1
    return 0

################################ Map class

class Map:
    def __init__(self, minla, maxla, minlo, maxlo, svgStream=None):
    
	progress("Lat between %f and %f, Long %f and %f" % (minla, maxla, minlo, maxlo))
    
	if svgStream==None: self.wr = sys.stdout.write
	else: self.wr = svgStream.write
	
	self.marks = []  # List of marks on the map to avoid overlap
	
	self.midla = (minla + maxla)/2.0
	self.midlo = (minlo + maxlo)/2.0
	
	r_earth = 6400000.0 # (say) meters
	pi = 3.14159265358979323846 # (say)
	degree = pi/180
	
	m_per_degree = r_earth * pi /180
	subtended_y = (maxla - minla) * m_per_degree
	subtended_x = (maxlo - minlo) * m_per_degree * cos(self.midla*degree)
    
	progress("Area subtended  %f (E-W)  %f (N-S) meters" %(subtended_x, subtended_y))
	
	page_x = 800.0  # pixels
	page_y = 600.0
	max_x_scale = page_x / subtended_x
	max_y_scale = page_y / subtended_y
	self.pixels_per_m = min(max_x_scale, max_y_scale)    * 0.9  # make margins
	self.pixels_per_deg_lat = self.pixels_per_m * r_earth * pi /180
	self.pixels_per_deg_lon = self.pixels_per_deg_lat * cos(self.midla*degree)
	
	self.page_x = int(subtended_x * self.pixels_per_m/0.9)
	self.page_y = int(subtended_y * self.pixels_per_m/0.9)

	map_wid = subtended_x /0.9
	map_ht  = subtended_y /0.9

	tigerURI = ("http://tiger.census.gov/cgi-bin/mapper/map.gif?"
		+"&lat=%f&lon=%f&ht=%f&wid=%f&"
		+"&on=CITIES&on=majroads&on=miscell&on=places&on=railroad&on=shorelin&on=streets"
		+"&on=interstate&on=statehwy&on=states&on=ushwy&on=water"
		+"&tlevel=-&tvar=-&tmeth=i&mlat=&mlon=&msym=bigdot&mlabel=&murl=&conf=mapnew.con"
		+"&iht=%i&iwd=%i")  % (self.midla, self.midlo, map_ht, map_wid, self.page_y, self.page_x)

	progress("Getting Tiger map ", tigerURI)
	try:
	    gifStream = urlopen(tigerURI)
	    gifData = gifStream.read()
	    gifStream.close
	    progress("Saving tiger map")
	    saveStream = open("tiger.gif", "w")
	    saveStream.write(gifData)
	    saveStream.close()
	except IOError:
	    progress("Offline? No tigermap.")
	    
#	tigerURI = ("http://tiger.census.gov/cgi-bin/mapper/map.gif?&lat=%f&lon=%f&ht=%f"
#	    +"&wid=%f&&on=majroads&on=miscell&tlevel=-&tvar=-&tmeth=i&mlat=&mlon=&msym=bigdot&mlabel=&murl="
#	    +"&conf=mapnew.con&iht=%i&iwd=%i" ) % (self.midla, self.midlo,  maxla-minla, maxlo-minlo, self.page_y, self.page_x)


	self.wr("""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<!DOCTYPE svg PUBLIC '-//W3C//DTD SVG 1.0//EN'
 'http://www.w3.org/TR/2001/REC-SVG-20010904/DTD/svg10.dtd'>
<!-- Generated by @@@ -->
<svg
    width="%ipx"
    height="%ipx"
    xmlns='http://www.w3.org/2000/svg'
    xmlns:xlink='http://www.w3.org/1999/xlink'>
 <g>
 <rect x='0' y='0' width='%ipx' height='%ipx' style='fill:#ddffbb'/>
 <image width="100%%" height="100%%"  xlink:href="tiger.gif"/>
 """  %   (self.page_x,self.page_y, self.page_x,self.page_y))  #"
 

    def deg_to_px(self, lon, lat):
	"Note the lon, lat order on input like x,y"
#	progress("lon %f from center %f is offset %f, ie %f meters" % (
#		lon, self.midlo, lon - self.midlo, ((lon - self.midlo) * self.pixels_per_deg_lon)))
	return (int((lon - self.midlo) * self.pixels_per_deg_lon + self.page_x/2),
	    int(self.page_y/2 - (lat - self.midla) * self.pixels_per_deg_lat))
	    
    def startPath(self, lon, lat):
	x, y = self.deg_to_px(lon, lat)
	self.wr("  <path   style='fill:none; stroke:red' d='M %i %i " % (x,y))

    def straightPath(self, lon, lat):
	x, y = self.deg_to_px(lon, lat)
	self.wr("L %i %i " % (x,y))

    def skipPath(self, lon, lat):
	x, y = self.deg_to_px(lon, lat)
	self.wr("M %i %i " % (x,y))

    def endPath(self):
	self.wr("'/>\n\n")

    def photo(self, uri, lon, lat):
	x, y = self.deg_to_px(lon, lat)
	rel = refTo(base(), uri)
	while 1:
	    for x2, y2 in self.marks:
		if sqrt((x-x2)*(x-x2) + (y-y2)*(y-y2)) < 7:
		    x, y = x + 9, y - 9  # shift
		    break
	    else:
		break
	self.marks.append((x, y))
	self.wr("""<a xlink:href='%s'>
		    <rect x='%i' y='%i' width='14' height='8' style='fill:#777;stroke:black'/>
		    <circle cx='%i' cy='%i' r='3'/>
		    </a>""" %(rel, x-7, y-4, x, y))
	
    def close(self):
	self.wr("</g></svg>\n")
	




############################################################ Main program
    
if __name__ == '__main__':
    import getopt
    verbose = 0
    gpsData = "." # root of data
    outputURI = "correlation.n3"
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hvg:o:",
	    ["help",  "verbose", "gpsData=", "output="])
    except getopt.GetoptError:
        # print help information and exit:
        print __doc__
        sys.exit(2)
    output = None
    for o, a in opts:
        if o in ("-h", "--help"):
            print __doc__
            sys.exit()
        if o in ("-v", "--verbose"):
	    verbose = 1
        if o in ("-g", "--gpsData"):
            gpsData = a
        if o in ("-o", "--output"):
            outputURI = a

    if verbose: progress( "Loading Photo data...")
    f = load(gpsData  + "/PhotoMeta.n3")
    if verbose: progress( "Loaded.")
    ss = f.statementsMatching(pred=FILE.date)
    events = []
    for s in ss:
	ph = s.subject()
	photo = str(ph)
	date = str(s.object())
	da = f.any(subj=ph, pred=EXIF.dateTime)
	if da != None:
	    date = str(da)
	else:
	    progress("Warning: using file date %s for %s" %(date, photo))
	events.append((date, "P", (ph, photo)))
	if verbose: progress("%s: %s" %(date, photo))
    
#    photos.sort()

    if verbose: progress( "Loading GPS data...")
    f = load(gpsData + "/gpsData.n3")
    if verbose: progress( "Loaded.")
    records = f.each(pred=rdf_type, obj=GPS.Record)
    progress( `len(records)`, "records")
#    trackpoints = []
    for record in records:
	tracks = f.each(subj=record, pred=GPS.track)
	progress ("  ", `len(tracks)`, "tracks")
	for track in tracks:
	    points = f.each(subj=track, pred=GPS.trackpoint)
	    for point in points:
		t = str(f.the(subj=point, pred=WGS.time))
		la = str(f.the(subj=point, pred=WGS.lat))
		lo = str(f.the(subj=point, pred=WGS.long))
		events.append((t, "T", (la, lo)))

    events.sort(compareByTime)
    
    last = None
    n = len(events)

    if verbose: progress( "First event:" , `events[0]`, "Last event:" , `events[n-1]`)

    minla, maxla = 90.0, 0.0
    minlo, maxlo = 400.0, -400.0
    conclusions = formula()
    for i in range(n):
	dt, ty, da = events[i]
	if ty == "T": # Trackpoint
	    last = i
	    (la, lo) = float(da[0]), float(da[1])
	    if la < minla: minla = la
	    if la > maxla: maxla = la
	    if lo < minlo: minlo = lo
	    if lo > maxlo: maxlo = lo
	elif ty == "P":
	    ph, photo = da
	    if last == None:
		progress("%s: Photo %s  before any trackpoints" %(dt, photo))
		continue
	    j = i+1
	    while j < n:
		dt2, ty2, da2 = events[j]
		if ty2 == "T": break
		j = j+1
	    else:
		progress( "%s: Photo %s off the end of trackpoints"% (dt, photo))
		continue
	    t = isodate.parse(dt)
	    dt1, ty1, (la1, lo1) = events[last]
	    lat1, long1 = float(la1), float(lo1)
	    t1 = isodate.parse(dt1)
	    dt2, ty2, (la2, lo2) = events[j]
	    lat2, long2 = float(la2), float(lo2)
	    t2 = isodate.parse(dt2)
	    delta = t2-t1
	    progress( "%s: Photo %s  between trackpoints %s and %s" %(dt, da, dt1, dt2))
#	    print "    Delta", delta, "seconds between", events[last], "and", events[j]
	    a = (t - t1) / (t1-t2)
	    lat = lat1 +  a * (lat2-lat1)
	    long = long1 + a * (long2-long1)
	    progress( "%s: Before (%f, %f)" % (dt1, lat1, long1))
	    progress( "%s: Guess  (%f, %f)" % (dt, lat, long))
	    progress( "%s: After  (%f, %f)" % (dt2, lat2, long2))
	    
	    where = conclusions.newBlankNode()
	    conclusions.add(ph, GPS.approxLocation, where)
	    conclusions.add(where, WGS.lat, lat)
	    conclusions.add(where, WGS.long, long)

    
#	    guess = isodate.fullString(...)

    progress("Start Output")
    print conclusions.close().n3String(base=base())

    svgStream = open("map.svg", "w")
    map = Map(minla, maxla, minlo, maxlo, svgStream=svgStream)

    pathpoint = None
    for i in range(n):
	dt, ty, da = events[i]
	if ty == "T": # Trackpoint
	    (la, lo) = float(da[0]), float(da[1])
	    if pathpoint == None:
		map.startPath(lo, la)
		pathpoint = 1
	    else:
		map.straightPath(lo, la)
	elif ty == "P":
	    pass
    map.endPath()


    for st in conclusions.statementsMatching(pred=GPS.approxLocation):
	photo = st.subject()
	loc = st.object()
	long = conclusions.the(subj=loc, pred=WGS.long)
	lat = conclusions.the(subj=loc, pred=WGS.lat)
	progress("Photo %s at lat=%s, long=%s" %(photo.uriref(), lat, long))
	la, lo = float(lat), float(long)
	map.photo(photo.uriref(), lo, la)
    map.close()
    svgStream.close()

def min(x, y):
	if x<y: return x
	return y

#ends
