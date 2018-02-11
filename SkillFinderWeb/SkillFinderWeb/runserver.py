"""
This script runs the SkillFinderWeb application using a development server.
"""

from os import environ
from SkillFinderWeb import app

if __name__ == '__main__':
    HOST = environ.get('SERVER_HOST', 'localhost')
    if(HOST == 'localhost'):
        PORT = 50000
    else:
        try:
            PORT = int(environ.get('SERVER_PORT', '50000'))
        except ValueError:
            PORT = 50000
    app.run(HOST, PORT)
