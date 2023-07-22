from flask import Flask, redirect, request, render_template, session, url_for
from functools import wraps
from google.cloud import datastore
from authlib.integrations.flask_client import OAuth
from flask_mail import Mail, Message
from config import PASSWORD, EMAIL
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Google Cloud Datastore setup
datastore_client = datastore.Client()

# Flask-Mail configuration
app.config['MAIL_SERVER'] = 'sandbox.smtp.mailtrap.io'
app.config['MAIL_PORT'] = 2525
app.config['MAIL_USERNAME'] = EMAIL
app.config['MAIL_PASSWORD'] = PASSWORD
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False

mail = Mail(app)

# Auth0 configuration
app.config['AUTH0_CLIENT_ID'] = 'CLIENT_ID'
app.config['AUTH0_CLIENT_SECRET'] = 'CLIENT_SECRET'
app.config['AUTH0_DOMAIN'] = 'YOUR_DOMAIN.auth0.com'

# Auth0 configuration
oauth = OAuth(app)
auth0 = oauth.register(
    'auth0',
    client_id='your_auth0_client_id',
    client_secret='your_auth0_client_secret',
    api_base_url='https://your-auth0-domain.auth0.com',
    access_token_url='https://your-auth0-domain.auth0.com/oauth/token',
    authorize_url='https://your-auth0-domain.auth0.com/authorize',
    client_kwargs={
        'scope': 'openid profile email',
    },
)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'profile' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Retrieve form data
        username = request.form['username']
        password = request.form['password']
        # Save the account to Datastore
        # Your implementation here

        return redirect('/login')
    return render_template('register.html')


@app.route('/login')
def login():
    return auth0.authorize_redirect(redirect_uri='https://your-app-url.com/callback')


@app.route('/callback')
def callback():
    auth0.authorize_access_token()
    resp = auth0.get('userinfo')
    userinfo = resp.json()

    session['profile'] = {
        'user_id': userinfo['sub'],
        'username': userinfo['username'],
        'email': userinfo['email'],
        # Additional profile data
    }

    return redirect('/profile')


@app.route('/logout')
def logout():
    session.clear()
    params = {
        'returnTo': 'https://your-app-url.com',
        'client_id': 'your_auth0_client_id'
    }
    return redirect(auth0.api_base_url + '/v2/logout?' + urlencode(params))


@app.route('/profile')
@login_required
def profile():
    profile_data = session['profile']
    # Retrieve and display the employer's profile data from Datastore
    # Your implementation here

    return render_template('profile.html', profile=profile_data)


@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        # Retrieve form data and update the employer's profile in Datastore
        # Your implementation here

        return redirect('/profile')
    else:
        # Retrieve the employer's profile from Datastore and display it in the edit form
        # Your implementation here

        return render_template('edit_profile.html', profile=profile_data)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/home')
def home():
    return render_template('home.html')


@app.route('/account/delete')
def delete_account():
    return render_template('delete_account.html')


@app.route('/quizzes')
def view_all_quizzes():
    return render_template('view_all_quizzes.html')


@app.route('/quiz/edit')
def edit_quiz():
    return render_template('edit_quiz.html')


@app.route('/scores')
def view_all_scores():
    return render_template('view_all_scores.html')


@app.route('/score/<int:score_id>')
def view_score(score_id):
    return render_template('score.html', score_id=score_id)


@app.route('/send_email', methods=['POST'])
def send_email():
    msg = Message('Hello', sender=EMAIL, recipients=['kennedm4@oregonstate.edu'])
    msg.body = "This is the email body"
    mail.send(msg)
    return "Email has been sent!"


@app.route('/quizzes')
def quiz_list():
    quizzes = []
    query = datastore_client.query(kind='quiz')
    results = list(query.fetch())

    quizzes = []

    for result in results:
        quiz = {
            'id': result.id,
            'name': result['name'],
            'num_questions': result['num_questions'],
            'modified_date': result['modified_date'].strftime('%m/%d/%Y')
        }
        quizzes.append(quiz)

    return render_template('quiz_list.html', quizzes=quizzes)


@app.route('/scores')
def scores():
    scores = []

    query = datastore_client.query(kind='scores')
    results = list(query.fetch())

    scores = []

    for result in results:
        score = {
            'username': result['username'],
            'score': result['score'],
            'max_score': result['max_score'],
            'percent': round((result['score'] / result['max_score']) * 100),
            'time_taken': result['time_taken']
        }
        scores.append(score)

    return render_template('scores.j2', scores=scores)


@app.route('/score/<username>')
def score(username):
    # Get user score data from datastore
    query = datastore_client.query(kind='scores')
    query.add_filter('username', '=', username)
    results = list(query.fetch())
    user_score = results[0]

    # Create score report elements
    score = user_score['score']
    max_score = user_score['max_score']
    percent = round((score / max_score) * 100)
    time = user_score['time_taken']

    # Create pie chart
    labels = ['Correct', 'Incorrect']
    values = [user_score['correct_answers'], user_score['incorrect_answers']]
    fig, ax = plt.subplots()
    ax.pie(values, labels=labels, autopct='%1.1f%%')
    img = io.BytesIO()
    fig.savefig(img, format='png')
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode()

    return render_template(
        'score.j2',
        username=username,
        score=score,
        max_score=max_score,
        percent=percent,
        time=time,
        plot_url=plot_url
        )


if __name__ == "__main__":
    app.run(host='127.0.0.1', port=8080, debug=True)
