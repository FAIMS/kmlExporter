'''
Python:
    accept epsg as argument

    copy into new DB
    create structure for 3nf
    add geometry columns
    Call Ruby:
        Write responses into 3nf
    write geometries into 3nf tables

    call shapefile tool


    TODO:
        convert ruby calls into rbenv or system ruby calls
        figure out how shell script wrapper needs to work for exporter


'''

import unicodedata
import sqlite3
import csv, codecs, cStringIO
from xml.dom import minidom
import sys
import pprint
import glob
import json
import os
import shutil
import re
import zipfile
import subprocess
import glob
import tempfile
import errno
import imghdr
import bz2
import tarfile
import platform
import lsb_release
import mimetypes, magic
import traceback
import glob
from shapely.wkb import dumps, loads
from collections import defaultdict
from pprint import pprint
from fastkml import kml
import shapely
import zipfile
try:
    import zlib
    compression = zipfile.ZIP_DEFLATED
except:
    compression = zipfile.ZIP_STORED

modes = { zipfile.ZIP_DEFLATED: 'deflated',
          zipfile.ZIP_STORED:   'stored',
          }

print sys.argv

class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")

class UnicodeReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        return self

class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def convertBuffer(self, obj):

        #print type(obj)        
        
        if isinstance(obj, basestring):         
            #print obj.encode("utf-8", errors="replace")
            return obj.encode("utf-8", errors="replace").replace('"',"''")
        if isinstance(obj, buffer):         
            bufferCon = sqlite3.connect(':memory:')
            bufferCon.enable_load_extension(True)
            bufferCon.load_extension(LIBSPATIALITE)
            foo = bufferCon.execute("select astext(?);", ([obj])).fetchone()            
            return foo[0]
        if obj == None:
            return ""
        return obj



    def writerow(self, row):
        self.writer.writerow(['"%s"' % self.convertBuffer(s) for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data.replace('"""','"').replace('"None"',''))
        # empty queue
        self.queue.truncate(0)
        self.stream.flush()

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)
        


    



def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def upper_repl(match):
    if (match.group(1) == None):
        return ""
    return match.group(1).upper()

def clean(str):
     out = re.sub(" ([a-z])|[^A-Za-z0-9]+", upper_repl, str)     
     return out

def cleanWithUnder(str):
     out = re.sub("[^a-zA-Z0-9]+", "_", str)     
     return out  

def makeSurePathExists(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise


originalDir = sys.argv[1]
exportDir = tempfile.mkdtemp()+"/"
finalExportDir = sys.argv[2]+"/"
importDB = originalDir+"db.sqlite3"
exportDB = exportDir+"shape.sqlite3"
shapeDB = exportDir+"noannotation.sqlite3"
jsondata = json.load(open(originalDir+'module.settings'))
srid = jsondata['srid']
arch16nFiles=[]
for file in glob.glob(originalDir+"*.properties"):
    arch16nFiles.append(file)

arch16nFile = next((s for s in arch16nFiles if '.0.' in s), arch16nFiles[0])
# print jsondata
moduleName = clean(jsondata['name'])
fileNameType = "Identifier" #Original, Unchanged, Identifier



if lsb_release.get_lsb_information()['RELEASE'] == '16.04':
    LIBSPATIALITE = 'mod_spatialite.so'
else:
    LIBSPATIALITE = 'libspatialite.so.5'


images = None
overrideFormattedIdentifiers = None
try:
    foo= json.load(open(sys.argv[3],"r"))
    # print foo["Export Images and Files?"]
    if (foo["Export Images and Files?"] != []):
        images = True
    else:
        images = False
    # Ugh. But the interface is buggy.
    if (foo["Export identifier components in plain as well as formatted state (if in doubt, leave the setting as is)?"] != []):
        overrideFormattedIdentifiers = False
    else:
        overrideFormattedIdentifiers = True
except:
    sys.stderr.write("Json input failed")
    images = True

print "Exporting Images %s" % (images)
print "Overwriting Identifier FormatStrings %s" % (overrideFormattedIdentifiers)
print foo
def zipdir(path, zip):
    for root, dirs, files in os.walk(path):
        for file in files:
            zip.write(os.path.join(root, file))


try:
    os.remove(exportDB)
except OSError:
    pass

importCon = sqlite3.connect(importDB)
importCon.enable_load_extension(True)
importCon.load_extension(LIBSPATIALITE)
exportCon = sqlite3.connect(exportDB)
exportCon.enable_load_extension(True)
exportCon.load_extension(LIBSPATIALITE)



exportCon.execute("select initSpatialMetaData(1)")
'''
for line in importCon.iterdump():
    try:
        exportCon.execute(line)
    except sqlite3.Error:       
        pass
'''     
            
exifCon = sqlite3.connect(exportDB)
exifCon.row_factory = dict_factory
exportCon.enable_load_extension(True)
exportCon.load_extension(LIBSPATIALITE)
exportCon.row_factory = dict_factory

  
exportCon.execute("create table keyval (key text, val text);")

f = open(arch16nFile, 'r')
for line in f:
    if "=" in line:
        keyval = line.replace("\n","").replace("\r","").decode("utf-8").split('=', 1)
        keyval[0] = '{'+keyval[0]+'}'
        
        exportCon.execute("replace into keyval(key, val) VALUES(?, ?)", keyval)
f.close()







for aenttypeid, aenttypename in importCon.execute("select aenttypeid, aenttypename from aenttype"): 
    aenttypename = clean(aenttypename)
    attributes = ['identifier', 'createdBy', 'createdAtGMT', 'modifiedBy', 'modifiedAtGMT']
    for attr in importCon.execute("select distinct attributename from attributekey join idealaent using (attributeid) where aenttypeid = ? group by attributename order by aentcountorder", [aenttypeid]):
        attrToInsert = clean(attr[0])
        if attrToInsert not in attributes:
            attributes.append(attrToInsert)
    attribList = " TEXT, \n\t".join(attributes)
    createStmt = "Create table if not exists %s (\n\tuuid TEXT PRIMARY KEY,\n\t%s TEXT);" % (aenttypename, attribList)

    exportCon.execute(createStmt)

geometryColumns = []
for row in importCon.execute("select aenttypename, geometrytype(geometryn(geospatialcolumn,1)) as geomtype, count(distinct geometrytype(geometryn(geospatialcolumn,1))) from latestnondeletedarchent join aenttype using (aenttypeid) where geomtype is not null group by aenttypename having  count(distinct geometrytype(geometryn(geospatialcolumn,1))) = 1"):
    geometryColumns.append(row[0])
    geocolumn = "select addGeometryColumn('%s', 'geospatialcolumn', %s, '%s', 'XY');" %(clean(row[0]),srid,row[1]);
    
    exportCon.execute(geocolumn)





for aenttypename, uuid, createdAt, createdBy, modifiedAt, modifiedBy,geometry in importCon.execute("select aenttypename, uuid, createdAt || ' GMT', createdBy, datetime(modifiedAt) || ' GMT', modifiedBy, geometryn(transform(geospatialcolumn,casttointeger(%s)),1) from latestnondeletedarchent join aenttype using (aenttypeid) join createdModifiedAtBy using (uuid) order by createdAt" % (srid)):
    
    if (aenttypename in geometryColumns):       
        insert = "insert into %s (uuid, createdAtGMT, createdBy, modifiedAtGMT, modifiedBy, geospatialcolumn) VALUES(?, ?, ?, ?, ?, ?)" % (clean(aenttypename))
        exportCon.execute(insert, [str(uuid), createdAt, createdBy, modifiedAt, modifiedBy, geometry])
    else:
        insert = "insert into %s (uuid, createdAtGMT, createdBy, modifiedAtGMT, modifiedBy) VALUES(?, ?, ?, ?, ?)" % (clean(aenttypename))
        exportCon.execute(insert, [str(uuid), createdAt, createdBy, modifiedAt, modifiedBy])



try:
    os.remove(exportDir+'shape.out')
    os.remove(exportDir+'noannotation.out')
except OSError:
    pass


subprocess.call(["bash", "./format.sh", originalDir, exportDir, exportDir])



updateArray = []

for line in codecs.open(exportDir+'shape.out', 'r', encoding='utf-8').readlines():  
    out = line.replace("\n","").replace("\\r","").split("\t")
    #print "!!%s -- %s!!" %(line, out)
    if (len(out) ==4):      
        update = "update %s set %s = ? where uuid = %s;" % (clean(out[1]), clean(out[2]), out[0])
        data = (unicode(out[3].replace("\\n","\n").replace("'","''")),)
        # print update, data
        exportCon.execute(update, data)



if (overrideFormattedIdentifiers):
    subprocess.call(["bash", "./override.sh", originalDir, exportDir, exportDir])

    for line in codecs.open(exportDir+'override.out', 'r', encoding='utf-8').readlines():  
        out = line.replace("\n","").replace("\\r","").split("\t")
        #print "!!%s -- %s!!" %(line, out)
        if (len(out) ==4):      
            update = "update %s set %s = ? where uuid = %s;" % (clean(out[1]), clean(out[2]), out[0])
            data = (unicode(out[3].replace("\\n","\n").replace("'","''")),)
            # print update, data
            exportCon.execute(update, data)


exportCon.commit()
files = ['shape.sqlite3', 'noannotation.sqlite3']

if (overrideFormattedIdentifiers):
    files.append('override.out')
    files.append('shape.out')




if images:
    attachedfiledump = []
    for directory in importCon.execute("select distinct aenttypename, attributename from latestnondeletedaentvalue join attributekey using (attributeid) join latestnondeletedarchent using (uuid) join aenttype using (aenttypeid) where attributeisfile is not null and measure is not null"):
        makeSurePathExists("%s/%s/%s" % (exportDir,clean(directory[0]), clean(directory[1])))

    filehash = defaultdict(int)

    outputFilename =defaultdict(int)
    outputAent = defaultdict(int)
    mime = magic.Magic(mime=True)
    print "* File list exported:"
    for filename in importCon.execute("select uuid, measure, freetext, certainty, attributename, aenttypename from latestnondeletedaentvalue join attributekey using (attributeid) join latestnondeletedarchent using (uuid) join aenttype using (aenttypeid) where attributeisfile is not null and measure is not null"):
        try:        
            oldPath = filename[1].split("/")
            oldFilename = oldPath[2]
            aenttypename = clean(filename[5])
            attributename = clean(filename[4])
            newFilename = "%s/%s/%s" % (aenttypename, attributename, oldFilename)
            if os.path.isfile(originalDir+filename[1]):
                if (fileNameType == "Identifier"):
                    # print filename[0]
                    
                    filehash["%s%s" % (filename[0], attributename)] += 1
                    

                    foo = exportCon.execute("select identifier from %s where uuid = %s" % (aenttypename, filename[0]))
                    identifier=cleanWithUnder(foo.fetchone()['identifier'])

                    r= re.search("(\.[^.]*)$",oldFilename)

                    delimiter = ""
                    
                    if filename[2]:
                        delimiter = "a"

                    newFilename =  "%s/%s/%s_%s%s%s" % (aenttypename, attributename, identifier, filehash["%s%s" % (filename[0], attributename)],delimiter, r.group(0))
                    


                exifdata = exifCon.execute("select * from %s where uuid = %s" % (aenttypename, filename[0])).fetchone()
                iddata = [] 
                for id in importCon.execute("select coalesce(measure, vocabname, freetext) from latestnondeletedarchentidentifiers where uuid = %s union select aenttypename from latestnondeletedarchent join aenttype using (aenttypeid) where uuid = %s" % (filename[0], filename[0])):
                    iddata.append(id[0])


                shutil.copyfile(originalDir+filename[1], exportDir+newFilename)

                mergedata = exifdata.copy()
                mergedata.update(jsondata)
                mergedata.pop("geospatialcolumn", None)
                exifjson = {"SourceFile":exportDir+newFilename, 
                            "UserComment": [json.dumps(mergedata)], 
                            "ImageDescription": exifdata['identifier'], 
                            "XPSubject": "Annotation: %s" % (filename[2]),
                            "Keywords": iddata,
                            "Artist": exifdata['createdBy'],
                            "XPAuthor": exifdata['createdBy'],
                            "Software": "FAIMS Project",
                            "ImageID": exifdata['uuid'],
                            "Copyright": jsondata['name']


                            }
                with open(exportDir+newFilename+".json", "w") as outfile:
                    json.dump(exifjson, outfile)    

                if imghdr.what(exportDir+newFilename):
                    
                    subprocess.call(["exiftool", "-m", "-q", "-sep", "\"; \"", "-overwrite_original", "-j=%s" % (exportDir+newFilename+".json"), exportDir+newFilename])
                if filename[0] not in outputFilename:
                    outputFilename[filename[0]] = {}
                if attributename not in outputFilename[filename[0]]:
                    outputFilename[filename[0]][attributename] = {}
                if filehash["%s%s" % (filename[0], attributename)]  not in outputFilename[filename[0]][attributename]:
                    outputFilename[filename[0]][attributename][filehash["%s%s" % (filename[0], attributename)]] = {}                    
                outputAent[filename[0]] = aenttypename
                outputFilename[filename[0]][attributename][filehash["%s%s" % (filename[0], attributename)]] = {"newFilename":newFilename,
                                                                   "mimeType":mime.from_file(originalDir+filename[1])
                                                                   }
                
                print "    * %s" % (newFilename)
                files.append(newFilename+".json")
                files.append(newFilename)
                attachedfiledump.append({"uuid":filename[0], 
                          "aenttype": aenttypename,
                          "attribute": attributename,
                          "newFilename":newFilename,
                          "mimeType":mime.from_file(originalDir+filename[1])})
            else:
                print "<b>Unable to find file %s, from uuid: %s" % (originalDir+filename[1], filename[0]) 
        except Exception as e:
           

            print "<b>Unable to find file (exception thrown) %s, from uuid: %s. Exception: %s" % (originalDir+filename[1], filename[0], traceback.format_exc())    

    for uuid in outputFilename:
        for attribute in outputFilename[uuid]:
            exportCon.execute("update %s set %s = ? where uuid = ?" % (outputAent[uuid], attribute), (json.dumps(outputFilename[uuid][attribute]) , uuid))

    files.append("attachedfiledump.csv")
    csv_writer = UnicodeWriter(open(exportDir+"attachedfiledump.csv", "wb+"))
    csv_writer.writerow(["uuid", "aenttype", "attribute", "filename", "mimeType"])
    for row in attachedfiledump:
        print(row)
        csv_writer.writerow([row["uuid"], row["aenttype"], row["attribute"], row["newFilename"], row["mimeType"]])
    # check input flag as to what filename to export

shutil.copyfile(exportDB, shapeDB)

shapeCon = sqlite3.connect(shapeDB)
shapeCon.enable_load_extension(True)
shapeCon.load_extension(LIBSPATIALITE)


# shapeCon.execute("drop view if exists latestNonDeletedArchEntFormattedIdentifiers;")
# shapeCon.execute("""
# CREATE VIEW latestNonDeletedArchEntFormattedIdentifiers as 
# select uuid, aenttypeid, aenttypename, group_concat(response, '') as response, null as deleted 
# from ( 
#   select uuid, aenttypeid, aenttypename, group_concat(format(formatstring, vocabname, measure, null, null), appendcharacterstring) as response, null as deleted, aentcountorder 
#   from ( 
#     select uuid, aenttypeid, aenttypename, replace(replace(formatstring, char(10),''), char(13),'') as formatstring, vocabname, replace(replace(measure, char(13), '\r'), char(10), '\n') as measure, replace(replace(freetext, char(13), '\r'), char(10), '\n') as freetext, certainty, appendcharacterstring, null as deleted, aentcountorder, vocabcountorder, attributeid 
#     from latestNonDeletedArchent 
#       JOIN aenttype using (aenttypeid) 
#       JOIN (select * from idealaent where isIdentifier='true') using (aenttypeid) 
#       join attributekey  using (attributeid) 
#       left outer join latestNonDeletedAentValue using (uuid, attributeid) 
#       left outer join vocabulary using (attributeid, vocabid) 
#     order by uuid, aentcountorder, vocabcountorder 
#   ) 
#   group by uuid, attributeid 
#   having response is not null 
#   order by uuid, aentcountorder) 
# group by uuid 
# order by uuid;
# """);


# for row in importCon.execute("select aenttypename, geometrytype(geometryn(geospatialcolumn,1)) as geomtype, count(distinct geometrytype(geometryn(geospatialcolumn,1))) from latestnondeletedarchent join aenttype using (aenttypeid) where geomtype is not null group by aenttypename having  count(distinct geometrytype(geometryn(geospatialcolumn,1))) = 1"):
#     cmd = ["spatialite_tool", "-e", "-shp", "%s" % (clean(row[0]).decode("ascii")), "-d", "%snoannotation.sqlite3" % (exportDir), "-t", "%s" % (clean(row[0])), "-c", "utf-8", "-g", "geospatialcolumn", "-s", "%s" % (srid), "--type", "%s" % (row[1])]

#     files.append("%s.dbf" % (clean(row[0])))
#     files.append("%s.shp" % (clean(row[0])))
#     files.append("%s.shx" % (clean(row[0])))
#     # print cmd
#     subprocess.call(cmd, cwd=exportDir)

# https://fastkml.readthedocs.io/en/latest/usage_guide.html#build-a-kml-from-scratch
kmlroot = kml.KML()
ns = '{http://www.opengis.net/kml/2.2}'
# 'docid'
kmldoc = kml.Document(ns, jsondata['key'], jsondata['name'], jsondata)
kmlroot.append(kmldoc)

for row in importCon.execute("select aenttypeid, aenttypename, aenttypedescription from aenttype"):
    aenttypename = row[1]
    kmlfolder = kml.Folder(ns, row[0], aenttypename, row[2])
    kmldoc.append(kmlfolder)

    # Make a placemark for each geometry in this aent
    for geomrow in importCon.execute("SELECT uuid, asewkb(geosptialcolumn) FROM latestnondeletedarchent where aenttypeid = ? and geosptialcolumn is not null", [row[0]]):
        print geomrow
        exportrow = exportCon.execute("SELECT * FROM {} WHERE uuid = ?".format(aenttypename), [geomrow[0]]).fetchone()
        placemark = kml.Placemark(ns, exportrow['uuid'], exportrow['identifier'])
        placemark.geometry = loads(geomrow[1])

        for key in exportrow:
            kmldata = kml.Data(ns, name=key, value=exportrow[key])

        kmlfolder.append(placemark)





for at in importCon.execute("select aenttypename from aenttype"):
    aenttypename = "%s" % (clean(at[0]))


    cursor = exportCon.cursor()
    try:
        cursor.execute("select * from %s" % (aenttypename)) 
    except:
        cursor.execute("select * from %s" % (aenttypename))     


    files.append("Entity-%s.csv" % (aenttypename))

    csv_writer = UnicodeWriter(open(exportDir+"Entity-%s.csv" % (aenttypename), "wb+"))
    csv_writer.writerow([i[0] for i in cursor.description]) # write headers
    csv_writer.writerows(cursor)

    #spatialite_tool -e -shp surveyUnitTransectBuffer -d db.sqlite3 -t surveyUnitWithTransectBuffer -c utf-8 -g surveyBuffer --type polygon



relntypequery = '''select distinct relntypeid, relntypename from relntype join latestnondeletedrelationship using (relntypeid);'''

relnquery = '''select parent.uuid as fromuuid, child.uuid as touuid, parent.participatesverb 
                 from (select * 
                        from latestnondeletedaentreln 
                        join relationship using (relationshipid)  
                       where relationshipid in (select relationshipid 
                                                  from relationship 
                                                  join relntype using (relntypeid) 
                                                 where relntypename = ?)
                      ) parent 
                 join (latestnondeletedaentreln 
                       join relationship using (relationshipid)
                       ) child on (parent.relationshipid = child.relationshipid and parent.uuid != child.uuid)  
                 join user using (userid)'''


relntypecursor = importCon.cursor()
relncursor = importCon.cursor()
for relntypeid, relntypename in relntypecursor.execute(relntypequery): 
    relncursor.execute(relnquery, [relntypename])
    exportCon.execute("CREATE TABLE %s (parentuuid TEXT, childuuid TEXT, participatesverb TEXT);" % (clean(relntypename)))
    for i in relncursor:
        exportCon.execute("INSERT INTO %s VALUES(?,?,?)" % (clean(relntypename)), i)
        
    files.append("Relationship-%s.csv" % (clean(relntypename)))
    relncursor.execute(relnquery, [relntypename])
    csv_writer = UnicodeWriter(open(exportDir+"Relationship-%s.csv" % (clean(relntypename)), "wb+"))
    csv_writer.writerow([i[0] for i in relncursor.description]) # write headers
    csv_writer.writerows(relncursor)
print "```"
pprint(files)
print "```"

# tarf = tarfile.open("%s/%s-export.tar.bz2" % (finalExportDir,moduleName), 'w:bz2')
# try:
#     for file in files:
#         tarf.add(exportDir+file, arcname=moduleName+'/'+file)
# finally:
#     tarf.close()


with ZipFile("%s/%s-export.zip" % (finalExportDir, moduleName), 'w', compression, allowZip64=True) as zipf:
    for file in files:
        zipf.write(exportDir+file, arcname=moduleName+'/'+file)

try:
    os.remove(exportDir)
except OSError:
    pass
