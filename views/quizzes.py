from main import request, json, jsonify, make_response
from main import datastore
from jwt import *
from flask import Blueprint
from datetime import datetime

client = datastore.Client()
USERS = "users"
QUIZZES = "quizzes"
SCORES = "scores"
QUESTIONS = "questions"
ANSWERS = "answers"

view_quizzes = Blueprint('view_quizzes', __name__)


# Create a quiz if the Auth header contains a valid JWT
@view_quizzes.route('/quizzes', methods=['POST', 'GET'])
def quizzes_get_post():
    if request.method == 'POST':
        quiz_name = request.form.get('QuizName')
        number_of_questions = request.form.get('NumberOfQuestions')
        last_modified = str(datetime.now())
        user_id = None#from JWT?

        # TODO
        # Verify JWT First

        if not isinstance(quiz_name, str):
            return jsonify({'error': 'Quiz name must be a string'}), 400

        if not isinstance(number_of_questions, str):
            return jsonify({'error': 'Number of questions must be a string'}), 400

        if not isinstance(last_modified, str):
            return jsonify({'error': 'Last modified must be a string'}), 400

        if not isinstance(user_id, int):
            return jsonify({'error': 'User ID must be an integer'}), 400

        user_key = client.key(USERS, user_id)
        user = client.get(user_key)

        if not user:
            return jsonify({'error': 'Invalid user ID'}), 400

        new_quiz = datastore.entity.Entity(key=client.key(QUIZZES))
        new_quiz.update(
            {
                'quiz_name': data['QuizName'],
                'num_questions': data['NumberOfQuestions'],
                'last_modified': data['LastModified'],
                'user_id': data['UserID'],
                'question_ids': [

                ],
                'score_ids': [

                ]
            }
        )

        client.put(new_quiz)

        return jsonify(quiz_to_dict(new_quiz)), 201

    elif request.method == 'GET':

        query = client.query(kind='Quizzes')
        quizzes = list(query.fetch())
        return jsonify([quiz_to_dict(q) for q in quizzes]), 200


def quiz_to_dict(quiz):
  return {
    'QuizID': quiz.id,
    'QuizName': quiz['QuizName'],
    'NumberOfQuestions': quiz['NumberOfQuestions'],
    'LastModified': quiz['LastModified']
  }


# DELETE, PUT, or PATCH a specific quiz
@view_quizzes.route('/quizzes/<quiz_id>', methods=['DELETE', 'PATCH', 'PUT'])
def quizzes_delete_put_patch(quiz_id):
    if request.method == 'PATCH':
        data = request.get_json()

        try:
            validate_quiz_data(data)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400

        key = client.key('Quizzes', quiz_id)
        quiz = client.get(key)

        quiz = update_quiz(quiz, data)

        client.put(quiz)

        return jsonify(quiz_to_dict(quiz)), 200

    elif request.method == 'PUT':
        data = request.get_json()

        try:
            validate_quiz_data(data)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400

        new_quiz = create_quiz(data)
        key = client.key('Quizzes', quiz_id)
        new_quiz.key = key

        client.put(new_quiz)

        return jsonify(quiz_to_dict(new_quiz)), 200

    elif request.method == 'DELETE':

        key = client.key('Quizzes', int(quiz_id))
        client.delete(key)

        return '', 204


def validate_quiz_data(data):
    if not isinstance(data['QuizName'], str):
        raise ValueError('Quiz name must be a string')

    if not isinstance(data['NumberOfQuestions'], int):
        raise ValueError('Number of questions must be an integer')

    if not isinstance(data['LastModified'], str):
        raise ValueError('LastModified must be a string')

    if not isinstance(data['UserID'], int):
        raise ValueError('UserID must be an integer')

    # Scores list
    # Questions list


def update_quiz(quiz, data):
  quiz['QuizName'] = data['QuizName']
  quiz['NumberOfQuestions'] = data['NumberOfQuestions']
  quiz['LastModified'] = data['LastModified']
  quiz['UserID'] = quiz['UserID']
  quiz['question_ids'] = quiz['question_ids']
  quiz['score_ids'] = quiz['score_ids']


def create_quiz(data):
  new_quiz = datastore.entity.Entity(key=client.key(QUIZZES))
  new_quiz.update({
    'QuizName': data['QuizName'],
    'NumberOfQuestions': data['NumberOfQuestions'],
    'LastModified': data['LastModified'],
    'UserID': data['UserID'],
    'question_ids': [

    ],
    'score_ids': [

    ]
  })


def get_quiz(quiz_id):
  key = client.key(QUIZZES, int(quiz_id))
  return client.get(key)


# Endpoint specifically for adding/deleting a quiz from a user, if desired
@view_quizzes.route('/users/<user_id>/quizzes/<quiz_id>', methods=['DELETE', 'POST'])
def add_delete_quiz_from_user(user_id, quiz_id):

    if request.method == 'POST':

        # POST Quiz to User Entity
        user_key = client.key(USERS, user_id)
        user = client.get(user_key)

        if quiz_id not in user['quiz_ids']:
            user['quiz_ids'].append(quiz_id)
            client.put(user)

        # POST Quiz to Quiz Entity
        query = client.query(kind=QUIZZES)
        quizzes = list(query.fetch())
        for quiz in quizzes:
            if quiz_id == quiz.id:
                return 'Quiz already in Quizzes database', 400

        new_quiz = client.get(client.key(QUIZZES, quiz_id))
        client.put(new_quiz)
        return '', 201

    if request.method == 'DELETE':

        # DELETE Quiz from User Entity
        user = client.get(client.key(USERS, user_id))
        user['quiz_ids'].remove(quiz_id)
        client.put(user)

        # DELETE Quiz from Quiz Entity
        quiz = client.get(client.key(QUIZZES, quiz_id))
        client.delete(quiz)

        return '', 204