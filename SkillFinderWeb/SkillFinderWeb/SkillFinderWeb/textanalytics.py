from flask import Flask, redirect, url_for, session, request, jsonify, render_template, Response, stream_with_context
from SkillFinderWeb import app, microsoft, db, table_service, Entity
import sys
import json
import re
import requests
import time
from SkillFinderWeb.mailparser import *
import SkillFinderWeb.appconfig as g

@stream_with_context
def create_payload():
    y_dict = {
        'step': None,
        'count': None,
        'message': None,
        'topics': [],
        'topicsRefined': []
        }

    payload = {
        'documents' : [],
        'stopWords' : [],
        'stopPhrases' : []
        }

    # Get and Parse Emails
    for i in get_parse_emails(payload, y_dict, 1):
        yield i

    # Topic Analysis API
    for i in topic_analysis(payload, y_dict):
        yield i

    # Get Enriched Skills
    for i in get_enriched_skills(y_dict):
        yield i

    # Save Topics to DB
    for i in save_topics(y_dict):
        yield i

    # Done!
    y_dict['step'] = 5
    y_dict['message'] = "We are done!"
    y_json = json.dumps(y_dict)
    yield 'data: ' + y_json + '\n\n'

def get_parse_emails(payload, y_dict, size):
    y_dict['step'] = 1
    y_dict['count'] = 0
    y_dict['message'] = "Setting up to get emails."
    y_json = json.dumps(y_dict)
    yield 'data: ' + y_json + '\n\n'

    #30 MB Limit (using 1mb to test)
    sizeLimit = size * 1024 * 1024

    full = False
    first_loop = True
    next_link = ''
    while not full:
        if first_loop:
            sent_mail = microsoft.get('me/MailFolders/SentItems/messages?$top=20&$select=subject,uniqueBody')
            first_loop = False
        else:
            sent_mail = microsoft.get(next_link)
        
        if '@odata.nextLink' in sent_mail.data:
            next_link = sent_mail.data['@odata.nextLink']
        else:
            full = True
        objectLists = jsonParser(sent_mail.data)
        filteredEmails = cleanList(objectLists)
        #print("Email cleanup:", len(objectLists), len(filteredEmails))
        for mail in filteredEmails:
            if sys.getsizeof(str(payload)) < sizeLimit:
                id = str(mail['id'])
                text = str(mail['text'])

                payload['documents'].append({ 'id': id, 'text':text })
                y_dict['count'] += 1
                y_dict['message'] = text
                y_json = json.dumps(y_dict)
                yield 'data: ' + y_json + '\n\n'

            else:
                del payload['documents'][-1]
                full = True
                y_dict['message'] = "Finished Collecting Emails"
                y_json = json.dumps(y_dict)
                print("Get emails output:", y_dict)
                yield 'data: ' + y_json + '\n\n'
                break
    if len(payload['documents']) == 0:
        y_dict['step'] == 0
        y_dict['message'] = "No emails collected. Try signing out and signing back in again."
        y_json = json.dumps(y_dict)
        yield 'data: ' + y_json + '\n\n'

def topic_analysis(payload, y_dict):
    y_dict['step'] = 2
    y_dict['count'] = 0
    y_dict['message'] = "Setting up to call Microsoft Cognitive Services' Text Analytics API"
    y_json = json.dumps(y_dict)
    yield 'data: ' + y_json + '\n\n'

    url = "https://westus.api.cognitive.microsoft.com/text/analytics/v2.0/topics"
    
    secret_count = 0
    status_code = 0

    while status_code != 202 and secret_count < len(g.apisecret):
        headers = {
            'Ocp-Apim-Subscription-Key' : g.apisecret[secret_count],
            'Content-Type' : 'application/json',
            'Accept' : 'application/json'
            }
        r = requests.post(url, data=json.dumps(payload), headers=headers)
        status_code = r.status_code
        
        y_dict['message'] = str(r.text)
        y_json = json.dumps(y_dict)
        yield 'data: ' + y_json + '\n\n'

        #print("TextAnalyticsResponse:", r.text)
        if status_code == 401 and 'invalid subscription key' in r.text:
            secret_count += 1
            y_dict['message'] += "\nTrying a new API Key..."
            y_json = json.dumps(y_dict)
            yield 'data: ' + y_json + '\n\n'

        elif status_code == 202:
            break

        else:
            y_dict['step'] = 0
            y_dict['message'] = "Something went wrong with calling the Text Analytics API"
            y_json = json.dumps(y_dict)
            yield 'data: ' + y_json + '\n\n'
            break

    if r.status_code == 202:
        if r.headers['Operation-Location']:
            oploc = r.headers['Operation-Location']
        elif r.headers['Location']:
            oploc = r.headers['Location']
        else:
            print("Error with Location of Operation")
            oploc = None
        print("Operation location: ", str(oploc))

        while True:
            r2 = requests.get(oploc, headers=headers)
            r2_dict = r2.json()

            if r2_dict['status'] == 'Succeeded':

                responseJson = r2.json()
                topics = responseJson['operationProcessingResult']['topics']
                topicAssignments = responseJson['operationProcessingResult']['topicAssignments']
                for topic in topics:
                    y_dict['topics'].append(topic['keyPhrase'])

                print('Text Analytics API Complete')
                y_dict['message'] = "Text Analytics API Complete"
                y_json = json.dumps(y_dict)
                yield 'data: ' + y_json + '\n\n'
                break

            elif (r2_dict['status'] != 'NotStarted') and (r2_dict['status'] != 'Running'):
                print('Error with the Text Analytics API')
                y_dict['step'] = 0
                y_dict['message'] = "Error with the Text Analytics API"
                y_json = json.dumps(y_dict)
                yield 'data: ' + y_json + '\n\n'
                break

            else:
                print('Analysis still running...')
                for i in range(0,60):
                    time.sleep(1)
                    y_dict['message'] = "Analysis still running. Will check again in " + str(60 - i) + " seconds."
                    y_dict['count'] += 1
                    y_json = json.dumps(y_dict)
                    yield 'data: ' + y_json + '\n\n'


# Queries the graph database to pull out skills related to the ones
# in the set from Text Analytics API. Returns a dictionary of confirmed skills (the ones for which a match was found in the graphDB)
# and other skills (the ones for which no match was found, and all the related skills from graph DB
# ranked by occurrence score
def get_enriched_skills(y_dict):
    # r3 =
    # requests.post("http://skillfindertags.azurewebsites.net/api/skillfindertags",
    # data=json.dumps({'values': y_dict['topics']}))
    # if r3.status_code == 200:
    #     responseJson = r3.json()
    #     y_dict['topicsRefined'] = responseJson
    #     y_json = json.dumps(y_dict)
    #     yield 'data: ' + y_json + '\n\n'
    y_dict['step'] = 3
    y_dict['count'] = 0
    y_dict['message'] = "Setting up to find skills."
    skill_graph = db.graph('skills_graph')
    otherskills = {}
    confirmedskills = {}
    for skill in y_dict['topics']:
        sk_key1 = re.sub('[\s&/]', '', skill)
        sk_key = re.sub('#', '', sk_key1)

        #print("Finding vertex", skill, sk_key)
        y_dict['message'] = "Finding vertex" + str(skill) + str(sk_key)
        y_json = json.dumps(y_dict)
        yield 'data: ' + y_json + '\n\n'

        vertname = 'skills_verts/' + sk_key
        verts = skill_graph.vertex_collection('skills_verts')
        if verts.has(sk_key):
            confirmedskills[skill] = 0
            # try this 4 times
            for attempt in range(4):
                try:
                    traverse = skill_graph.traverse(start_vertex=vertname,
                        direction='outbound',
                        strategy='bfs',
                        edge_uniqueness='global',
                        vertex_uniqueness='global',
                        max_depth=1,)
                    for path in traverse['paths']:
                        for p in path['vertices']:
                            if p['name'] != skill:
                                skill_name = p['name']
                                if skill_name in otherskills:
                                    otherskills[skill_name] += 1
                                else:
                                    otherskills[skill_name] = 1
                except:
                    print("Attempt %s unsuccessful" % attempt)
                    continue
                else:
                    break
        else:
            otherskills[skill] = 1
    for skill, count in confirmedskills.items():
        if skill in otherskills:
            confirmedskills[skill] = otherskills[skill]
    print("Other skills:", otherskills, "\nConfirmed skills:", confirmedskills)
    
    if len(confirmedskills) == 0 and len(otherskills) == 0:
        y_dict['step'] = 0
        y_dict['message'] = "Couldn't find any skills! :(  Don't worry, it is probabaly our fault, not yours."
        y_json = json.dumps(y_dict)
        yield 'data: ' + y_json + '\n\n'
    
    else:
        y_dict['message'] = "Skill Finding Complete."
        y_dict['topicsRefined'] = sorted(confirmedskills, key=confirmedskills.__getitem__, reverse=True)
        y_dict['topics'] = sorted(otherskills, key=otherskills.__getitem__, reverse=True)
        y_json = json.dumps(y_dict)
        yield 'data: ' + y_json + '\n\n'


def save_topics(y_dict):
    y_dict['step'] = 4
    y_dict['message'] = "Saving topics to DB."
    y_json = json.dumps(y_dict)
    yield 'data: ' + y_json + '\n\n'

    try:
        user = Entity()
        user.PartitionKey = microsoft.get('organization').data['value'][0]['id']
        user.RowKey = microsoft.get('me').data['id']
        confirmed = ",".join(y_dict['topicsRefined']) if len(y_dict['topicsRefined']) > 0 else ''
        suggested = ",".join(y_dict['topics']) if len(y_dict['topics']) > 0 else ''
        user.confirmedSkills = json.dumps(confirmed)
        user.suggestedSkills = json.dumps(suggested)
        table_service.insert_or_merge_entity('users', user)

        y_dict['message'] = "Sucessfully saved topics to DB!"
        y_json = json.dumps(y_dict)
        yield 'data: ' + y_json + '\n\n'

    except Exception as e:
        y_dict['step'] = 0
        y_dict['message'] = "We ran into a problem saving to DB: " + str(e)
        y_json = json.dumps(y_dict)
        yield 'data: ' + y_json + '\n\n'

@stream_with_context
def testMe():
    y_dict = {
        'step': None,
        'count': None,
        'message': None,
        'topics': [],
        'topicsRefined': []
        }

    payload = {
        'documents' : [],
        'stopWords' : [],
        'stopPhrases' : []
        }
    size = 5

    # Get and Parse Emails
    y_dict['step'] = 1
    y_dict['count'] = 0
    y_dict['message'] = "Setting up to get emails."
    y_json = json.dumps(y_dict)
    yield 'data: ' + y_json + '\n\n'

    #30 MB Limit (using 1mb to test)
    sizeLimit = size * 1024 * 1024

    full = False
    first_loop = True
    next_link = ''
    while not full:
        if first_loop:
            sent_mail = microsoft.get('me/MailFolders/SentItems/messages?$top=20&$select=subject,uniqueBody')
            first_loop = False
        else:
            sent_mail = microsoft.get(next_link)
        
        if '@odata.nextLink' in sent_mail.data:
            next_link = sent_mail.data['@odata.nextLink']
        else:
            full = True

        objectLists = jsonParser(sent_mail.data)
        filteredEmails = cleanList(objectLists)
        #print("Email cleanup:", len(objectLists), len(filteredEmails))
        for mail in filteredEmails:
            if sys.getsizeof(str(payload)) < sizeLimit:
                id = str(mail['id'])
                text = str(mail['text'])

                payload['documents'].append({ 'id': id, 'text':text })
                y_dict['count'] += 1
                y_dict['message'] = text
                y_json = json.dumps(y_dict)
                yield 'data: ' + y_json + '\n\n'

            else:
                del payload['documents'][-1]
                full = True
                y_dict['message'] = "Finished Collecting Emails"
                y_json = json.dumps(y_dict)
                print("Get emails output:", y_dict)
                yield 'data: ' + y_json + '\n\n'
                break
    if len(payload['documents']) == 0:
        y_dict['step'] == 0
        y_dict['message'] = "No emails collected. Try signing out and signing back in again."
        y_json = json.dumps(y_dict)
        yield 'data: ' + y_json + '\n\n'

    # Done!
    y_dict['step'] = 5
    y_dict['message'] = "We are done!"
    y_json = json.dumps(y_dict)
    yield 'data: ' + y_json + '\n\n'