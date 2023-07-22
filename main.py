from flask import Flask, render_template, request, redirect, url_for, session, flash
from authlib.integrations.flask_client import OAuth
from google.cloud import datastore
from google.cloud.datastore import Entity

app = Flask(__name__)

app.secret_key = 'SECRET_KEY'

client = datastore.Client()

accounts_kind = "Account"

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

datastore_client = datastore.Client()

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
    user_key = datastore_client.key('User', userinfo['sub'])
    existing_user = datastore_client.get(user_key)

    if not existing_user:
        # User does not exist yet, create new Entity
        user = datastore.Entity(key=user_key)
        user.update({
            'email': userinfo['email'],
            'name': userinfo['name'],  
            'picture': userinfo['picture'],
            'sub': userinfo['sub']
        })
        datastore_client.put(user)

    # Store token and redirect to profile
    session['jwt_payload'] = userinfo
    session['profile'] = {
        'user_id': userinfo['sub'],
        'name': userinfo['name'],
        'picture': userinfo['picture']
    }
    
    return redirect(url_for('user_profile', sub=userinfo['sub']))

@app.before_request
def before_request():
    session['jwt_payload'] = None
    session['profile'] = None

# CLAUDE (WEEK4)  
def get_user(sub):
    key = datastore_client.key('User', sub)
    return datastore_client.get(key)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/user_profile/<sub>')
def user_profile(sub):
    user_key = datastore_client.key('User', sub)
    user = datastore_client.get(user_key)
    
    return render_template('user_profile.html', user=user)

# CLAUDE (WEEK4)  
@app.route('/scores/<sub>')
def scores(sub):
    return render_template('scores.html')

# CLAUDE (WEEK4)  
@app.route('/quizzes/<sub>')
def quizzes(sub):
    return render_template('quizzes.html')

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
        user_key = datastore_client.key('User', sub)  
        datastore_client.delete(user_key)

        # Flash confirmation message
        flash('Account deleted', 'success')

        # Clear session
        session.clear()  

        return redirect(url_for('login'))

    else:
    
        # GET request - Render confirmation page 
        return render_template('delete_confirmation.html', sub=sub)



if __name__ == '__main__':
    app.run(debug=True)
