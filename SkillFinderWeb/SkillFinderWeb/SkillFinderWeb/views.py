"""
Routes and views for the flask application.
"""
from SkillFinderWeb.mailparser import *

from datetime import datetime, timedelta
from flask import Flask, redirect, url_for, session, request, jsonify, render_template, Response, stream_with_context
from SkillFinderWeb import app, microsoft, db, table_service, Entity
from SkillFinderWeb.textanalytics import create_payload, testMe
from functools import wraps

import time
import re
import requests
import json
import uuid
import sys
import bs4

def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'microsoft_token' in session:
            if session['expires_at'] > datetime.now():
                print(session['expires_at'])
                return f(*args, **kwargs)
            elif 'refresh_token' in session:
                # Try to get a Refresh Token
                data = {}
                data['grant_type'] = 'refresh_token'
                data['refresh_token'] = session['refresh_token']
                data['client_id'] = microsoft.consumer_key
                data['client_secret'] = microsoft.consumer_secret

                response = (microsoft.post(microsoft.access_token_url, data=data)).data
                #Not sure if this is the right check... might need to revisit this code
                if response is None:
                    session.clear()
                    print("Access Denied: Reason=%s\nError=%s" % (response.get('error'),request.get('error_description')))
                    return redirect(url_for('index'))
                else:
                    session['microsoft_token'] = (response['access_token'], '')
                    session['expires_at'] = datetime.now() + timedelta(seconds=int(response['expires_in']))
                    session['refresh_token'] = response['refresh_token']
                    return f(*args, **kwargs)
        else:
            return redirect(url_for('login'))
    return wrap

@app.route('/')
def index():
    """Renders the index page."""

    return render_template(
        'index.html',
        title='Unauthenticated: Index Page',
        year=datetime.now().year,
    )

@app.route('/home')
@login_required
def home():
    me = microsoft.get('me')
    user = Entity()
    user.PartitionKey = microsoft.get('organization').data['value'][0]['id']
    user.RowKey = microsoft.get('me').data['id']
    try:
        user = table_service.get_entity('users', user.PartitionKey, user.RowKey)
        if len(user.suggestedSkills) < 3:
            print("No suggested skills found, redirecting to sent mail", user.suggestedSkills)
            return redirect('/sentMail')
        else:
            print("Skills found, redirecting to the skills page")
            return redirect('/skills')
    except:
        print("No user was found in Azure tables, redirecting to sent mail")
        return redirect('/sentMail')

@app.route('/sentMail')
@login_required
def sentMail():  
    if 'microsoft_token' in session:
        token = session['microsoft_token']
    else:
        token = None
    return render_template('progress.html', token=token)


@app.route('/progress')
@login_required
def progress():
    return Response(create_payload(), mimetype= 'text/event-stream')


@app.route('/login', methods = ['POST', 'GET'])
def login():

    # This is login
    if 'microsoft_token' in session:
        return redirect(url_for('home'))

    # Generate the guid to only accept initiated logins
    guid = uuid.uuid4()
    session['state'] = guid

    return microsoft.authorize(callback=url_for('authorized', _external=True), state=guid)

@app.route('/logout', methods = ['POST', 'GET'])
def logout():
	session.clear()
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
    session['expires_at'] = datetime.now() + timedelta(seconds=int(response['expires_in']))
    if 'refresh_token' in response:
        session['refresh_token'] = response['refresh_token']
    return redirect(url_for('home'))

@app.route('/skills', methods=['GET', 'POST'])
@login_required
def showskills():
    if request.method == 'GET':
        user = Entity()
        user.PartitionKey = microsoft.get('organization').data['value'][0]['id']
        user.RowKey = microsoft.get('me').data['id']
        user = table_service.get_entity('users', user.PartitionKey, user.RowKey)
        print(user.confirmedSkills, user)
        confirmed = remove_quotes(user.confirmedSkills)
        confirmed_list = confirmed.split(",") if len(confirmed) > 0 else []
        other = remove_quotes(user.suggestedSkills)
        other_list = other.split(",") if len(user.suggestedSkills) > 0 else []
        print("Got skills from Azure Tables:", confirmed)
        return render_template('showskills.html', confirmed=confirmed_list, other=other_list)

    if request.method == 'POST':
        print(request.content_type, request.json)
        data = request.json
        confirmed_data = data['confirmed']
        other_data = data['other']
        pub_choices = data['pubChoices']

        try:
            user = Entity()
            user.PartitionKey = microsoft.get('organization').data['value'][0]['id']
            user.RowKey = microsoft.get('me').data['id']
            confirmed = ",".join(confirmed_data) if len(confirmed_data) > 0 else ''
            suggested = ",".join(other_data) if len(other_data) > 0 else ''
            user.confirmedSkills = json.dumps(confirmed)
            user.suggestedSkills = json.dumps(suggested)
            table_service.insert_or_merge_entity('users', user)
        except:
            return json.dumps({'success': False}), 500, {'ContentType': 'application/json'}
        else:
            return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}

@app.route('/me')
def aboutMe():
    return render_template('me.html')

@app.route('/loadMe')
def loadMe():
    return Response(testMe(), mimetype= 'text/event-stream')

# If library is having trouble with refresh, uncomment below and implement refresh handler
# see https://github.com/lepture/flask-oauthlib/issues/160 for instructions on how to do this

# Implements refresh token logic
# @app.route('/refresh', methods=['POST'])
# def refresh():

@microsoft.tokengetter
def get_microsoft_oauth_token():
    return session.get('microsoft_token')

def remove_quotes(str):
    if str.startswith('"') and str.endswith('"'):
        return str[1:-1]
    else:
        return str

