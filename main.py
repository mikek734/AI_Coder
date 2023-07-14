from flask import Flask, render_template, request, make_response
from google.cloud import datastore
import requests
import json

app = Flask(__name__)

QUIZZES = "quizzes"
SCORES = "scores"

@app.route("/quizzes", methods=['GET'])
def list_quizzes():
    if request.method == 'GET':
        # Verify the user is logged in before showing quizzes

        # Get the user's quizzes from Cloud Datastore.
        client = datastore.Client()
        quizzes = client.query(kind=QUIZZES).fetch()

        # Create a list of rows to display the quizzes.
        rows = []
        for quiz in quizzes:
            row = [quiz.title, quiz.num_questions, quiz.last_modified]
            row.append(f"<a href='/scores/{quiz.key}'>View Scores</a>")
            rows.append(row)

        return render_template("quizzes.j2", rows=rows)
    else:
        return 'Method not recognized'

@app.route("/scores", methods=['GET'])
def scores():
    if request.method == 'GET':
        # Get the scores from Cloud Datastore.
        client = datastore.Client()
        scores = client.query(kind=SCORES).fetch()

        # Render the scores page.
        return render_template("scores.j2", scores=scores)
    else:
        return 'Method not recognized'

@app.route("/scores/<score_id>", methods=['GET'])
def individual_score(score_id):
    if request.method == 'GET':
        # Get the score from Cloud Datastore.
        client = datastore.Client()
        score = client.get(score_id)

        # Render the individual score page.
        return render_template("score.j2", score=score)
    else:
        return 'Method not recognized'


if __name__ == "__main__":
    app.run(debug=True)
