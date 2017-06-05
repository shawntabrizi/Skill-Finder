import requests
import TopicExpert.appconfig as g
from TopicExpert.jsonToDB import *

from bs4 import BeautifulSoup

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
    body = email[6]
    soup = BeautifulSoup(body)
    # kill all script and style elements
    for script in soup(["script", "style"]):
        script.decompose()    # rip it out

    text = soup.get_text(" ", strip=True)
    #text = text.strip()
    payload['documents'].append({'language': 'en', 'id': id, 'text': text})


r = requests.post(url, data=json.dumps(payload), headers=headers)

responseJson = r.json()

for mail in responseJson['documents']:
    c.execute("update AADTechTalk set keyPhrases = (?) where id = (?)", [str(mail['keyPhrases']), mail['id']]) 