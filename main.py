from flask import Flask, render_template, request, redirect, url_for, session
from authlib.integrations.flask_client import OAuth
from google.cloud import datastore
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)
datastore_client = datastore.Client()

# Auth0 configuration
app.config['AUTH0_CLIENT_ID'] = 'CLIENT_ID'
app.config['AUTH0_CLIENT_SECRET'] = 'CLIENT_SECRET'
app.config['AUTH0_DOMAIN'] = 'YOUR_DOMAIN.auth0.com'
oauth = OAuth(app)

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