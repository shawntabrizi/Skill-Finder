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
    c.execute('select * from AADTechTalk where rowid = ?', [str(email_id)])
    return c.fetchone()