import requests
from TopicExpert.jsonToDB import *

from bs4 import BeautifulSoup

url = "https://westus.api.cognitive.microsoft.com/text/analytics/v2.0/keyPhrases"

headers = {  'Ocp-Apim-Subscription-Key' : '2f6f29cc5d0d4f1d9a33373df2ea6911',
             'Content-Type' : 'application/json',
             'Accept' : 'application/json'
             }

payload = { 'documents' : [] }

conn = connect_db()
c = conn.cursor()
c.execute("select * from AADTechTalk")
data = c.fetchall()

for email in data[:100]:
    id = email[0]
    body = email[5]
    soup = BeautifulSoup(body)
    # kill all script and style elements
    for script in soup(["script", "style"]):
        script.decompose()    # rip it out

    text = soup.get_text(" ", strip=True)
    #text = text.strip()
    payload['documents'].append({'language': 'en', 'id': id, 'text': text})


r = requests.post(url, data=json.dumps(payload), headers=headers)