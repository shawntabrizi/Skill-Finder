"""
This script runs the TopicExpert application using a development server.
"""

from os import environ
from TopicExpert import app

if __name__ == '__main__':
    HOST = environ.get('SERVER_HOST', 'localhost')
    PORT = 50000
    app.run(HOST, PORT)
