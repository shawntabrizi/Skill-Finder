"""
The flask application package.
"""

import TopicExpert.appconfig as g

from flask import Flask
from flask_oauthlib.client import OAuth, OAuthException
app = Flask(__name__)

# sslify = SSLify(app)
app.debug = True
app.secret_key = 'development'
oauth = OAuth(app)

# Put your consumer key and consumer secret into a config file
# and don't check it into github!!
microsoft = oauth.remote_app(
	'microsoft',
	consumer_key=g.appid,
	consumer_secret=g.appsecret,
	request_token_params={'scope': 'offline_access User.Read Mail.Read'},
	base_url='https://graph.microsoft.com/v1.0/',
	request_token_url=None,
	access_token_method='POST',
	access_token_url='https://login.microsoftonline.com/common/oauth2/v2.0/token',
	authorize_url='https://login.microsoftonline.com/common/oauth2/v2.0/authorize'
)

import TopicExpert.views