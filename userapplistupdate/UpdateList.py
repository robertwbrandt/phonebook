#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
Created on 24 Nov 2009

@author: brandtb
'''
# We need these optparse for the __main__ function
import optparse, smtplib
import ldapurl, ldap, ldif, sys
from lxml import etree
import syslog
encoding = "utf-8"     

class LDAPSearch(object):
    """ 
    The class returns a List of a Truples of a String and a Dicionary of a List
        
        ldapurl     = ldap[s]://[host[:port]][/base[?[attributes][?[scope][?[filter][?extensions]]]]]
        scope       = "base" / "one" / "sub"
        ldap://ldap.opw.ie:389/o=opw?cn,mail?base
        ldaps://ldap1.opw.ie/ou=userapp,o=opw?cn,mail?sub??bindname=cn=brandtb%2cou=it%2co=opw,X-BINDPW=password
    """
    
    def __init__(self, source = None):
        self.__source = None
        self.__type = None
        self.__sourcename = None
        self.__results = None 
        if source != None:
            self.search(source)
    
    def getSource(self):
        return self.__source
    def setSource(self, source):
        if str(type(source)) == "<type 'str'>" and source == "stdin":
            self.__source = sys.stdin
            self.__type = "stream"
            self.__sourcename = "stdin"            
        elif str(type(source)) == "<type 'file'>":
            self.__source = source
            self.__type = "file"
            self.__sourcename = str(source.name).lstrip("<").rstrip(">")
        elif str(type(source)) == "<type 'str'>":
            try:
                self.__source = ldapurl.LDAPUrl(source)
                self.__type = "url"
                self.__sourcename = source
            except:
                try:
                    self.__source = open(source)
                    self.__type = "file"
                    self.__sourcename = str(source)
                except:
                    raise ValueError, "Parameter source does not seem to be a LDAP URL or File."
                    self.__source = None
                    self.__type = None
                    self.__sourcename = None

        else:
            raise ValueError, "Parameter source does not seem to be a LDAP URL or File."
            self.__source = None
            self.__type = None
            self.__sourcename = None
    source = property(getSource, setSource)

    def getType(self):
        if self.__type != None:
            return self.__type
        else:
            raise ValueError, "Source does not seem to be a LDAP URL or File."
            return None
    type=property(getType)

    def getSourceName(self):
        if self.__sourcename != None:
            return self.__sourcename
        else:
            raise ValueError, "Source does not seem to be a LDAP URL or File."
            return None
    sourcename=property(getSourceName)        

    def getresults(self):
        return self.__results
    results = property(getresults)
    
    def search(self, source):
        timeout = 0
        self.source = source
        self.__results = []
        if self.type == "file" or self.type == "stream":
            ldifFile = ldif.LDIFRecordList(self.__source)
            ldifFile.parse()
            self.__results = ldifFile.all_records

        elif self.type == "url":
            filterstr = self.source.filterstr
            #extensions = self.source.extensions
            if filterstr == None: filterstr = "(objectClass=*)"
          
            con_string = "%s://%s" % (self.source.urlscheme, self.source.hostport)    
            l = ldap.initialize(con_string)
            #l.start_tls_s()
            if self.source.who:
                l.bind_s(self.source.who, self.source.cred)
            else:
                l.bind_s('', '') # anonymous bind
        
            ldap_result_id = l.search(self.source.dn, self.source.scope, filterstr, self.source.attrs)
            while 1:
                result_type, result_data = l.result(ldap_result_id, timeout)
                if (result_data == []):
                    break
                else:
                    if result_type == ldap.RES_SEARCH_ENTRY:
                        self.__results.append(result_data[0])
        return self.__results

    def attributelist(self, attribute):
        temp = {}
        for entry in self.results:            
            for attr in entry[1]:
                if attr == attribute:
                    for value in entry[1][attr]:
                        temp[value] = value            
        return tuple( temp.keys() )
    
    def __str__(self):
        tmp = ""
        if self.results:
            for result in self.results:
                tmp += str(result) + "\n"
        return tmp.strip("\n")
    
class UserAppList(object):
    
    def __init__(self, data = None, attribute = None, label = None):
        self.__encoding = "utf-8"     
        self.__xml = None 
        if data != None:
            self.parse(data, attribute, label)
        
    def parse(self, data, attribute, labelstr):              
        tmp = []
        for item in data:
            tmp += item[1][attribute]
        tmp.sort()

        # Load the XML from a string because of the weird namespaces.
        self.__xml = etree.fromstring('<list-items protected="false" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="../../../../../../../xml-validation/conf/schema/DirectoryModelXmlData3_5_0.xsd"/>')

        # Insert List Name
        display = etree.fromstring('<display xml:lang="en"/>')
        label = etree.SubElement(display, "label")
        label.text = unicode(labelstr, self.__encoding)
        self.__xml.append(display)   
        
        # Insert the None option
        listitem = etree.SubElement(self.__xml, "list-item")
        key = etree.SubElement(listitem, "key")
        display = etree.fromstring('<display xml:lang="en"/>')
        label = etree.SubElement(display, "label")
        label.text = unicode("(none)", self.__encoding)
        listitem.append(display)           
         
        for item in tmp:
            listitem = etree.SubElement(self.__xml, "list-item")
            key = etree.SubElement(listitem, "key")
            key.text = unicode(item, self.__encoding)
            display = etree.fromstring('<display xml:lang="en"/>')
            label = etree.SubElement(display, "label")
            label.text = unicode(item, self.__encoding)
            listitem.append(display)           

    xml = property(lambda self: str(self))

    def __str__(self):
        return etree.tostring(self.__xml)

def replaceXMLData(source, XMLData):
    timeout = 0
    source = ldapurl.LDAPUrl(source)

    con_string = "%s://%s" % (source.urlscheme, source.hostport)    
    l = ldap.initialize(con_string)
    #l.start_tls_s()
    if source.who:
        l.bind_s(source.who, source.cred)
    else:
        l.bind_s('', '') # anonymous bind

    mod_attrs = [( ldap.MOD_REPLACE, "XMLData", XMLData )]
    l.modify_s(source.dn, mod_attrs)



    
if __name__ == '__main__':
    version = 0.1
    usageText="usage: %prog [options]"
    versionText =  "\n" + " ".join(["GNU","%prog",str(version)]) + "\n"
    versionText += "This program is distributed in the hope that it will be useful,\n"
    versionText += "but WITHOUT ANY WARRANTY; without even the implied warranty of\n"
    versionText += "MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the\n"
    versionText += "GNU General Public License for more details.\n\n"
    versionText += "Originally written by Bob Brandt <projects@brandt.ie>.\n"

    parser = optparse.OptionParser(usage=usageText, version=versionText)
    parser.add_option("-w", "--write", dest="write", action="store_true", default=True, help="Write changes to LDAP.")
    parser.add_option("-t", "--test", dest="write", action="store_false", help="Do not Write changes..")
    (options, args) = parser.parse_args()


    syslog.syslog("Starting the Automatic Phonebook List Update")
    print "Starting the Automatic Phonebook List Update"


    locationURL = "ldaps://idm1.opw.ie/ou=location,ou=userapp,ou=web,ou=org,o=opw?l?sub?(&(objectClass=Template)(l=*))"
    sectionURL = "ldaps://idm1.opw.ie/ou=section,ou=userapp,ou=web,ou=org,o=opw?ou?sub?(&(objectClass=Template)(ou=*))"
    gradeURL = "ldaps://idm1.opw.ie/ou=grade,ou=userapp,ou=web,ou=org,o=opw?title?sub?(&(objectClass=Template)(title=*))"
    locationListURL = "ldaps://idm1.opw.ie/cn=locationlist,cn=choicedefs,cn=directorymodel,cn=appconfig,cn=userapp36,cn=driverset,ou=services,o=opw?xmldata?base??bindname=cn=userapp%2co=opw,X-BINDPW=us3rapp"
    sectionListURL = "ldaps://idm1.opw.ie/cn=sectionlist,cn=choicedefs,cn=directorymodel,cn=appconfig,cn=userapp36,cn=driverset,ou=services,o=opw?xmldata?base??bindname=cn=userapp%2co=opw,X-BINDPW=us3rapp"
    gradeListURL = "ldaps://idm1.opw.ie/cn=gradelist,cn=choicedefs,cn=directorymodel,cn=appconfig,cn=userapp36,cn=driverset,ou=services,o=opw?xmldata?base??bindname=cn=userapp%2co=opw,X-BINDPW=us3rapp"
    MailServer = "smtp.opw.ie"
    MailFrom = "corrections@opw.ie"
    MailTo = "corrections@opw.ie"

    location = LDAPSearch(locationURL).results
    section = LDAPSearch(sectionURL).results
    grade = LDAPSearch(gradeURL).results
    
    locationList = LDAPSearch(locationListURL).results
    sectionList = LDAPSearch(sectionListURL).results
    gradeList = LDAPSearch(gradeListURL).results

    location = UserAppList(location, "l","Location List").xml
    section = UserAppList(section, "ou", "Section List").xml
    grade = UserAppList(grade, "title", "Grade List").xml

    locationList = locationList[0][1]["xmldata"][0]
    sectionList = sectionList[0][1]["xmldata"][0]
    gradeList = gradeList[0][1]["xmldata"][0]

    update = {}
    if unicode(location, encoding) != unicode(locationList, encoding):
        syslog.syslog("Replacing Location XML Data")
        print "Replacing Location XML Data"
        if options.write:
            replaceXMLData(locationListURL, location)
            update["location"] = location
        else:
            print location
    if unicode(section, encoding) != unicode(sectionList, encoding):
        syslog.syslog("Replacing Section XML Data")
        print "Replacing Section XML Data"
        if options.write:
            replaceXMLData(sectionListURL, section)
            update["section"] = section
        else:
            print section
    if unicode(grade, encoding) != unicode(gradeList, encoding):
        syslog.syslog("Replacing Grade XML Data")
        print "Replacing Grade XML Data"
        if options.write:
            replaceXMLData(gradeListURL, grade)
            update["grade"] = grade
        else:
            print grade

    if update:
        tmpmsg = "From: " + str( MailFrom ).lower() +"\n"
        tmpmsg += "To: " + str( MailTo ).lower() +"\n"
        tmpmsg += "Subject: Automatic UserApp List Changes\n"
        tmpmsg += "User-Agent: Python 2.6.4 (projects@brandt.ie)\n"
        if update.has_key("location"):
            tmpmsg += "The Location XML Data has been changed to:\n" + update["location"] + "\n\n"
        if update.has_key("section"):
            tmpmsg += "The Section XML Data has been changed to:\n" + update["section"] + "\n\n"
        if update.has_key("grade"):
            tmpmsg += "The Grade XML Data has been changed to:\n" + update["grade"] + "\n\n"
        server = smtplib.SMTP( MailServer )
        server.set_debuglevel(1)
        server.sendmail([ MailFrom ], [ MailTo ], tmpmsg)
        server.quit()  

    syslog.syslog("Finished the Automatic Phonebook List Update")
    print "Finished the Automatic Phonebook List Update"
