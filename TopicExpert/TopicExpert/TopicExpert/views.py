"""
Routes and views for the flask application.
"""

from TopicExpert.jsonToDB import *
from TopicExpert.textanalytics import *

from datetime import datetime
from flask import Flask, redirect, url_for, session, request, jsonify, render_template
from flask_oauthlib.client import OAuth, OAuthException
from TopicExpert import app, microsoft
import json
import re

import uuid

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods = ['POST', 'GET'])
def login():

    if 'microsoft_token' in session:
        return redirect(url_for('me'))

    # Generate the guid to only accept initiated logins
    guid = uuid.uuid4()
    session['state'] = guid

    return microsoft.authorize(callback=url_for('authorized', _external=True), state=guid)

@app.route('/home')
def home():
    me = microsoft.get('me')
    return render_template('home.html', me=str(me.data), token=str(session['microsoft_token']))

@app.route('/logout', methods = ['POST', 'GET'])
def logout():
	session.pop('microsoft_token', None)
	session.pop('state', None)
	return redirect(url_for('index'))

@app.route('/login/authorized')
def authorized():
	response = microsoft.authorized_response()

	if response is None:
		return "Access Denied: Reason=%s\nError=%s" % (
			response.get('error'), 
			request.get('error_description')
		)
		
	# Check response for state
	print("Response: " + str(response))
	if str(session['state']) != str(request.args['state']):
		raise Exception('State has been messed with, end authentication')
		
	# Okay to store this in a local variable, encrypt if it's going to client
	# machine or database. Treat as a password. 
	session['microsoft_token'] = (response['access_token'], '')

	return redirect(url_for('home')) 


@app.route('/folders/')
@app.route('/folders/<string:dbFileName>/')
def folders(dbFileName=None):
    if dbFileName is None:
        folders = microsoft.get('me/MailFolders?$top=1000')
        folderName = "Top Level Folder"
    else:
        folders = microsoft.get('me/MailFolders/{0}/childFolders?$top=1000'.format(dbFileName))
        folder = microsoft.get('me/MailFolders/{0}'.format(dbFileName))
        folderName = folder.data['displayName']

    return render_template('folders.html', folders=folders.data['value'], folderName=folderName)

@app.route('/folders/<string:dbFileName>/mail/')
@app.route('/folders/<string:dbFileName>/mail/<int:page_id>')
def mail(dbFileName, page_id=None):
    if page_id is None:
        return render_template('mail.html', folder=dbFileName)
    else:
        top = 1000
        skip = top * page_id

        messages = microsoft.get('me/MailFolders/{0}/messages?$top={1}&$skip={2}&$select=id,conversationId,uniqueBody,sender,subject,body'.format(dbFileName,top,skip))

        mailToDB(messages.data,dbFileName)

        return render_template('loadMail.html', messages=str(messages.data), next=page_id+1)

@app.route('/folders/<string:dbFileName>/topics/')
@app.route('/folders/<string:dbFileName>/topics/<int:email_id>')
def topics(dbFileName, email_id=0):
    email = emailFromDB(email_id, dbFileName)
    emailId = email[0]
    subject = email[4]
    uniqueBody = email[6]

    topics = topicsForEmail(emailId,dbFileName)

    uniqueBody = uniqueBody.replace('<html><body>','')
    uniqueBody = uniqueBody.replace('</body></html>','')
    uniqueBody = re.sub(r'<img.*?/?>','(image) ',uniqueBody)
    return render_template('topics.html', subject = subject, uniqueBody = uniqueBody, topics = topics, next=email_id+1, back=email_id-1)

@app.route('/folders/<string:dbFileName>/topics/analytics')
def tanalytics(dbFileName):
    topicAnalytics(dbFileName)
    return redirect(url_for('folders'))

@app.route('/folders/<string:dbFileName>/keyPhrases/')
@app.route('/folders/<string:dbFileName>/keyPhrases/<int:email_id>')
def keyPhrases(dbFileName, email_id=0):
    email = emailFromDB(email_id, dbFileName)
    subject = email[4]
    uniqueBody = email[6]
    uniqueBody = uniqueBody.replace('<html><body>','')
    uniqueBody = uniqueBody.replace('</body></html>','')
    uniqueBody = re.sub(r'<img.*?/?>','(image) ',uniqueBody)
    keyPhrases = email[7]
    return render_template('keyphrases.html', subject = subject, uniqueBody = uniqueBody, keyPhrases = keyPhrases, next=email_id+1, back=email_id-1)

# If library is having trouble with refresh, uncomment below and implement refresh handler
# see https://github.com/lepture/flask-oauthlib/issues/160 for instructions on how to do this

# Implements refresh token logic
# @app.route('/refresh', methods=['POST'])
# def refresh():

@microsoft.tokengetter
def get_microsoft_oauth_token():
    return session.get('microsoft_token')



