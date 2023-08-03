from google.cloud import datastore
from google.cloud.datastore import Entity

import authorization
from authorization import *
import requests

import json

import datetime
from os import environ as env

from dotenv import load_dotenv, find_dotenv
from flask import Flask
from flask import request, make_response, jsonify, redirect, render_template, session, url_for, flash
from flask import session
from flask import url_for
from urllib.parse import quote_plus
from authlib.integrations.flask_client import OAuth
from six.moves.urllib.parse import urlencode
from six.moves.urllib.request import urlopen
from urllib.parse import quote_plus
from authlib.integrations.flask_client import OAuth
from six.moves.urllib.parse import urlencode
from jose import jwt
import jwt as pyjwt
from functools import wraps
from flask_mail import Mail, Message
# from config import PASSWORD, EMAIL
from constants import USERS, QUIZZES, QUESTIONS, ANSWERS, SCORES, CLIENT_ID, CLIENT_SECRET, DOMAIN
from views.quizzes import view_quizzes
from views.scores import view_scores
from views.questions import view_questions
from views.answers import view_answers

# ENV_FILE = find_dotenv()
# if ENV_FILE:
#     load_dotenv(ENV_FILE)

app = Flask(__name__)
app.secret_key = "APP_SECRET_KEY"

client = datastore.Client()

URL = ""

oauth = OAuth(app)

auth0 = oauth.register(
    'auth0',
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    api_base_url="https://" + DOMAIN,
    access_token_url="https://" + DOMAIN + "/oauth/token",
    authorize_url="https://" + DOMAIN + "/authorize",
    client_kwargs={
        'scope': 'openid profile email',
    },
    server_metadata_url=f'https://{DOMAIN}/.well-known/openid-configuration'
)

# Flask-Mail configuration
app.config['MAIL_SERVER'] = 'sandbox.smtp.mailtrap.io'
app.config['MAIL_PORT'] = 2525
# app.config['MAIL_USERNAME'] = EMAIL
# app.config['MAIL_PASSWORD'] = PASSWORD
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False

mail = Mail(app)


@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
    return response


@app.route("/login")
def login():
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("callback", _external=True)
    )


# updated by Claude to check if user already exists (WEEK 4)
@app.route('/callback')
def callback():
    # Initialize session
    session['jwt_payload'] = None
    session['profile'] = None

    auth0.authorize_access_token()
    resp = auth0.get('userinfo')
    userinfo = resp.json()

    # Check if user already exists
    user_key = client.key(USERS, userinfo['sub'])
    existing_user = client.get(user_key)

    if not existing_user:
        # User does not exist yet, create new Entity
        user = datastore.Entity(key=user_key)
        user.update({
            'email': userinfo['email'],
            'name': userinfo['name'],
            'picture': userinfo['picture'],
            'sub': userinfo['sub']
        })
        client.put(user)

    # Store token and redirect to home
    session['jwt_payload'] = userinfo
    session['profile'] = {
        'user_id': userinfo['sub'],
        'name': userinfo['name'],
        'picture': userinfo['picture']
    }
    return redirect(url_for('user_profile'))


# CLAUDE (WEEK4)
def get_user(sub):
    key = client.key(USERS, sub)
    return client.get(key)


@app.route('/user_profile')
def user_profile():
    sub = session['profile']['user_id']
    user_key = client.key(USERS, sub)
    user = client.get(user_key)

    return render_template('user_profile.html', user=user)


# CLAUDE (WEEK4)
@app.route('/update_name/<sub>', methods=['GET', 'POST'])
def update_name(sub):
    user = get_user(sub)

    if request.method == 'POST':
        name = request.form['name']

        # chatgpt fixed claudes function (WEEK4)
        user['name'] = name  # Update the 'name' property directly

        # Save the changes to the Datastore using the 'put' method of the client
        client = datastore.Client()
        client.put(user)

        return redirect(url_for('user_profile', sub=sub))

    return render_template('update_name.html', user=user)


# CLAUDE (WEEK4)
@app.route('/update_picture/<sub>', methods=['GET', 'POST'])
def update_picture(sub):
    user = get_user(sub)

    if request.method == 'POST':
        picture = request.form['picture']

        # chatgpt fixed claudes function (WEEK4)
        user['picture'] = picture  # Update the 'picture' property directly

        # Save the changes to the Datastore using the 'put' method of the client
        client = datastore.Client()
        client.put(user)

        return redirect(url_for('user_profile', sub=sub))

    return render_template('update_picture.html', user=user)


# updated by Claude to because deletion and page redirection wasn't working (WEEK 4)
@app.route('/delete_account/<sub>', methods=['GET', 'POST'])
def delete_account(sub):
    # Initialize session
    session['jwt_payload'] = None
    session['profile'] = None

    if request.method == 'POST':

        # Delete account
        user_key = client.key('User', sub)
        client.delete(user_key)

        # Flash confirmation message
        flash('Account deleted', 'success')

        # Clear session
        session.clear()

        return redirect(url_for('login'))

    else:

        # GET request - Render confirmation page
        return render_template('delete_confirmation.html', sub=sub)


app.register_blueprint(view_quizzes)
app.register_blueprint(view_scores)
app.register_blueprint(view_questions)
app.register_blueprint(view_answers)
app.register_blueprint(authorization.auth_bp)


@app.route('/send_email/<quiz_id>/<quiz_name>/<to_email>', methods=['GET'])
def send_email(quiz_id, quiz_name, to_email):
    quiz_url = request.url_root + 'quizzes/' + str(quiz_id)
    msg = Message('Technical Job Quiz', sender=EMAIL, recipients=[to_email])
    msg.html = f'<p>Someone at AI Coder has requested that you take the {quiz_name} quiz to test your ' \
               f'programming capabilities for employment.</p>' \
               f'<p>Please click the following to take the quiz: <a href="{quiz_url}">{quiz_name}</a></p>'
    mail.send(msg)
    return jsonify({'message': 'Email sent successfully'})


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
