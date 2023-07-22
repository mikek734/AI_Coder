from main import request, json, jsonify, make_response
from main import datastore
from jwt import *
from flask import Blueprint

client = datastore.Client()
USERS = "users"
QUIZZES = "quizzes"
SCORES = "scores"
QUESTIONS = "questions"
ANSWERS = "answers"

view_scores = Blueprint('view_scores', __name__)


@view_scores.route('/quizzes/quiz_id/scores', methods=['GET', 'POST'])
def scores_get_post():

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

        quiz_key = client.key('Quiz', data['quiz_id'])
        if not client.get(quiz_key):
            return jsonify({'error': 'Invalid quiz ID'}), 400

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

        # Update Quiz Entity to maintain referential integrity
        quiz = client.get(quiz_key)
        quiz['score_ids'].append(new_score.id)
        client.put(quiz)

        client.put(new_score)

        return jsonify(score_to_dict(new_score)), 201

    elif request.method == 'GET':
        quiz_id = request.args.get('quiz_id')
        query = client.query(kind='Score')
        query.add_filter('quiz_id', '=', int(quiz_id))
        scores = list(query.fetch())

        return jsonify([score_to_dict(s) for s in scores]), 200


def score_to_dict(score):
    return {
        'ScoreID': score.id,
        'CandidateName': score['CandidateName'],
        'PercentScore': score['PercentScore'],
        'RawScore': score['RawScore'],
        'TimeTaken': score['TimeTaken'],
        'QuizID': score['QuizID']
    }


# Endpoint specifically for adding/deleting a score to/from a quiz, if desired
@view_scores.route('/quizzes/<quiz_id>/scores/<score_id>', methods=['DELETE', 'POST'])
def add_delete_score_from_quiz(quiz_id, score_id):

    if request.method == 'POST':

        # POST Score to Quiz Entity
        quiz_key = client.key(QUIZZES, quiz_id)
        quiz = client.get(quiz_key)

        if score_id not in quiz['score_ids']:
            quiz['score_ids'].append(score_id)
            client.put(quiz)

        # POST Score to Score Entity
        query = client.query(kind=SCORES)
        scores = list(query.fetch())
        for score in scores:
            if score_id == score.id:
                return 'Score already in Scores database', 400

        new_score = client.get(client.key(SCORES, score_id))
        client.put(new_score)
        return '', 201

    if request.method == 'DELETE':

        # DELETE Score From Quiz Entity
        quiz = client.get(client.key(QUIZZES, quiz_id))
        quiz['score_ids'].remove(score_id)
        client.put(quiz)

        # DELETE Score From Score Entity
        score = client.get(client.key(SCORES, score_id))
        client.delete(score)

        return '', 204


# DELETE a Score
@view_scores.route('/scores/<score_id>', methods=['DELETE'])
def delete_score(score_id):
    if request.method == 'DELETE':
        # DELETE Score from any Quizzes
        query = client.query(kind=QUIZZES)
        quizzes = list(query.fetch())
        for quiz in quizzes:
            if score_id in quiz['score_ids']:
                quiz['score_ids'].remove(score_id)
                client.put(quiz)

        # DELETE Score from Score Entity
        score = client.get(client.key(SCORES, score_id))
        client.delete(score)
        return '', 204
