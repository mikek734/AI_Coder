from google.cloud import datastore
import requests

import json

import datetime
from os import environ as env

from dotenv import load_dotenv, find_dotenv
from flask import Flask
from flask import request, make_response, jsonify, redirect, render_template
from flask import session
from flask import url_for
from urllib.parse import quote_plus
from authlib.integrations.flask_client import OAuth
from six.moves.urllib.parse import urlencode
from jose import jwt
import jwt as pyjwt

from views.quizzes import view_quizzes
from views.scores import view_scores
from views.questions import view_questions
from views.answers import view_answers

# ENV_FILE = find_dotenv()
# if ENV_FILE:
#     load_dotenv(ENV_FILE)

app = Flask(__name__)
app.secret_key = env.get("APP_SECRET_KEY")

client = datastore.Client()

USERS = "users"
QUIZZES = "quizzes"
SCORES = "scores"
QUESTIONS = "questions"
ANSWERS = "answers"

URL = ""

# Auth0 configuration
# CLIENT_ID = env.get("AUTH0_CLIENT_ID")
# CLIENT_SECRET = env.get("AUTH0_CLIENT_SECRET")
# DOMAIN = env.get("AUTH0_DOMAIN")
#
# ALGORITHMS = ["RS256"]
#
# oauth = OAuth(app)

app.register_blueprint(view_quizzes)
app.register_blueprint(view_scores)
app.register_blueprint(view_questions)
app.register_blueprint(view_answers)

@app.route('/')
def index():
    return 'Hello world'


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
