#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
Created on 20 Oct 2009

@author: brandtb
'''
# We need these optparse for the __main__ function
import optparse, os, difflib, smtplib, urllib
import ldapurl, ldap, sys
import ldap.modlist as modlist
import IrishPhoneNumber
import syslog


def listunion(*lists):
    tmp = []
    for tmplist in lists:
        for item in tmplist:
            if not item in tmp: tmp.append(item)
    return tmp

def listintersection(*lists):
    if len(lists) == 1: return lists[0]
    
    tmp = []
    for item in lists[0]:
        condition = True
        for count in range(1,len(lists)):
            if not item in lists[count]: condition = False
        if condition: tmp.append(item)
    return tmp
    
def listprint(*lists):
    tmp = ""
    separator = ", "
    for tmplist in lists:
        for item in tmplist:
            tmp += str(item) + separator
    return tmp.strip(separator)

def photoURL(GUID):
    return str("http://intranet/media/photos/" + str(GUID).lower() + ".jpg")

def convertGUID(binaryGUID):
    temp = ""
    for char in str(binaryGUID):
        tmp = "00" + hex(ord(char))[2:]
        temp += tmp[-2:]
    return temp.lower()

def formatFullName(FullName):
    tmp = " ".join(unicode(FullName).split())
    tmp = "'".join(unicode(tmp).split("' "))
    tmp = "'".join(unicode(tmp).split(" '"))
    return tmp

class LDAPURL2(ldapurl.LDAPUrl):
    def appendAttributeList(self, AttributeList):
        if self.attrs == None: self.attrs = list(AttributeList)
        else:
            for attribute in AttributeList:
                if not attribute in self.attrs: self.attrs.append(attribute)

class Phonebook(object):
    """
    Update Entries in the OPW PhoneBook.
    """
    
    def __init__(self):
        self._ldaptimeout = 0

    LDAPQuery = property(lambda self: self._ldapquery, lambda self, LDAPQuery: setattr(self, "_ldapquery", LDAPURL2(LDAPQuery)))
    UniqueIDs = property(lambda self: self._uidlist, lambda self, UIDAttributeList: setattr(self,"_uidlist", tuple(UIDAttributeList))) 
    PhotoIDs = property(lambda self: self._photolist, lambda self, PhotoAttributeList: setattr(self,"_photolist", tuple(PhotoAttributeList))) 
    SingleValueAttributes = property(lambda self: self._singleattributes, lambda self, attributes: setattr(self,"_singleattributes", tuple(attributes)))
    PhoneAttributes = property(lambda self: self._phoneattributes, lambda self, attributes: setattr(self,"_phoneattributes", tuple(attributes))) 
    MailServer = property(lambda self: self._mailserver, lambda self, mailserver: setattr(self,"_mailserver", str(mailserver))) 
    MailFrom = property(lambda self: self._mailfrom, lambda self, mailfrom: setattr(self,"_mailfrom", str(mailfrom))) 
    MailTo = property(lambda self: self._mailto, lambda self, mailto: setattr(self,"_mailto", str(mailto))) 
    MailAdmin = property(lambda self: self._mailadmin, lambda self, mailadmin: setattr(self,"_mailadmin", str(mailadmin)))
    PhoneType = property(lambda self: self._phonetype, lambda self, f: setattr(self,"_phonetype", f))
    ApproxValues = property(lambda self: self._approxvalues, lambda self, values: setattr(self,"_approxvalues", tuple(values))) 
    ListAttributes = property(lambda self: tuple(self._listattributes.keys()))


    def AddListAttribute(self, AttributeName, LDAPQuery):
        AttributeName = str(AttributeName).lower()
        if not hasattr(self,"_listattributes"): self._listattributes = {}
        if not self._listattributes.has_key(AttributeName): self._listattributes[AttributeName] = {"query":"","list":[]}
        self._listattributes[AttributeName]["query"] = LDAPURL2(LDAPQuery)
        self._listattributes[AttributeName]["query"].appendAttributeList([AttributeName])

    def getAttributeMap(self, Attribute = None):
        if not hasattr(self,"_attributemap"): self._attributemap = {}
        if Attribute == None: return self._attributemap
        AttributeLower = str(Attribute).lower()
        for attr in self._attributemap.keys():
            if str(attr).lower() == AttributeLower: return self._attributemap[attr]
        else:
            return Attribute
    AttributeMap = property(getAttributeMap, lambda self, MapDict: setattr(self, "_attributemap", dict(MapDict)))     

    def getDN(self, DN):
        tmp = ()
        if hasattr(self,"_queryresults") and self._queryresults:
            for entry in self._queryresults:
                if str(entry[0]).lower() == str(DN).lower():
                    tmp = entry
                    break
        return tmp  
    
    def getDNAttribute(self, DN, Attribute):
        tmp = []
        if hasattr(self,"_queryresults") and self._queryresults:
            for entry in self._queryresults:
                if str(entry[0]).lower() == str(DN).lower():
                    tmp = entry[1].get(Attribute, [])
                    break
        return tmp


    def __str__(self):
        tmp = ""
        keys = self.__dict__.keys()
        keys.sort()
        for key in keys:
            tmp += str(key) + ": " + str(self.__dict__[key]) + "\n"
        return tmp.strip("\n")


    def check(self, write = False):
        self._ldapquery.appendAttributeList(self._uidlist)
        self._ldapquery.appendAttributeList(self._singleattributes)
        self._ldapquery.appendAttributeList(self._phoneattributes)
        self._ldapquery.appendAttributeList(self._listattributes.keys())

        syslog.syslog("Starting the Automatic Phonebook Update")
        print "Starting the Automatic Phonebook Update"
        try:
            self._openldap()
            self._getlists()
            self._getusers()
            self._checkuids()
            self._checkphones()
            self._checksingleattributes()
            self._checklistattributes()
            
            # OPW Specific Checks
            self._checkphotoandworkforceID()
            self._checkfullname()        
                
            self._writechanges(write)
        finally:
            self._closeldap()
        syslog.syslog("Finished the Automatic Phonebook Update")
        print "Finished the Automatic Phonebook Update"


    def _openldap(self):
        con_string = "%s://%s" % (self._ldapquery.urlscheme, self._ldapquery.hostport)    
        self._l = ldap.initialize(con_string)
        self._l.start_tls_s()
        if self._ldapquery.who: self._l.bind_s(self._ldapquery.who, self._ldapquery.cred)
        else: self._l.bind_s('', '') # anonymous bind
            
    def _closeldap(self):
        if hasattr(self,"_l"): self._l.unbind_s()
                
    def _getlists(self):
        if hasattr(self,"_l") and len(self._listattributes):
            for attribute in self._listattributes:
                query = self._listattributes[attribute]["query"]
                ldap_result_id = self._l.search(query.dn, query.scope, query.filterstr, query.attrs)
                results = []
                while 1:
                    result_type, result_data = self._l.result(ldap_result_id, self._ldaptimeout)
                    if (result_data == []):
                        break
                    else:
                        if result_type == ldap.RES_SEARCH_ENTRY:
                            results.append(result_data[0])
                tmp = {}
                for result in results:
                    tmp[result[1][attribute][0]] = attribute
                self._listattributes[attribute]["list"] = tmp.keys()
                self._listattributes[attribute]["list"].sort()
                
    def _getusers(self):
        if hasattr(self,"_l"):
            ldap_result_id = self._l.search(self._ldapquery.dn, self._ldapquery.scope, self._ldapquery.filterstr, self._ldapquery.attrs)
            self._queryresults = []
            while 1:
                result_type, result_data = self._l.result(ldap_result_id, self._ldaptimeout)
                if (result_data == []):
                    break
                else:
                    if result_type == ldap.RES_SEARCH_ENTRY:
                        self._queryresults.append(result_data[0])
                
    def _checkuids(self):
        if hasattr(self,"_queryresults") and self._queryresults and hasattr(self,"_uidlist") and self._uidlist:
            self._nonunique = {}
            for uid in self._uidlist:
                self._nonunique[uid] = {}
                unique = {}
                for result in self._queryresults:
                    if result[1].has_key(uid):
                        for entry in result[1][uid]:
                            if unique.has_key(entry):
                                unique[entry].append(result[0])
                            else:
                                unique[entry] = [result[0]]
                for entry in unique.keys():
                    if len(unique[entry]) > 1: 
                        self._nonunique[uid][entry] = unique[entry]
                        
    def _checkphones(self):
        if hasattr(self,"_queryresults") and self._queryresults and hasattr(self,"_phoneattributes") and self._phoneattributes and hasattr(self,"_phonetype"):
            self._updatephones = {}
            for result in self._queryresults:
                for phoneattr in self._phoneattributes:
                    if result[1].has_key(phoneattr):
                        for phone in result[1][phoneattr]:
                            try:
                                newphone = self._phonetype(phone)
                            except:
                                newphone = None
                            if phone != newphone: 
                                if not self._updatephones.has_key(result[0]): self._updatephones[result[0]] = {}
                                if not self._updatephones[result[0]].has_key(phoneattr):
                                    self._updatephones[result[0]][phoneattr] = {"delete":[], "add":[]}
                                self._updatephones[result[0]][phoneattr]["delete"].append(phone)
                                if newphone: self._updatephones[result[0]][phoneattr]["add"].append(newphone)
                                

    def _checksingleattributes(self):
        if hasattr(self,"_queryresults") and self._queryresults and hasattr(self,"_singleattributes") and self._singleattributes:
            self._updatesingles = {}        
            for result in self._queryresults:
                for singleattr in self._singleattributes:
                    if result[1].has_key(singleattr):
                        if len(result[1][singleattr]) > 1:
                            self._updatesingles[result[0]] = {singleattr:{"keep":[result[1][singleattr][0]], "delete":result[1][singleattr][1:]}}
                            
    def _checklistattributes(self):
        if hasattr(self,"_queryresults") and self._queryresults and hasattr(self,"_listattributes") and self._listattributes and hasattr(self,"_approxvalues") and self._approxvalues:
            self._updatelists = {}
            if not self._singleattributes: self._singleattributes = []
            for result in self._queryresults:
                for listattr in self._listattributes.keys():
                    if result[1].has_key(listattr):
                        for item in result[1][listattr]:
                            if not item in self._listattributes[listattr]["list"]:
                                tempdict = {"attribute":listattr, "delete":item}
                                for cutoff in self._approxvalues:
                                    approx = difflib.get_close_matches(str(item), self._listattributes[listattr]["list"], n=1, cutoff=cutoff)
                                    if approx:
                                        tempdict.update({"add":approx, "closeness":cutoff})
                                        break
                                if not self._updatelists.has_key(result[0]):
                                    self._updatelists[result[0]] = [tempdict]
                                else:
                                    self._updatelists[result[0]].append(tempdict)

                        # Attack the problem 
                        if listattr in self._singleattributes and len(result[1][listattr]) > 1:
                            # Check to see if one of the current values is in the list, take the first one that matches
                            finalvalue = ""
                            for item in result[1][listattr]:
                                if item in self._listattributes[listattr]["list"]:
                                    finalvalue = item
                                    templist = list(result[1][listattr])
                                    templist.remove(finalvalue)
                                    self._updatesingles[result[0]] = {listattr:{"delete":templist, "keep":[finalvalue]}}
                                    break
                            # Check for the best approx value
                            if not finalvalue:
                                closeness = 0
                                for item in self._updatelists[result[0]]:
                                    if closeness < item.get("closeness",-1):
                                        closeness = item["closeness"]
                                        finalvalue = item["add"][0]
                                if finalvalue:
                                    self._updatesingles[result[0]] = {listattr:{"delete":result[1][listattr], "add":[finalvalue]}}
                            # Remove all values
                            if not finalvalue:
                                self._updatesingles[result[0]] = {listattr:{"delete":result[1][listattr]}}
                            try:
                                del self._updatelists[result[0]]
                            except:
                                pass

    def _checkphotoandworkforceID(self):
        if hasattr(self,"_queryresults") and self._queryresults and self._attributemap.has_key("guid"):
            self._updateGUIDattrs = {}        
            for result in self._queryresults:
                GUID = str(convertGUID(result[1]["guid"][0])).lower()
                
                if self._attributemap.has_key("photo"):
                    newphoto = photoURL(convertGUID(result[1]["guid"][0]))
                    if result[1].has_key("photo"):
                        oldphoto = str(result[1]["photo"][0])
                    else:
                        oldphoto = ""
                    if oldphoto != newphoto:
                        self._updateGUIDattrs[result[0]] = {"photo":{"add":[ newphoto ]}}
                        if oldphoto: self._updateGUIDattrs[result[0]]["photo"]["delete"] = [ oldphoto ]

                if self._attributemap.has_key("workforceID"):               
                    if result[1].has_key("workforceID"):
                        oldworkforceid = str(result[1]["workforceID"][0])
                    else:
                        oldworkforceid = ""
                    if oldworkforceid != GUID:
                        self._updateGUIDattrs[result[0]] = {"workforceID":{"add":[ GUID ]}}
                        if oldworkforceid: self._updateGUIDattrs[result[0]]["workforceID"]["delete"] = [ oldworkforceid ]
                        
    def _checkfullname(self):
        if hasattr(self,"_queryresults") and self._queryresults and self._attributemap.has_key("fullName"):
            self._fullname = {}
            for result in self._queryresults:
                try:
                    if result[1].has_key("fullName"):
                        oldfullname = str(result[1]["fullName"][0])
                        newfullname = formatFullName(oldfullname)
                    if oldfullname != newfullname:
                        # Unicode is causeing issues.
                        newfullname = str(newfullname)
                        self._fullname[result[0]] = {"fullName":{"add":[ newfullname ], "delete":[ newfullname ] }}
                except:
                    pass
                                             
                        
    def _writechanges(self, write):
        if hasattr(self,"_l") and hasattr(self,"_queryresults") and self._queryresults:
            if not self._updatephones: self._updatephones = {}
            if not self._updatesingles: self._updatesingles = {}        
            if not self._updatelists: self._updatelists = {}
            if not self._updateGUIDattrs: self._updateGUIDattrs = {}
            if not self._fullname: self._fullname = {}
            DNlist = listunion(self._updatephones.keys(), self._updatesingles.keys(), self._updatelists.keys(), self._updateGUIDattrs.keys(), self._fullname.keys())
            
            changelist = {}
            message = ""
            adminmessage = ""
            for DN in DNlist:
                attributes = {"delete":{}, "add":{}}
                msg = ""
                adminmsg = ""
                if DN in self._updatephones.keys():
                    for attr in self._updatephones[DN]:
                        if self._updatephones[DN][attr].has_key("delete"): 
                            if not attributes["delete"].has_key(attr): attributes["delete"][attr] = []
                            attributes["delete"][attr] += self._updatephones[DN][attr]["delete"]
                            msg += " - The following " + self.getAttributeMap(attr) + "(s) " + listprint(self._updatephones[DN][attr]["delete"])
                        if self._updatephones[DN][attr].has_key("add"): 
                            if not attributes["add"].has_key(attr): attributes["add"][attr] = []
                            attributes["add"][attr] += self._updatephones[DN][attr]["add"]
                            msg += " were replaced by " + listprint(self._updatephones[DN][attr]["add"]) + ".\n"
                        else:
                            msg += " were deleted.\n"
                            
                if DN in self._updatesingles.keys():
                    for attr in self._updatesingles[DN]:
                        if self._updatesingles[DN][attr].has_key("delete"): 
                            if not attributes["delete"].has_key(attr): attributes["delete"][attr] = []
                            attributes["delete"][attr] += self._updatesingles[DN][attr]["delete"]
                            msg += " - The following " + self.getAttributeMap(attr) + "(s) " + listprint(self._updatesingles[DN][attr]["delete"])
                        if self._updatesingles[DN][attr].has_key("add"): 
                            if not attributes["add"].has_key(attr): attributes["add"][attr] = []
                            attributes["add"][attr] += self._updatesingles[DN][attr]["add"]
                            msg += " were replaced by " + listprint(self._updatesingles[DN][attr]["add"]) + ".\n"
                        else:
                            msg += " were deleted.\n"

                if DN in self._updatelists.keys():
                    for attr in self._updatelists[DN]:
                        if attr.has_key("delete"): 
                            if not attributes["delete"].has_key(attr["attribute"]): attributes["delete"][attr["attribute"]] = []
                            attributes["delete"][attr["attribute"]] += [ attr["delete"] ]
                            msg += " - The following " + self.getAttributeMap(attr["attribute"]) + "(s) " + listprint([ attr["delete"] ])
                        if attr.has_key("add"): 
                            if not attributes["add"].has_key(attr["attribute"]): attributes["add"][attr["attribute"]] = []
                            attributes["add"][attr["attribute"]] += attr["add"]
                            msg += " were replaced by " + listprint( attr["add"] ) + ".\n"
                        else:
                            msg += " were deleted.\n"

                if DN in self._updateGUIDattrs.keys():
                    for attr in self._updateGUIDattrs[DN]:
                        if self._updateGUIDattrs[DN][attr].has_key("delete"): 
                            if not attributes["delete"].has_key(attr): attributes["delete"][attr] = []
                            attributes["delete"][attr] += self._updateGUIDattrs[DN][attr]["delete"]
                            adminmsg += " - The following " + self.getAttributeMap(attr) + "(s) " + listprint(self._updateGUIDattrs[DN][attr]["delete"]) + " were deleted.\n"
                        if self._updateGUIDattrs[DN][attr].has_key("add"): 
                            if not attributes["add"].has_key(attr): attributes["add"][attr] = []
                            attributes["add"][attr] += self._updateGUIDattrs[DN][attr]["add"]
                            adminmsg += " - The following " + self.getAttributeMap(attr) + "(s) " + listprint(self._updateGUIDattrs[DN][attr]["add"]) + " were added.\n"

                if DN in self._fullname.keys():
                    if not attributes["delete"].has_key("fullName"): attributes["delete"]["fullName"] = []
                    attributes["delete"]["fullName"] += self._fullname[DN]["fullName"]["delete"]
                    if not attributes["add"].has_key("fullName"): attributes["add"]["fullName"] = []
                    attributes["add"]["fullName"] += self._fullname[DN]["fullName"]["add"]
                    msg += " - The following Full Name '" + listprint( self._fullname[DN]["fullName"]["delete"] ) + "' was replaced by '" + listprint( self._fullname[DN]["fullName"]["add"] ) + "'.\n"

                if attributes["add"] or attributes["delete"]:
                    changelist[DN] = attributes
                    try:
                        fullname = test.getDNAttribute(DN, "fullName")[0]
                    except:
                        fullname = DN
                    if msg: message += fullname + " (" + DN + ") has had the following changes to their account:\n" + msg + "\n"
                    if adminmsg: adminmessage += fullname + " (" + DN + ") has had the following changes to their account:\n" + adminmsg + "\n"

            if message and hasattr(self,"_mailserver") and hasattr(self,"_mailfrom") and hasattr(self,"_mailto"):
                tmpmsg = "From: " + str(self._mailfrom).lower() +"\n"
                tmpmsg += "To: " + str(self._mailto).lower() +"\n"
                tmpmsg += "Subject: Automatic Phonebook Changes\n"
                tmpmsg += "User-Agent: Python 2.6.4 (projects@brandt.ie)\n" + message                
                server = smtplib.SMTP(self._mailserver)
                server.set_debuglevel(1)
                server.sendmail([self._mailfrom], [self._mailto], tmpmsg)
                server.quit()

            if adminmessage and hasattr(self,"_mailserver") and hasattr(self,"_mailfrom") and hasattr(self,"_mailadmin"):
                tmpmsg = "From: " + str(self._mailfrom).lower() +"\n"
                tmpmsg += "To: " + str(self._mailadmin).lower() +"\n"
                tmpmsg += "Subject: Automatic Phonebook Changes (Admin)\n"
                tmpmsg += "User-Agent: Python 2.6.4 (projects@brandt.ie)\n" + adminmessage                
                server = smtplib.SMTP(self._mailserver)
                server.set_debuglevel(1)
                server.sendmail([self._mailfrom], [self._mailadmin], tmpmsg)
                server.quit()

            if changelist and hasattr(self,"_l"):
                errormsg = ""                
                for dn in changelist.keys():
                    delete_attrs = []
                    add_attrs = []
                    for attr in changelist[dn]["delete"].keys():
                        for value in changelist[dn]["delete"][attr]:
                            delete_attrs.append( ( ldap.MOD_DELETE, attr, value ) )
                    
                    for attr in changelist[dn]["add"].keys():
                        for value in changelist[dn]["add"][attr]:
                            add_attrs.append( ( ldap.MOD_ADD, attr, value ) )         

                    if write:
                        try:
                            self._l.modify_s(dn, delete_attrs)
                        except:
                            errormsg += dn + " : An error occurred while deleting the following attributes\n - " + listprint(delete_attrs) + "\n"
                        try:
                            self._l.modify_s(dn, add_attrs)
                        except:                            
                            errormsg += dn + " : An error occurred while adding the following attributes\n - " + listprint(add_attrs) + "\n"
                    else:
                        print dn
                        print "Delete Attrs", listprint(delete_attrs)
                        print "Add Attrs", listprint(add_attrs), "\n"

                if errormsg:
                    tmpmsg = "From: " + str(self._mailfrom).lower() +"\n"
                    tmpmsg += "To: " + str(self._mailadmin).lower() +"\n"
                    tmpmsg += "Subject: Automatic Phonebook Changes (errors)\n"
                    tmpmsg += "User-Agent: Python 2.6.4 (projects@brandt.ie)\n\n" + errormsg                
                    server = smtplib.SMTP(self._mailserver)
                    server.set_debuglevel(1)
                    server.sendmail([self._mailfrom], [self._mailadmin], tmpmsg)
                    server.quit()
                    
                    print "\n\nErrors - \n", errormsg         


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

    test = Phonebook()
    test.LDAPQuery = "ldap://ldap.opw.ie/o=opw??sub?(&(objectClass=Person)(!(givenName=System)))?bindname=cn=updatePhonebook%2cou=web%2co=opw,X-BINDPW=UpdatePh0neB00k"
    test.AttributeMap = {'mail':"Email Address", 'cn':"CN", 'photo':"Photo", 'uid':"Unique ID", 'givenName':"Given Name", 'middleName':"Middle Name", 'sn':"Surname", 'initials':"Initials", 'generationalQualifier':"Generational Qualifier", 'fullName':"Full Name", 'title':"Grade", 'l':"Location", 'ou':"Section", 'personalTitle':"Personal Title", 'employeeType':"Employee Type", 'employeeStatus':"Employee Status", 'manager':"Manager", 'telephoneNumber':"Telephone Number", 'facsimileTelephoneNumber':"FAX Number", 'mobile':"Mobile", 'guid':"Globally Unique ID",'workforceID':"Workforce ID"}
    test.UniqueIDs = ["mail","cn","uid","guid","photo","workforceID"]
    test.SingleValueAttributes = ["givenName","middleName","sn","initials","generationalQualifier","fullName","title","l","ou","mail","uid","photo","personalTitle","employeeType","employeeStatus","manager"]
    test.PhoneAttributes = ["telephoneNumber","facsimileTelephoneNumber","mobile"]
    test.PhoneType = IrishPhoneNumber.IrishPhoneNumber
    test.MailServer = "smtp.opw.ie"
    test.MailFrom = "corrections@opw.ie"
    test.MailAdmin = "bob.brandt@opw.ie"
    test.ApproxValues = [0.95, 0.90, 0.85, 0.80, 0.75, 0.70, 0.65] 
    test.AddListAttribute("title", "ldap:///ou=grade,ou=userapp,ou=web,o=opw??sub?(&(objectClass=Template)(title=*))")
    test.AddListAttribute("ou", "ldap:///ou=section,ou=userapp,ou=web,o=opw??sub?(&(objectClass=Template)(ou=*))")
    test.AddListAttribute("l", "ldap:///ou=location,ou=userapp,ou=web,o=opw??sub?(&(objectClass=Template)(l=*))")

    test.MailTo = "corrections@opw.ie"
    test.check(write = options.write)
#    test.MailTo = "bob.brandt@opw.ie"        
#    test.check(write = False)
