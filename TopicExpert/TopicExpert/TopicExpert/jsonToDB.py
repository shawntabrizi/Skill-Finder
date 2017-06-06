import json
import sqlite3
import os

def reset_db():
    delete_db()
    create_db()


def connect_db():
    file_dir = os.path.dirname(__file__)
    filename = os.path.join(file_dir, 'db\mail.db')
    return sqlite3.connect(filename)


def delete_db():
    conn = connect_db()
    c = conn.cursor()
    c.executescript('drop table if exists AADTechTalk')
    conn.close()

def create_db():
    conn = connect_db()
    c = conn.cursor()

    c.executescript('''create table if not exists AADTechTalk(
                                emailId text,
                                conversationId text,
                                senderEmail text,
                                senderName text,
                                subject text,
                                body text,
                                uniqueBody text,
                                keyPhrases text,
                                constraint unique_row unique (emailId)
                                )''')
    conn.close()

def create_topics_db():
    conn = connect_db()
    c = conn.cursor()

    c.executescript('''create table if not exists AADTechTalkTopics(
                                id text,
                                score numeric,
                                keyPhrase text,
                                constraint unique_row unique (id)
                                )''')
    conn.close()

def create_topic_assignments_db():
    conn = connect_db()
    c = conn.cursor()

    c.executescript('''create table if not exists AADTechTalkTopicAssignments(
                                topicId text,
                                documentId text,
                                distance numeric
                                )''')
    conn.close()

def jsonParser( raw_json ):
    dbobject = []
    json_obj = raw_json
    for mail in json_obj['value']:
        mailobject = []
        mailobject.append(mail['id'])
        mailobject.append(mail['conversationId'])
        mailobject.append(mail['sender']['emailAddress']['address'])
        mailobject.append(mail['sender']['emailAddress']['name'])
        mailobject.append(mail['subject'])
        mailobject.append(mail['body']['content'])
        mailobject.append(mail['uniqueBody']['content'])
        mailobject.append(None)

        dbobject.append(mailobject.copy())

    return dbobject

def topicsParser( topics ):
    dbobject = []
    for topic in topics:
        topicobject = []
        topicobject.append(topic['id'])
        topicobject.append(int(topic['score']))
        topicobject.append(topic['keyPhrase'])
        
        dbobject.append(topicobject.copy())

    return dbobject

def topicAssignmentsParser( topicAssignments ):
    dbobject = []
    for assignment in topicAssignments:
        topicobject = []
        topicobject.append(assignment['topicId'])
        topicobject.append(assignment['documentId'])
        topicobject.append(float(assignment['distance']))
        
        dbobject.append(topicobject.copy())

    return dbobject

def jsonToDB( raw_json ):
    conn = connect_db()
    c = conn.cursor()

    dbobject = jsonParser(raw_json)

    print("Adding Values")

    c.executemany('insert or replace into AADTechTalk values (?,?,?,?,?,?,?,?)', dbobject)

    conn.commit()
    conn.close()

def emailFromDB( email_id ):
    conn = connect_db()
    c = conn.cursor()
    c.execute('select * from AADTechTalk order by rowid limit 1 offset ?', [str(email_id)])
    email = c.fetchone()
    conn.close()
    return email

def topicsToDB ( topics ):
    conn = connect_db()
    c = conn.cursor()

    dbobject = topicsParser(topics)

    c.executemany('insert or replace into AADTechTalkTopics values (?,?,?)', dbobject)

    conn.commit()
    conn.close()

def topicAssignmentsToDB ( topicAssignments ):
    conn = connect_db()
    c = conn.cursor()

    dbobject = topicAssignmentsParser(topicAssignments)

    c.executemany('insert or replace into AADTechTalkTopicAssignments values (?,?,?)', dbobject)

    conn.commit()
    conn.close()

def topicsForEmail( emailId ):
    conn = connect_db()
    c = conn.cursor()
    c.execute('select * from AADTechTalkTopicAssignments where documentId = ?', [emailId])

    assignments = c.fetchall()
    topics = []
    for assignment in assignments:
        c.execute('select * from AADTechTalkTopics where id = ?', [assignment[0]])
        topic = c.fetchone()
        topics.append([topic[2], assignment[2], topic[1]])

    conn.close()

    return topics