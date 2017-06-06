import requests
import TopicExpert.appconfig as g
from TopicExpert.jsonToDB import *
import sys
import time

from bs4 import BeautifulSoup

def keyPhrases():
    url = "https://westus.api.cognitive.microsoft.com/text/analytics/v2.0/keyPhrases"


    headers = {  'Ocp-Apim-Subscription-Key' : g.apisecret,
                 'Content-Type' : 'application/json',
                 'Accept' : 'application/json'
                 }



    conn = connect_db()
    c = conn.cursor()
    c.execute("select * from AADTechTalk")
    data = c.fetchall()

    payload = { 'documents' : [] }

    for email in data:
        id = email[0]
        uniqueBody = email[6]
        soup = BeautifulSoup(uniqueBody)
        # kill all script and style elements
        for script in soup(["script", "style"]):
            script.decompose()    # rip it out

        text = soup.get_text(" ", strip=True)
        text = text.replace('\xa0', ' ')
        text = text.replace('\r\n', ' ')
        textSize = sys.getsizeof(text)
        if textSize > 9000:
            fraction = 9000/textSize
            charlen = fraction * len(text)
            text = text[:int(charlen)]

        payload['documents'].append({'id': id, 'text': text})


    r = requests.post(url, data=json.dumps(payload), headers=headers)

    responseJson = r.json()

    for mail in responseJson['documents']:
        c.execute("update AADTechTalk set keyPhrases = ? where emailId = ?", (str(mail['keyPhrases']), mail['id'])) 

    conn.commit()
    conn.close()

def topics():

    url = "https://westus.api.cognitive.microsoft.com/text/analytics/v2.0/topics"

    headers = {  'Ocp-Apim-Subscription-Key' : g.apisecret,
                 'Content-Type' : 'application/json',
                 'Accept' : 'application/json'
                 }



    conn = connect_db()
    c = conn.cursor()
    c.execute("select * from AADTechTalk")
    data = c.fetchall()

    payload = { 'documents' : [],
                'stopWords' : ['issue', 'error', 'user'],
                'stopPhrases' : ['Microsoft','Azure']
               }

    for email in data:
        id = email[0]
        uniqueBody = email[6]
        soup = BeautifulSoup(uniqueBody)
        # kill all script and style elements
        for script in soup(["script", "style"]):
            script.decompose()    # rip it out

        text = soup.get_text(" ", strip=True)
        text = text.replace('\xa0', ' ')
        text = text.replace('\r\n', ' ')
        textSize = sys.getsizeof(text)
        if textSize > 9000:
            fraction = 9000/textSize
            charlen = fraction * len(text)
            text = text[:int(charlen)]

        payload['documents'].append({'id': id, 'text': text})
        if sys.getsizeof(str(payload)) > 30000000:
            payload['documents'].pop()
            break


    r = requests.post(url, data=json.dumps(payload), headers=headers)

    if r.headers['Operation-Location']:
        oploc = r.headers['Operation-Location']
    elif r.headers['Location']:
        oploc = r.headers['Location']
    else:
        print("Error with Location of Operation")
        oploc = None

    status = True

    while (status):
        r2 = requests.get(oploc, headers=headers)
        r2dict = r2.json()
        if r2dict['status'] == 'Succeeded':
            status = False
        elif (r2dict['status'] != 'notStarted') or (r2dict['status'] != 'Running'):
            break
        else:
            time.sleep(60)


    responseJson = r2.json()

    topics = responseJson['operationProcessingResult']['topics']
    topicAssignments = responseJson['operationProcessingResult']['topicAssignments']

    topicsToDB(topics)
    topicAssignmentsToDB(topicAssignments)

    conn.close()