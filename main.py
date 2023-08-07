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


@app.route("/login")
def login():
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("callback", _external=True)
    )

@app.route("/callback", methods=["GET", "POST"])
def callback():
    token = oauth.auth0.authorize_access_token()
    print("Token: ", token)

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
        "picture": user["picture"]  # Use the picture URL from the Datastore
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
    query = client.query(kind=users_kind)
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
    
    print("Received sub:", sub)

    query = client.query(kind=users_kind)
    query.add_filter('sub', '=', sub)
    user = list(query.fetch())[0]
    print(request.url)

    print("User:", user)
    
    if request.method == 'POST':
        print("IN POST NOW")
        name = request.form['name']

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

    query = client.query(kind=users_kind)
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


@app.route('/delete_account/<sub>', methods=['POST', 'GET'])
def delete_account(sub):
    
    print("Received sub:", sub)

    if request.method == 'POST':

        query = client.query(kind=users_kind)
        query.add_filter('sub', '=', sub)
        user = list(query.fetch())[0]
        print("User:", user)
        print(request.url)

        if user is None:
            return {'Error': 'No user with this sub exists'}, 404     

        user_key = user.key
        print("User key:", user_key)  
        
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

  
@app.route('/scores/<sub>')
def scores(sub):
    return render_template('scores.html', sub=sub)


@app.route('/quizzes/<sub>')
def quizzes(sub):
    return render_template('quizzes.html', sub=sub)

if __name__ == '__main__':
    app.run(debug=True)
