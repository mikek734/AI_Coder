from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from urllib.parse import quote_plus, urlencode
from authlib.integrations.flask_client import OAuth
from google.cloud import datastore
from google.cloud.datastore import Entity
import requests
import json 


app = Flask(__name__)
app.secret_key = 'SECRET_KEY'

client = datastore.Client()

users_kind = "User"

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
        raise AuthError({"code": "no auth header",
                            "description":
                                "Authorization header is missing"}, 401)
    print("Authorization header exists")

    jsonurl = urlopen("https://"+ DOMAIN+"/.well-known/jwks.json")
    jwks = json.loads(jsonurl.read())
    print("JWKS")
    print(jwks)
    try:
        unverified_header = jwt.get_unverified_header(token)
        print("UNVERIFIED_HEADER")
        print(unverified_header)
    except jwt.JWTError:
        raise AuthError({"code": "invalid_header",
                        "description":
                            "Invalid header. "
                            "Use an RS256 signed JWT Access Token"}, 401)
    print("Authorization header valid")

    if unverified_header["alg"] == "HS256":
        raise AuthError({"code": "invalid_header",
                        "description":
                            "Invalid header. "
                            "Use an RS256 signed JWT Access Token"}, 401)
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
                issuer="https://"+ DOMAIN+"/"
            )
        except jwt.ExpiredSignatureError:
            raise AuthError({"code": "token_expired",
                            "description": "token is expired"}, 401)

        except jwt.JWTClaimsError:
            raise AuthError({"code": "invalid_claims",
                            "description":
                                "incorrect claims,"
                                " please check the audience and issuer"}, 401)

        except Exception:
            raise AuthError({"code": "invalid_header",
                            "description":
                                "Unable to parse authentication"
                                " token."}, 401)
        
        print("token not expired")
        print("claims valid")
        print("authentication parsed")

        return payload
    else:
        print("no RSA key")
        raise AuthError({"code": "no_rsa_key",
                            "description":
                                "No RSA key in JWKS"}, 401)
    
# Decode the JWT supplied in the Authorization header
@app.route('/decode', methods=['GET'])
def decode_jwt():
    payload = verify_jwt(request)
    return payload     
# NOT BING: END


@app.route("/login")
def login():
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("callback", _external=True)
    )

@app.route("/callback", methods=["GET", "POST"])
def callback():
    token = oauth.auth0.authorize_access_token()

    sub = token['userinfo']['sub']
    name = token['userinfo']['name']
    email = token['userinfo']['email']
    picture = token['userinfo']['picture']

    # Fetch the updated user from the Datastore
    user = fetch_user(sub)

    # Update the session with the necessary user information
    session["user"] = {
        "sub": sub,
        "name": user["name"],
        "email": email,
        "picture": user["picture"]  # Use the picture URL from the Datastore
    }

    store_user(sub, name, email, picture)

    return redirect("/")



@app.route("/logout")
def logout():
    session.clear()
    return redirect(
        "https://" + DOMAIN
        + "/v2/logout?"
        + urlencode(
            {
                "returnTo": url_for("home", _external=True),
                "client_id": CLIENT_ID,
            },
            quote_via=quote_plus,
        )
    )


@app.route('/')
def home():
    if session.get('user'):
        return redirect(url_for('user_profile', sub=session['user']['sub']))
    else:
        return render_template("home.html")


@app.route('/user_profile/<sub>')
def user_profile(sub):
    print("Received sub:", sub)

    # Fetch the user from the session
    user = session.get('user')

    if not user:
        # User is not logged in or session expired
        return redirect(url_for('login'))

    print("User:", user)

    return render_template('user_profile.html', user=user)


def store_user(sub, name, email, picture):
    # Check if user already exists in Datastore
    query = client.query(kind=users_kind)
    query.add_filter("sub", "=", sub)
    existing_user = list(query.fetch())

    # Create or update the user entity
    user_entity = None
    if existing_user:
        user_entity = existing_user[0]
    else:
        user_entity = datastore.Entity(key=client.key(users_kind))
        user_entity["sub"] = sub

    user_entity["name"] = name
    user_entity["email"] = email
    user_entity["picture"] = picture

    client.put(user_entity)  

def fetch_user(sub):
    query = client.query(kind='User')
    query.add_filter('sub', '=', sub)

    # Convert to list
    users = list(query.fetch())   

    return users[0]


# CLAUDE (WEEK4)
@app.route('/update_name/<sub>', methods=['GET', 'POST'])
def update_name(sub):
    
    print("Received sub:", sub)

    query = client.query(kind='User')
    query.add_filter('sub', '=', sub)
    user = list(query.fetch())[0]
    print(request.url)

    print("User:", user)
    
    if request.method == 'POST':
        print("IN POST NOW")
        name = request.form['name']

        # chatgpt fixed claudes function (WEEK4)
        user['name'] = name  # Update the 'name' property directly

        # Save the changes to the Datastore using the 'put' method of the client
        client.put(user)

        user = fetch_user(sub)
        print("after fetch:", user['name'])

        session['user'] = user

        sub = user['sub']
        name = user['name']
        email = user['email']
        picture = user['picture']

        store_user(sub, name, email, picture)

        return redirect(url_for('user_profile', sub=sub))
    else:
        print("Sending:", user)
        return render_template('update_name.html', user=user)


@app.route('/update_picture/<sub>', methods=['GET', 'POST']) 
def update_picture(sub):

    print("Received sub:", sub)

    query = client.query(kind='User')
    query.add_filter('sub', '=', sub)
    user = list(query.fetch())[0]
    print(request.url)

    print("User:", user)
    
    if request.method == 'POST':
        print("IN POST NOW")
        picture = request.form['picture']

        user['picture'] = picture  # Update the 'name' property directly

        # Save the changes to the Datastore using the 'put' method of the client
        client.put(user)

        user = fetch_user(sub)
        print("after fetch:", user['picture'])

        session['user'] = user
        
        sub = user['sub']
        name = user['name']
        email = user['email']
        picture = user['picture']

        store_user(sub, name, email, picture)


        return redirect(url_for('user_profile', sub=sub))

    else:
        print("Sending:", user)
        return render_template('update_picture.html', user=user)



# updated by Claude to because deletion and page redirection wasn't working (WEEK 4)
@app.route('/delete_account/<sub>', methods=['POST', 'GET'])
def delete_account(sub):
    
    print("Received sub:", sub)

    if request.method == 'POST':

        query = client.query(kind='User')
        query.add_filter('sub', '=', sub)
        user = list(query.fetch())[0]
        print("User:", user)
        print(request.url)

        user_key = client.key(users_kind, sub)
        print("User key:", user_key)

        if user is None:
            return {'Error': 'No user with this sub exists'}, 404       
        
        client.delete(user_key)
        
        return redirect(url_for('logout'))

    else:
    
        # GET request - Render confirmation page 
        return render_template('delete_confirmation.html', sub=sub)

# CLAUDE (WEEK4)  
@app.route('/scores/<sub>')
def scores(sub):
    return render_template('scores.html', sub=sub)

# CLAUDE (WEEK4)  
@app.route('/quizzes/<sub>')
def quizzes(sub):
    return render_template('quizzes.html', sub=sub)

if __name__ == '__main__':
    app.run(debug=True)
