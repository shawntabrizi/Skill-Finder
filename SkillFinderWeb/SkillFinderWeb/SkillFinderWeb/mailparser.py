import json
import re
import sys
from bs4 import BeautifulSoup

def parsemail(messages):
    objectLists = jsonParser(messages.data)

    return cleanList(objectLists)
    pass


def jsonParser(mail_json):
    dbobject = []
    if 'value' in mail_json.keys() and len(mail_json['value']) > 0:
        for mail in mail_json['value']:
            mailobject = []
            mailobject.append(mail['id'])
            mailobject.append(mail['uniqueBody']['content'])
            dbobject.append(mailobject.copy())

    return dbobject

def cleanList(objectLists):
    mails = dict()
    for email in objectLists:

        id = email[0]
        uniqueBody = email[1]

        soup = BeautifulSoup(uniqueBody)
        count = 0

        mail = []
        for img in soup.find_all('span'):
            if(count == 0):
                count+=1
                continue
            mail.append(img.get_text(" ", strip = True))

        mails[id] = mail

    nLinesToBeRemoved = filterSignature(list(mails.values()))

    mailsToBeReturned = []
    for id, mail in mails.items():
        #mail = mail[:-(nLinesToBeRemoved-1)]
        mail = [x for x in mail if not re.match(r'^b*[_\W]*$',x.strip())]
        
        isSkypeInviteOnly = False
        if(len(mail) > 0):
            try:
                indexOfSkypeInvite = mail.index("à Join Skype Meeting")

                if(indexOfSkypeInvite == 0):
                    isSkypeInviteOnly = True
                else:
                    mail = mail[0:indexOfSkypeInvite]

                print('index of skype:'+str(mail.index("à Join Skype Meeting")))
            except ValueError:
                None

            if(not isSkypeInviteOnly):
                mail = ''.join(str(elem) for elem in mail)
                # Filter out mails which are lesser than 50 characters.
                if(len(mail) >50):

                    mailToBeReturned  = dict()

                    mailToBeReturned['id'] = id
                    mailToBeReturned['text'] = mail 

                    mailsToBeReturned.append(mailToBeReturned)

    return mailsToBeReturned
    print(filterSignature(mails))

# Returns the number of lines that is common at the end of all Emails. 
def filterSignature(mails):

    for noOfLines in range(1, 10):
        map = dict()
        isFirstMail = True

        for i in range (0, int(len(mails)*.3)):
            mail = mails[i]
            if(len(mail) < noOfLines):
                # Exit from for loop because there is atleast one email without the signature of this length
                return noOfLines

            # Get Last N lines
            lastNLines = mail[-noOfLines]
            for line in lastNLines:
                # First mail so this would be the first occurance
                if(isFirstMail == True):
                    map[line.strip().lower()] = 1 
                else:
                    if(line.strip().lower() not in map):
                        return noOfLines
                    isFirstMail = False
    return 0
    # Take the last 5 lines



