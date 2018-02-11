"""
The flask application package.
"""

import SkillFinderWeb.appconfig as g

from flask import Flask
from flask_oauthlib.client import OAuth, OAuthException
import arango

from azure.storage.table import TableService, Entity
   
app = Flask(__name__)
app.debug = True
app.secret_key = 'development'

# Put your consumer key and consumer secret into a config file
# and don't check it into github!!
oauth = OAuth(app)

microsoft = oauth.remote_app(
	'microsoft',
	consumer_key=g.appid,
	consumer_secret=g.appsecret,
	request_token_params={'scope': 'User.Read Mail.Read'},
	base_url='https://graph.microsoft.com/v1.0/',
	request_token_url=None,
	access_token_method='POST',
	access_token_url='https://login.microsoftonline.com/common/oauth2/v2.0/token',
	authorize_url='https://login.microsoftonline.com/common/oauth2/v2.0/authorize'
)

def setup_arango_client():
    client = arango.ArangoClient(
        protocol='http',
        host=g.arangohost,
        port='8529',
        username='root',
        password=g.arangopw1,
        enable_logging=True
    )
    db = client.database('skills')
    return db

db = setup_arango_client()

#Connect to Azure Table
table_service = TableService(
    account_name=g.tablename,
    account_key=g.tablekey
)

import SkillFinderWeb.views
