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
from config import PASSWORD, EMAIL
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
app.config['MAIL_USERNAME'] = EMAIL
app.config['MAIL_PASSWORD'] = PASSWORD
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


@app.route("/callback", methods=["GET", "POST"])
def callback():
    token = oauth.auth0.authorize_access_token()

    sub = token['userinfo']['sub']
    email = token['userinfo']['email']

    # Fetch the updated user from the Datastore
    user = fetch_user(sub)

    # If the user is not found in the Datastore, create a new user entity
    if user is None:
        user = {
            "name": token['userinfo']['name'],
            "email": email,
            "picture": token['userinfo']['picture']
        }

    # Update the session with the necessary user information
    session["user"] = {
        "sub": sub,
        "name": user["name"],
        "email": email,
        "picture": user["picture"],  # Use the picture URL from the Datastore
        "token": token["id_token"]  # Add the access token to the session
    }

    store_user(sub, user["name"], email, user["picture"])

    return redirect("/")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(
        "https://" + DOMAIN
        + "/v2/logout?"
        + urlencode(
            {
                "returnTo": url_for("index", _external=True),
                "client_id": CLIENT_ID,
            },
            quote_via=quote_plus,
        )
    )


@app.route('/')
def index():
    if session.get('user'):
        return redirect(url_for('user_profile', sub=session['user']['sub']))
    else:
        return render_template("index.html")


@app.route('/user_profile')
def user_profile():
    # Fetch the user from the session
    user = session.get('user')

    if not user:
        # User is not logged in or session expired
        return redirect(url_for('login'))

    return render_template('user_profile.html', user=user)


def store_user(sub, name, email, picture):
    # Create a key using the 'sub' value as the ID
    key = client.key(USERS, sub)

    # Check if user already exists in Datastore
    user_entity = client.get(key)

    if user_entity is None:
        # If the user doesn't exist, create a new entity with the key
        user_entity = datastore.Entity(key=key)
        user_entity["sub"] = sub

    # Update the user's details
    user_entity["name"] = name
    user_entity["email"] = email
    user_entity["picture"] = picture

    # Save the user entity to the Datastore
    client.put(user_entity)


def fetch_user(sub):
    query = client.query(kind=USERS)
    query.add_filter('sub', '=', sub)

    # Convert to list
    users = list(query.fetch())

    if users:
        # Return the first user found
        return users[0]
    else:
        # Return None if no user is found
        return None


# CLAUDE (WEEK4)
@app.route('/update_name/<sub>', methods=['GET', 'POST'])
def update_name(sub):

    query = client.query(kind=USERS)
    query.add_filter('sub', '=', sub)
    user = list(query.fetch())[0]

    if request.method == 'POST':
        name = request.form['name']

        user['name'] = name  # Update the 'name' property directly

        # Save the changes to the Datastore using the 'put' method of the client
        client.put(user)

        user = fetch_user(sub)

        session['user'] = user

        sub = user['sub']
        name = user['name']
        email = user['email']
        picture = user['picture']

        store_user(sub, name, email, picture)

        return redirect(url_for('user_profile', sub=sub))
    else:
        return render_template('update_name.html', user=user)


@app.route('/update_picture/<sub>', methods=['GET', 'POST'])
def update_picture(sub):

    query = client.query(kind=USERS)
    query.add_filter('sub', '=', sub)
    user = list(query.fetch())[0]

    if request.method == 'POST':
        picture = request.form['picture']

        user['picture'] = picture  # Update the 'name' property directly

        # Save the changes to the Datastore using the 'put' method of the client
        client.put(user)

        user = fetch_user(sub)

        session['user'] = user

        sub = user['sub']
        name = user['name']
        email = user['email']
        picture = user['picture']

        store_user(sub, name, email, picture)

        return redirect(url_for('user_profile', sub=sub))

    else:
        return render_template('update_picture.html', user=user)


@app.route('/delete_account/<sub>', methods=['POST', 'GET'])
def delete_account(sub):

    if request.method == 'POST':

        query = client.query(kind=USERS)
        query.add_filter('sub', '=', sub)
        user = list(query.fetch())[0]

        if user is None:
            return {'Error': 'No user with this sub exists'}, 404

        user_key = user.key

        client.delete(user_key)

        # Delete the user from Auth0
        delete_user_from_auth0(sub)

        return redirect(url_for('logout'))

    else:
        # GET request - Render confirmation page
        return render_template('delete_confirmation.html', sub=sub)


def delete_user_from_auth0(user_id):
    url = f"https://{DOMAIN}/api/v2/users/{user_id}"
    headers = {
        "Authorization": f"Bearer {get_auth0_access_token()}"
    }
    response = requests.delete(url, headers=headers)
    if response.status_code == 204:
        print("User successfully deleted from Auth0.")
    else:
        print("Failed to delete user from Auth0:", response.text)


def get_auth0_access_token():
    # Fetch an access token for the Auth0 Management API
    response = auth0.fetch_access_token()
    return response.get('access_token')


@app.route('/auth/<url>', methods=['GET'])
def add_authorization(url):
    token = session['user']['token']
    headers = {'Authorization': f'Bearer {token}'}

    # Build the URL using request.url_root and the desired path
    application_url = request.url_root + url

    response = requests.get(application_url, headers=headers)

    if response.status_code == 200:
        # Return the HTML content directly
        return make_response(response.text), 200
    else:
        return redirect("/")


@app.route('/scores/<sub>')
def scores(sub):
    return render_template('scores.j2', sub=sub)


@app.route('/quizzes/<sub>')
def quizzes(sub):
    return render_template('quizzes.j2', sub=sub)


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


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)