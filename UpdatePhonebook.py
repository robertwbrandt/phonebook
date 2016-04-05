#!/usr/bin/env python2.7
"""
Script for updating LDAP phonebook entries to ensure uniformity throughout the database.
"""
import argparse, textwrap, errno
import fnmatch, subprocess, re, datetime

# Import Brandt Common Utilities
import sys, os
sys.path.append( os.path.realpath( os.path.join( os.path.dirname(__file__), "/opt/brandt/common" ) ) )
import brandt
sys.path.pop()

version = 0.3
args = {}
args['setup'] = False
args['test'] = True
args['config'] = "/etc/brandt/UpdatePhonebook.conf"

class customUsageVersion(argparse.Action):
  def __init__(self, option_strings, dest, **kwargs):
    self.__version = str(kwargs.get('version', ''))
    self.__prog = str(kwargs.get('prog', os.path.basename(__file__)))
    self.__row = min(int(kwargs.get('max', 80)), brandt.getTerminalSize()[0])
    self.__exit = int(kwargs.get('exit', 0))
    super(customUsageVersion, self).__init__(option_strings, dest, nargs=0)
  def __call__(self, parser, namespace, values, option_string=None):
    if self.__version:
      print self.__prog + " " + self.__version
      print "Copyright (C) 2013 Free Software Foundation, Inc."
      print "License GPLv3+: GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>."
      version  = "This program is free software: you can redistribute it and/or modify "
      version += "it under the terms of the GNU General Public License as published by "
      version += "the Free Software Foundation, either version 3 of the License, or "
      version += "(at your option) any later version."
      print textwrap.fill(version, self.__row)
      version  = "This program is distributed in the hope that it will be useful, "
      version += "but WITHOUT ANY WARRANTY; without even the implied warranty of "
      version += "MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the "
      version += "GNU General Public License for more details."
      print textwrap.fill(version, self.__row)
      print "\nWritten by Bob Brandt <projects@brandt.ie>."
    else:
      print "Usage: " + self.__prog + " [-t] [-c CONFIG]"
      print "\nScript for updating LDAP phonebook entries to ensure uniformity throughout the database.\n"
      print "Options:"
      options = []
      options.append(("-h, --help",           "Show this help message and exit"))
      options.append(("-v, --version",        "Show program's version number and exit"))
      options.append(("-t, --test",           "Only test, do not write anything to LDAP"))
      options.append(("-c, --config CONFIG",  "Use the given CONFIG file rather then the default"))
      length = max( [ len(option[0]) for option in options ] )
      for option in options:
        description =  textwrap.wrap(option[1], (self.__row - length - 5))
        print "  " + option[0].ljust(length) + "   " + description[0]
        for n in range(1,len(description)): print " " * (length + 5) + description[n]
    exit(self.__exit)
def command_line_args():
  global args
  parser = argparse.ArgumentParser(add_help=False)
  parser.add_argument('-v', '--version', action=customUsageVersion, version=version, max=80)
  parser.add_argument('-h', '--help', action=customUsageVersion)
  parser.add_argument('--setup',
                    required=False,
                    action='store_true')
  parser.add_argument('-t', '--test',    
                    required=False,
                    default=args['test'],                    
                    action='store_true')  
  parser.add_argument('-c', '--config',
                    required=False,
                    default=args['config'],
                    action='store',
                    type=str)
  args.update(vars(parser.parse_args()))

def setup():
  global args 
  if os.geteuid() != 0:
    exit("You need to have root privileges to setup this script.\nPlease try again, this time using 'sudo'.\nExiting.")

  # Create Symbolic link at /usr/local/bin
  src = os.path.realpath( __file__ )
  dst = os.path.join( '/usr/local/bin', os.path.splitext(os.path.basename(__file__))[0] )
  try:
    os.symlink(src, dst)
  except OSError, e:
    if e.errno == errno.EEXIST:
      os.remove(dst)
      os.symlink(src, dst)  

  if not os.path.isfile(args['config']):
    f = open(args['config'], "w")
    f.write( """
#     Configuration file for the Brandt Update Phonebook script"
#     Bob Brandt <projects@brandt.ie>
[global]

[mail]
Name = Email Address

[photo]
Name = Email Address

[title]
Name = Grade

[l]
Name = Location

[ou]
Name = Section

[telephoneNumber]
Name = Telephone Number

[facsimileTelephoneNumber]
Name = FAX Number

[mobile]
Name = Mobile



    test.AttributeMap = {'mail':"Email Address", 'cn':"CN", 'photo':"Photo", 'uid':"Unique ID", 'givenName':"Given Name", 'middleName':"Middle Name", 'sn':"Surname"
    , 'initials':"Initials", 'generationalQualifier':"Generational Qualifier", 'fullName':"Full Name", 'title':"Grade", 'l':"Location", 'ou':"Section"
    , 'personalTitle':"Personal Title", 'employeeType':"Employee Type", 'employeeStatus':"Employee Status"
    , 'manager':"Manager", 'telephoneNumber':"Telephone Number", 'facsimileTelephoneNumber':"FAX Number", 'mobile':"Mobile", 'guid':"Globally Unique ID",'workforceID':"Workforce ID"}
    test.UniqueIDs = ["mail","cn","uid","guid","photo","workforceID"]
    test.SingleValueAttributes = ["givenName","middleName","sn","initials","generationalQualifier","fullName","title","l","ou","mail","uid","photo","personalTitle","employeeType","employeeStatus","manager"]


""")
    f.close()
  exit()


# Start program
if __name__ == "__main__":
  command_line_args()
  if args['setup']: setup()

  config =[]
  f = open(args['config'], "r")
  for line in f.read().split('\n'):
    if line and str(line)[0] not in ["#",";"," ","\t"]:        
      config.append( [ str(l).strip() for l in line.split(",", 4) ] )
  f.close()

  attrib = {'host':os.uname()[1], 'date':datetime.datetime.strftime(datetime.datetime.now(),'%Y%m%d%H%M%S')}
  xml = ElementTree.Element('deamons', attrib = attrib)

  rc = 0
  for test in ['first', 'present', 'last']:
    for line in config:
      if str(line[0]).lower() == test:
        xmlname, name, present, cmd = line[1], line[2], line[3], str(line[4]).split(" ")

        if os.path.isfile(present):
          if cmd[0] == "deamon":
            del cmd[0]
            if ("-o" not in cmd) and ("--output" not in cmd):
              if args['xml']:
                cmd = ["--name",xmlname,"--output","xml"] + cmd
              else:
                cmd = ["--name",name,"--output","pretty"] + cmd        
            cmd = ["deamon"] + cmd

          p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
          out,err = p.communicate()
          rc = rc | p.returncode
          out = str(out).strip()
          if args["xml"]:
            for child in ElementTree.fromstring(out):
              if child.tag == "deamon": xml.append(child)
          else:
            print out

  if args["xml"]:  
    print '<?xml version="1.0" encoding="' + encoding + '"?>'
    print ElementTree.tostring(xml, encoding=encoding, method="xml")

  exit(rc)
