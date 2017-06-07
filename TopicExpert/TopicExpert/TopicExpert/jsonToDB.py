import json
import sqlite3
import os

def reset_db():
    delete_db()
    create_db()


def connect_db(dbFileName):
    file_dir = os.path.dirname(__file__)
    dbpath = 'db\\' + dbFileName + '.db'
    filename = os.path.join(file_dir, dbpath)
    return sqlite3.connect(filename)


def delete_db(dbFileName, dbName):
    conn = connect_db(dbFileName)
    c = conn.cursor()
    c.executescript('drop table if exists ?', dbName)
    conn.close()

def create_mail_db(dbFileName):
    conn = connect_db(dbFileName)
    c = conn.cursor()

    c.executescript('''create table if not exists Mail(
                                emailId text,
                                conversationId text,
                                senderEmail text,
                                senderName text,
                                subject text,
                                body text,
                                uniqueBody text,
                                constraint unique_row unique (emailId)
                                )''')
    conn.close()

def create_topics_db(dbFileName):
    conn = connect_db(dbFileName)
    c = conn.cursor()

    c.executescript('''create table if not exists Topics(
                                id text,
                                score numeric,
                                keyPhrase text,
                                constraint unique_row unique (id)
                                )''')
    conn.close()

def create_topic_assignments_db(dbFileName):
    conn = connect_db(dbFileName)
    c = conn.cursor()

    c.executescript('''create table if not exists TopicAssignments(
                                topicId text,
                                documentId text,
                                distance numeric
                                )''')
    conn.close()

def jsonParser(mail_json):
    dbobject = []

    for mail in mail_json['value']:
        mailobject = []
        mailobject.append(mail['id'])
        mailobject.append(mail['conversationId'])
        mailobject.append(mail['sender']['emailAddress']['address'])
        mailobject.append(mail['sender']['emailAddress']['name'])
        mailobject.append(mail['subject'])
        mailobject.append(mail['body']['content'])
        mailobject.append(mail['uniqueBody']['content'])

        dbobject.append(mailobject.copy())

    return dbobject

def topicsParser(topics):
    dbobject = []
    for topic in topics:
        topicobject = []
        topicobject.append(topic['id'])
        topicobject.append(int(topic['score']))
        topicobject.append(topic['keyPhrase'])
        
        dbobject.append(topicobject.copy())

    return dbobject

def topicAssignmentsParser(topicAssignments):
    dbobject = []
    for assignment in topicAssignments:
        topicobject = []
        topicobject.append(assignment['topicId'])
        topicobject.append(assignment['documentId'])
        topicobject.append(float(assignment['distance']))
        
        dbobject.append(topicobject.copy())

    return dbobject

def mailToDB(mail_json, dbFileName):
    conn = connect_db(dbFileName)
    c = conn.cursor()

    dbobject = jsonParser(mail_json)

    print("Adding Values")
    
    create_mail_db(dbFileName)

    c.executemany('insert or replace into Mail values (?,?,?,?,?,?,?)', dbobject)

    conn.commit()
    conn.close()

def emailFromDB(email_id , dbFileName):
    conn = connect_db(dbFileName)
    c = conn.cursor()
    c.execute('select * from Mail order by rowid limit 1 offset ?', [str(email_id)])
    email = c.fetchone()
    conn.close()
    return email

def topicsToDB(topics, dbFileName):
    conn = connect_db(dbFileName)
    c = conn.cursor()

    dbobject = topicsParser(topics)

    create_topics_db(dbFileName)

    c.executemany('insert or replace into Topics values (?,?,?)', dbobject)

    conn.commit()
    conn.close()

def topicAssignmentsToDB(topicAssignments,dbFileName):
    conn = connect_db(dbFileName)
    c = conn.cursor()

    dbobject = topicAssignmentsParser(topicAssignments)

    create_topic_assignments_db(dbFileName)

    c.executemany('insert or replace into TopicAssignments values (?,?,?)', dbobject)

    conn.commit()
    conn.close()

def topicsForEmail(emailId,dbFileName):
    conn = connect_db(dbFileName)
    c = conn.cursor()
    c.execute('select * from TopicAssignments where documentId = ?', [emailId])

    assignments = c.fetchall()
    topics = []
    for assignment in assignments:
        c.execute('select * from Topics where id = ?', [assignment[0]])
        topic = c.fetchone()
        topics.append([topic[2], assignment[2], topic[1]])

    conn.close()

    return topics

def folderParser (folder_json):
    return