"""
Routes and views for the flask application.
"""

from TopicExpert.jsonToDB import *

from datetime import datetime
from flask import Flask, redirect, url_for, session, request, jsonify, render_template
from flask_oauthlib.client import OAuth, OAuthException
from TopicExpert import app, microsoft
import json
import re

import uuid

@app.route('/')
def index():
    return render_template('hello.html')

@app.route('/login', methods = ['POST', 'GET'])
def login():

    if 'microsoft_token' in session:
        return redirect(url_for('me'))

    # Generate the guid to only accept initiated logins
    guid = uuid.uuid4()
    session['state'] = guid

    return microsoft.authorize(callback=url_for('authorized', _external=True), state=guid)

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

	return redirect(url_for('me')) 

@app.route('/mail/<int:page_id>')
def mail(page_id):
    top = 1000
    skip = top * page_id
    messages = microsoft.get('me/MailFolders/AAMkADY3M2VkZjI4LTJjMjEtNGZhMS05MjBiLTU3ZWQyMDFkODc3ZgAuAAAAAADv9UQOpbLPRbfgtgI53-P4AQBAiZS0lTedQIHlewGxaW7RAFZOdABfAAA=/messages?$top={0}&$skip={1}&$select=id,conversationId,uniqueBody,sender,subject,body'.format(top,skip))

    with open('data.json', 'w') as outfile:
        json.dump(messages.data, outfile)
    jsonToDB(messages.data)
    return render_template('mail.html', messages=str(messages.data), next=page_id+1)

@app.route('/me')
def me():
    me = microsoft.get('me')
    return render_template('me.html', me=str(me.data), token=str(session['microsoft_token']))

# If library is having trouble with refresh, uncomment below and implement refresh handler
# see https://github.com/lepture/flask-oauthlib/issues/160 for instructions on how to do this

# Implements refresh token logic
# @app.route('/refresh', methods=['POST'])
# def refresh():

@microsoft.tokengetter
def get_microsoft_oauth_token():
    return session.get('microsoft_token')

@app.route('/keyPhrases/<int:email_id>')
def keyPhrases(email_id):
    email = emailFromDB(email_id+1)
    subject = email[4]
    uniqueBody = email[6]
    uniqueBody = uniqueBody.replace('<html><body>','')
    uniqueBody = uniqueBody.replace('</body></html>','')
    uniqueBody = re.sub(r'<img.*?/?>','(image) ',uniqueBody)
    keyPhrases = email[7]
    return render_template('keyphrases.html', subject = subject, uniqueBody = uniqueBody, keyPhrases = keyPhrases, next=email_id+1, back=email_id-1)