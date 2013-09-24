

# Almanac.py


# REFERENCES ========================
#
# http://www.astro.uu.nl/~strous/AA/en/reken/zonpositie.html
# http://www.astro.uu.nl/~strous/AA/en/reken/juliaansedag.html
# http://en.wikipedia.org/wiki/Sunrise_equation
# http://en.wikipedia.org/wiki/Julian_Day
# http://rhodesmill.org/pyephem/
# http://aa.usno.navy.mil/data/docs/RS_OneDay.php
#


# IMPORTS ===========================
import os, sys, math
from datetime import *
import ephem
from xml.etree import ElementTree
import traceback
import arcpy
from arcpy import env


# ARGUMENTS =========================
#latitudeOfObserver = "34.428"
#longitudeOfObserver = "-115.689"
#inputDate = "4/15/2010"
#utcZone = "UTC-08, U"
inputFeatures = arcpy.GetParameterAsText(0)
inputDate = arcpy.GetParameterAsText(1)
utcZone = arcpy.GetParameterAsText(2)
outputFile = arcpy.GetParameterAsText(3)


# CONSTANTS =========================
sun = ephem.Sun() # Sun PyEphem body
moon = ephem.Moon() # Moon PyEphem body


# LOCALS ============================
almanac = {} # dictionary storing almanac info


# FUNCTIONS =========================
def DDtoDMSstring(dd): # Convert Decimal Degrees (DD.dddd) to Degrees Minutes Seconds (DDD:MM:SS)
    dd = float(dd)
    degrees = int(math.trunc(dd))
    minutes = int(math.trunc(math.fabs(dd - degrees) * 60))
    minDec = math.fabs(dd - degrees) * 60
    seconds = math.fabs(minutes - minDec) * 60
    seconds = round(seconds)
    dms = str(degrees) + ":" + str(minutes) + ":" + str(seconds)
    return dms


def round(a): # rounds float up or down & returns integer
    # positive numbers only
    dec = a - math.trunc(a)
    if dec >= 0.5: return int(math.ceil(a))
    if dec < 0.5: return int(math.floor(a))


def UTCDictionary():
    # Dictionary of the time zones in the esriTimeZones.xml file   
    installDir = arcpy.GetInstallInfo('desktop')['InstallDir']
    tzFile = os.path.join(installDir,r"TimeZones\esriTimeZones.xml")
    lUTC = {}
    tree = ElementTree.parse(tzFile)
    root = tree.getroot()
    for elem in root:
      tzName = elem.find("DisplayName").text
      tzDefaultBias = int(elem.find("DefaultRule/Bias").text)
      tzHourOffset = int(math.modf(float(tzDefaultBias)/60.0)[1])
      tzMinuteOffset = int(math.fabs(math.fmod(tzDefaultBias,60)))
      tzOffset = (tzHourOffset,tzMinuteOffset,0)
      lUTC[tzName] = tzOffset
    return lUTC
    

# MAIN ==============================
try:

    UTC = UTCDictionary()

    # convert date to year, month, day
    month = int(inputDate.split("/")[0])
    day = int(inputDate.split("/")[1])
    year = int(inputDate.split("/")[2])

    offsetHour = UTC[utcZone][0]
    offsetMinute = UTC[utcZone][1]
    offsetSecond = UTC[utcZone][2]
    timeDelta = timedelta(hours=offsetHour, minutes=offsetMinute, seconds=offsetSecond)
    d = ephem.Date(datetime(year,month,day,0,0,0) + timeDelta)
    almanac["Report Date"] = d.datetime() + timeDelta
    
    
    # get Lat & Lon from input point feature
    #desc = arcpy.Describe(inputFeatures)
    shapefieldname = "SHAPE"#desc.ShapeFieldName
    rows = arcpy.SearchCursor(inputFeatures)
    row = rows.next()
    feat = row.getValue(shapefieldname)
    pnt = feat.getPart()
    latitudeOfObserver = pnt.Y
    longitudeOfObserver = pnt.X
    del pnt, feat, row, rows
    
    # Set observer
    observer = ephem.Observer()
    observer.lat = DDtoDMSstring(latitudeOfObserver)
    observer.long = DDtoDMSstring(longitudeOfObserver)
    observer.date = d
    almanac["Report UTC Zone"] = utcZone
    almanac["Report Location"] = "%s, %s" % (str(longitudeOfObserver),str(latitudeOfObserver))
    
    # Sun
    observer.horizon = 0
    sunrise = observer.next_rising(sun)
    suntransit = observer.next_transit(sun)
    sunset = observer.next_setting(sun)
    almanac["Sunrise"] = sunrise.datetime() + timeDelta
    almanac["Solar Transit"] = suntransit.datetime() + timeDelta
    almanac["Sunset"] = sunset.datetime() + timeDelta
    
    # Lunar
    moonrise = observer.previous_rising(moon)
    moontransit = observer.next_transit(moon)
    moonset = observer.next_setting(moon)
    moonphase = str(ephem.Moon(d).moon_phase * 100) + "% illuminated"
    nextNewMoon = ephem.next_new_moon(d)
    nextFullMoon = ephem.next_full_moon(d)
    almanac["Moonrise"] = moonrise.datetime() + timeDelta
    almanac["Moon Transit"] = moontransit.datetime() + timeDelta
    almanac["Moonset"] = moonset.datetime() + timeDelta
    almanac["Lunar Phase"] = moonphase
    almanac["Next New Moon"] = nextNewMoon.datetime() + timeDelta
    almanac["Next Full Moon"] = nextFullMoon.datetime() + timeDelta
    # Civil Twilight (6 degrees below horizon)
    observer.horizon = "-6:00:00"
    civilTwilightBegin = observer.previous_rising(sun) #, use_center=True)
    civilTwilightEnd = observer.next_setting(sun) #, use_center=True)
    almanac["Civil Twilight Begin"] = civilTwilightBegin.datetime() + timeDelta
    almanac["Civil Twilight End"] = civilTwilightEnd.datetime() + timeDelta
    
    # Nautical Twilight (12 degrees below horizon)
    observer.horizon = "-12:00:00"
    nautTwilightBegin = observer.previous_rising(sun) #, use_center=True)
    nautTwilightEnd = observer.next_setting(sun) #, use_center=True)
    almanac["Nautical Twilight Begin"] = nautTwilightBegin.datetime() + timeDelta
    almanac["Nautical Twilight End"] = nautTwilightEnd.datetime() + timeDelta
    
    # Astronomical Twilight (18 degrees below horizon)
    observer.horizon = "-18:00:00"
    astroTwilightBegin = observer.previous_rising(sun) #, use_center=True)
    astroTwilightEnd = observer.next_setting(sun) #, use_center=True)
    almanac["Astronomical Twilight Begin"] = astroTwilightBegin.datetime() + timeDelta
    almanac["Astronomical Twilight End"] = astroTwilightEnd.datetime() + timeDelta
    
    # if GP is set to overwrite remove existing output file
    if (env.overwriteOutput == True):
        if (os.path.exists(outputFile)): os.remove(outputFile)
    
    # Write out the report to HTML file
    reportFile = open(outputFile,"w")
    reportFile.write(r'<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"  "http://www.w3.org/TR/html4/strict.dtd">')
    reportFile.write(r'<html lang="en">')
    reportFile.write(r'<head><title>"Almanac Report"</title></head>')
    reportFile.write(r'<body>')
    reportFile.write(r'<P></P>')
    reportFile.write(r'<P>Report Date: ' + str(almanac["Report Date"]) + r'</P>')
    reportFile.write(r'<P>Report UTC Zone: ' + str(almanac["Report UTC Zone"]) + r'</P>')
    reportFile.write(r'<P>Report Location (Long,Lat): ' + str(almanac["Report Location"]) + r'</P>')
    reportFile.write(r'<P></P>')
    reportFile.write(r'<P>Solar Info</P>')
    reportFile.write(r'<table BORDER=1>')
    reportFile.write(r'<TR><TD>Astronomical Twilight Begin</TD><TD>' + str(almanac["Astronomical Twilight Begin"]) + r'</TD></TR>')
    reportFile.write(r'<TR><TD>Nautical Twilight Begin</TD><TD>' + str(almanac["Nautical Twilight Begin"]) + r'</TD></TR>')
    reportFile.write(r'<TR><TD>Civil Twilight Begin</TD><TD>' + str(almanac["Civil Twilight Begin"]) + r'</TD></TR>')
    reportFile.write(r'<TR><TD>Sunrise</TD><TD>' + str(almanac["Sunrise"]) + r'</TD></TR>')
    reportFile.write(r'<TR><TD>Solar Transit</TD><TD>' + str(almanac["Solar Transit"]) + r'</TD></TR>')
    reportFile.write(r'<TR><TD>Sunset</TD><TD>' + str(almanac["Sunset"]) + r'</TD></TR>')
    reportFile.write(r'<TR><TD>Civil Twilight End</TD><TD>' + str(almanac["Civil Twilight End"]) + r'</TD></TR>')
    reportFile.write(r'<TR><TD>Nautical Twilight End</TD><TD>' + str(almanac["Nautical Twilight End"]) + r'</TD></TR>')
    reportFile.write(r'<TR><TD>Astronomical Twilight End</TD><TD>' + str(almanac["Astronomical Twilight End"]) + r'</TD></TR>')
    reportFile.write(r'</table>')
    reportFile.write(r'<P></P>')
    reportFile.write(r'<P>Lunar Info</P>')
    reportFile.write(r'<table BORDER=1>')
    reportFile.write(r'<TR><TD>Moonrise</TD><TD>' + str(almanac["Moonrise"]) + r'</TD></TR>')
    reportFile.write(r'<TR><TD>Moon Transit</TD><TD>' + str(almanac["Moon Transit"]) + r'</TD></TR>')
    reportFile.write(r'<TR><TD>Moonset</TD><TD>' + str(almanac["Moonset"]) + r'</TD></TR>')
    reportFile.write(r'<TR><TD>Moon Phase (%)</TD><TD>' + str(almanac["Lunar Phase"]) + r'</TD></TR>')
    reportFile.write(r'<TR><TD>Next New Moon</TD><TD>' + str(almanac["Next New Moon"]) + r'</TD></TR>')
    reportFile.write(r'<TR><TD>Next Full Moon</TD><TD>' + str(almanac["Next Full Moon"]) + r'</TD></TR>')
    reportFile.write(r'</table>')
    reportFile.write(r'<P></P>')
    reportFile.write(r'</body>')
    reportFile.write(r'</html>')
    reportFile.close()
    
    # Set output file
    arcpy.SetParameterAsText(3,outputFile)
    arcpy.AddMessage("Report file is in " + str(outputFile))

except arcpy.ExecuteError: 
    # Get the tool error messages 
    msgs = arcpy.GetMessages(2) 
    arcpy.AddError(msgs) 
    print msgs

except:
    # Get the traceback object
    tb = sys.exc_info()[2]
    tbinfo = traceback.format_tb(tb)[0]

    # Concatenate information together concerning the error into a message string
    pymsg = "PYTHON ERRORS:\nTraceback info:\n" + tbinfo + "\nError Info:\n" + str(sys.exc_info()[1])
    msgs = "ArcPy ERRORS:\n" + arcpy.GetMessages(2) + "\n"

    # Return python error messages for use in script tool or Python Window
    arcpy.AddError(pymsg)
    arcpy.AddError(msgs)

    # Print Python error messages for use in Python / Python Window
    print pymsg + "\n"
    print msgs

    