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
from six.moves.urllib.request import urlopen
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

# Update the values of the following 3 variables
CLIENT_ID = '2r0PPGAOS2oBYlLYgtnSq2BaBSMyVQUz'
CLIENT_SECRET = 'Y_F4LcRxDvIj2qksWC6h6RJAtxxAR5kI0WPrcPTjZ-ziYt9vit8KC6IJPMl51nMv'
DOMAIN = '476-summer-2023.us.auth0.com'

ALGORITHMS = ["RS256"]

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

app.register_blueprint(view_quizzes)
app.register_blueprint(view_scores)
app.register_blueprint(view_questions)
app.register_blueprint(view_answers)

@app.route('/')
def index():
    return 'Hello world'

# NOT BING: START
# This code is adapted from https://auth0.com/docs/quickstart/backend/python/01-authorization?_ga=2.46956069.349333901.1589042886-466012638.1589042885#create-the-jwt-validation-decorator
class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code

@app.errorhandler(AuthError)
def handle_auth_error(ex):
    response = jsonify(ex.error)
    response.status_code = ex.status_code
    return response


# Verify the JWT in the request's Authorization header
def verify_jwt(request):
    if 'Authorization' in request.headers:
        auth_header = request.headers['Authorization'].split()
        token = auth_header[1]
    else:
        raise AuthError(
            {"code": "no auth header",
             "description":
                 "Authorization header is missing"}, 401
            )
    print("Authorization header exists")

    jsonurl = urlopen("https://" + DOMAIN + "/.well-known/jwks.json")
    jwks = json.loads(jsonurl.read())
    print("JWKS")
    print(jwks)
    try:
        unverified_header = jwt.get_unverified_header(token)
        print("UNVERIFIED_HEADER")
        print(unverified_header)
    except jwt.JWTError:
        raise AuthError(
            {"code": "invalid_header",
             "description":
                 "Invalid header. "
                 "Use an RS256 signed JWT Access Token"}, 401
            )
    print("Authorization header valid")

    if unverified_header["alg"] == "HS256":
        raise AuthError(
            {"code": "invalid_header",
             "description":
                 "Invalid header. "
                 "Use an RS256 signed JWT Access Token"}, 401
            )
    print("Authorization header not HS256")

    rsa_key = {}
    for key in jwks["keys"]:
        if key["kid"] == unverified_header["kid"]:
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"]
            }
    if rsa_key:
        try:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=ALGORITHMS,
                audience=CLIENT_ID,
                issuer="https://" + DOMAIN + "/"
            )
        except jwt.ExpiredSignatureError:
            raise AuthError(
                {"code": "token_expired",
                 "description": "token is expired"}, 401
                )

        except jwt.JWTClaimsError:
            raise AuthError(
                {"code": "invalid_claims",
                 "description":
                     "incorrect claims,"
                     " please check the audience and issuer"}, 401
                )

        except Exception:
            raise AuthError(
                {"code": "invalid_header",
                 "description":
                     "Unable to parse authentication"
                     " token."}, 401
                )

        print("token not expired")
        print("claims valid")
        print("authentication parsed")

        return payload
    else:
        print("no RSA key")
        raise AuthError(
            {"code": "no_rsa_key",
             "description":
                 "No RSA key in JWKS"}, 401
            )


# Decode the JWT supplied in the Authorization header
@app.route('/decode', methods=['GET'])
def decode_jwt():
    payload = verify_jwt(request)
    return payload


# NOT BING: END


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
