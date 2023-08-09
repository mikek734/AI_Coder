from google.cloud import datastore
from flask import request, jsonify, redirect, render_template
from flask import Blueprint

client = datastore.Client()
USERS = "users"
QUIZZES = "quizzes"
SCORES = "scores"
QUESTIONS = "questions"
ANSWERS = "answers"

view_scores = Blueprint('view_scores', __name__)


# View All Scores of a specific Quiz OR internally Post a new Score
@view_scores.route('/quizzes/<quiz_id>/scores', methods=['GET', 'POST'])
def get_post_scores(quiz_id):
    if request.method == 'POST':
        data = request.get_json()

        if not isinstance(data['CandidateName'], str):
            return jsonify({'error': 'Name must be a string'}), 400

        if not isinstance(data['PercentScore'], str):
            return jsonify({'error': 'Percent score must be a string'}), 400

        if not isinstance(data['RawScore'], str):
            return jsonify({'error': 'Raw score must be a string'}), 400

        if not isinstance(data['TimeTaken'], str):
            return jsonify({'error': 'Time taken must be a string'}), 400

        if not isinstance(data['QuizID'], int):
            return jsonify({'error': 'Quiz ID must be an integer'}), 400

        quiz_query = client.query(kind=QUIZZES)
        quizzes = list(quiz_query.fetch())
        for quiz in quizzes:
            if quiz.id == int(quiz_id):
                new_score = datastore.entity.Entity(key=client.key(SCORES))
                new_score.update(
                    {
                        'CandidateName': data['CandidateName'],
                        'PercentScore': data['PercentScore'],
                        'RawScore': data['RawScore'],
                        'TimeTaken': data['TimeTaken'],
                        'QuizID': data['QuizID']
                    }
                )

                client.put(new_score)

                # Update Quiz Entity to maintain referential integrity
                quiz['ScoreIDs'].append(new_score.id)
                client.put(quiz)

                return redirect('/quizzes/<quiz_id/scores'), 201

        return jsonify({'error': 'Invalid quiz ID'}), 400

    elif request.method == 'GET':
        quiz_query = client.query(kind=QUIZZES)
        quizzes = list(quiz_query.fetch())
        quiz_name = ''
        results = []
        for quiz in quizzes:

            if quiz.id == int(quiz_id):
                quiz_name = quiz['QuizName']
                for score_id in quiz['ScoreIDs']:
                    score = client.get(client.key(SCORES, int(score_id)))
                    results.append(score)

        return render_template("scores.j2", quiz_name=quiz_name, scores=results), 200


# View a Score or (internally) Delete a Score
@view_scores.route('/quizzes/<quiz_id>/scores/<score_id>', methods=['DELETE', 'GET'])
def delete_get_score(quiz_id, score_id):
    if request.method == 'DELETE':

        # DELETE Score from the Quiz
        quiz = client.get(client.key(QUIZZES, int(quiz_id)))
        quiz['ScoreIDs'].remove(score_id)
        client.put(quiz)

        # DELETE Score from Score Entity
        score = client.get(client.key(SCORES, int(score_id)))
        client.delete(score)
        return redirect('/quizzes/<quiz_id>/scores'), 204

    elif request.method == 'GET':

        quiz = client.get(client.key(QUIZZES, int(quiz_id)))
        quiz_name = quiz["QuizName"]

        for s_id in quiz['ScoreIDs']:
            if s_id == int(score_id):
                score = client.get(client.key(SCORES, int(score_id)))
                split_score = int((score["RawScore"]).split(' ')[1])

                return render_template(
                    "score.j2", score=score, total_questions=int((score["RawScore"]).split(' ')[3]), score_id=int(
                        score_id
                    ), quiz_name=quiz_name,
                    quiz_id=int(quiz_id)
                    ), \
                       200

        return 'Score by Score ID not found', 400