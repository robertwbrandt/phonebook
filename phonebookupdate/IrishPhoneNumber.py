#!/usr/bin/python
'''
Created on 21 Dec 2009

@author: brandtb
'''

class IrishPhoneNumber(str):
    def __new__(cls, phonenumber, defaultAreaCode = "01", defaultExtensionLength = 4, defaultExtensionPrefix = "647"):    
        irishphoneformats = {"01":"(##) ###-*",
                             "0402":"(####) ###-*",
                             "0404":"(####) ###-*",
                             "0504":"(####) ###-*",
                             "0505":"(####) ###-*",
                             "099":"(###) ##-*"}   
        defaultirishphoneformat = "(###) ###-*"
        
        # Strip out all the non-characters
        temp = ""
        for digit in str(phonenumber): 
            if digit in ["0","1","2","3","4","5","6","7","8","9"]:
                temp += str(int(digit))
        if not len(temp): raise ValueError, str(phonenumber) + " is not a valid Irish Phone Number."
    
        # Correct short numbers
        if len(temp) <= int(defaultExtensionLength): temp = str(defaultExtensionPrefix) + temp
        if len(temp) == int(defaultExtensionLength) + int(len(str(defaultExtensionPrefix))): temp = str(defaultAreaCode) + temp
        if temp[0] != "0": temp = "0" + temp
        
        for areacode in irishphoneformats.keys():
            if areacode == temp[0:len(areacode)]:
                format = irishphoneformats[areacode]
                break
        else:
            format = defaultirishphoneformat

        formattedphonenumber = ""
        for character in format:
            if character == "#":
                if temp:
                    formattedphonenumber += temp[0]
                    temp = temp[1:]
            elif character == "*":
                if temp:
                    formattedphonenumber += temp
                temp = ""
            else:
                formattedphonenumber += character
        
        if not formattedphonenumber[-1] in ["0","1","2","3","4","5","6","7","8","9"]:
            raise ValueError, str(phonenumber) + " is not a valid Irish Phone Number."
        
        return str.__new__(cls, formattedphonenumber)



if __name__ == '__main__':
    test = IrishPhoneNumber("1234", defaultAreaCode="021")
    print test
 