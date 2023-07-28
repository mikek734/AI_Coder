from flask import request, json, jsonify, redirect, render_template
from google.cloud import datastore
from flask import Blueprint
from authorization import *
from datetime import datetime

client = datastore.Client()
USERS = "users"
QUIZZES = "quizzes"
SCORES = "scores"
QUESTIONS = "questions"
ANSWERS = "answers"

view_quizzes = Blueprint('view_quizzes', __name__)


# PROTECTED ROUTE
# View all Quizzes made by User
@view_quizzes.route('/quizzes', methods=['GET'])
def quizzes_get():

    if request.method == 'GET':

        # TODO add Authentication
        # payload = verify_jwt(request)

        query = client.query(kind=QUIZZES)
        quizzes = list(query.fetch())

        return render_template("quizzes.j2", quizzes=quizzes), 200


# ROUTE WHERE CANDIDATE TAKES THE QUIZ
@view_quizzes.route('/quizzes/<quiz_id>', methods=['POST', 'GET'])
def quizzes_get_quiz(quiz_id):

    # This is what the candidate does when hitting 'Submit Quiz'
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

        quiz_key = client.key(QUIZZES, int(quiz_id))
        if not client.get(quiz_key):
            return jsonify({'error': 'Invalid quiz ID'}), 400

        # TODO Calculate quiz scores when the candidate hits Submit Quiz
        new_score = datastore.entity.Entity(key=client.key(SCORES))
        new_score.update(
            {
                'CandidateName': data['CandidateName'],
                'PercentScore': data['PercentScore'],
                'RawScore': data['RawScore'],
                'TimeTaken': data['TimeTaken'],
                'QuizID': int(quiz_id)
            }
        )

        client.put(new_score)

        # Update Quiz Entity to maintain referential integrity
        quiz = client.get(quiz_key)
        quiz['ScoreIDs'].append(new_score.id)
        client.put(quiz)

        scores = []
        for score_id in quiz['ScoreIDs']:
            score = client.get(client.key(SCORES, score_id))
            scores.append(score)  # append all of that individual Score's 'Score' attributes as a single object

        # TODO Decide on where to redirect candidate after they hit 'Submit Quiz'
        return redirect('/'), 201

    # This is what the candidate sees to take the quiz
    elif request.method == 'GET':

        quiz = client.get(client.key(QUIZZES, int(quiz_id)))

        quiz_name = quiz['QuizName']
        questions = []
        answers = []

        # First, call all the Questions and add them to the viewing list
        for question_id in quiz['QuestionIDs']:
            question = client.get(client.key(QUESTIONS, int(question_id)))
            questions.append(question)
            options = []
            for answer in question['AnswerChoices']:
                options.append(answer)
            answers.append(options)

        return render_template("questions.j2", quiz=quiz, quiz_name=quiz_name, questions=questions),\
               200


# PROTECTED ROUTE
# POST a new blank Quiz if the Auth header contains a valid JWT
@view_quizzes.route('/quizzes/add', methods=['POST', 'GET'])
def quizzes_post():

    if request.method == 'POST':

        # TODO Add Authentication
        data = request.get_json()

        try:
            validate_quiz_data(data)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400

        user_key = client.key(USERS, int(data['sub']))
        user = client.get(user_key)

        if not user:
            return jsonify({'error': 'Invalid user'}), 400

        quiz = create_quiz(data)

        client.put(quiz)

        return redirect('/quizzes'), 201

    elif request.method == 'GET':

        return render_template('quizzes_add.j2'), 200


# PROTECTED ROUTE
# DELETE, PUT, or PATCH a specific quiz
@view_quizzes.route('/quizzes/<quiz_id>/edit', methods=['DELETE', 'PATCH', 'PUT', 'GET'])
def quizzes_delete_put_patch(quiz_id):

    if request.method == 'PATCH':
        data = request.get_json()

        # TODO Add Authentication

        try:
            validate_quiz_data(data)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400

        key = client.key(QUIZZES, int(quiz_id))
        quiz = client.get(key)

        quiz = update_quiz(quiz, data)

        client.put(quiz)

        return redirect('/quizzes'), 200

    elif request.method == 'PUT':
        data = request.get_json()

        try:
            validate_quiz_data(data)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400

        quiz = create_quiz(data)
        key = client.key(QUIZZES, int(quiz_id))
        quiz.key = key

        client.put(quiz)

        return redirect('/quizzes'), 200

    elif request.method == 'DELETE':

        # Delete all Questions associated with Quiz
        quiz = client.get(client.key(QUIZZES, int(quiz_id)))
        query = client.query(kind=QUESTIONS)
        questions = list(query.fetch())
        for question in questions:
            if question.id in quiz['QuestionIDs']:
                client.delete(question)

        # Delete Quiz from Quiz Entity
        client.delete(quiz)

        return redirect('/quizzes'), 204

    elif request.method == 'GET':

        # TODO
        quiz = client.get(client.key(QUIZZES, int(quiz_id)))
        quiz_questions = []

        # Pull up the questions, if any
        question_query = client.query(kind=QUESTIONS)
        questions = list(question_query.fetch())
        for question in questions:
            if question.id in quiz["QuestionIDs"]:
                quiz_questions.append(question)

        return render_template('quizzes_edit.j2', quiz=quiz, questions=quiz_questions)


# PROTECTED ROUTE
# to be used with Quiz Edit page
# POST or DELETE a Quiz Question
@view_quizzes.route('/quizzes/<quiz_id>/questions/<question_id>', methods=['DELETE', 'POST'])
def add_delete_question_from_quiz(quiz_id, question_id):
    if request.method == 'POST':

        # TODO Add Authentication

        # POST Question to Quiz Entity
        quiz_key = client.key(QUIZZES, int(quiz_id))
        quiz = client.get(quiz_key)

        if question_id not in quiz['QuestionIDs']:
            quiz['QuestionIDs'].append(question_id)
            client.put(quiz)
        elif question_id in quiz['QuestionIDs']:
            return 'Question already exists in the Quiz Questions', 400

        # POST Question to Question Entity
        question = client.get(client.key(QUESTIONS, int(question_id)))
        if question_id == question.id:
            return 'Question already exists in Questions', 400

        client.put(question)
        return redirect('/quizzes/<quiz_id>/questions'), 201

    if request.method == 'DELETE':
        # DELETE Question from Quiz Entity
        quiz = client.get(client.key(QUIZZES, int(quiz_id)))
        quiz['QuestionIDs'].remove(question_id)
        client.put(quiz)

        # DELETE Question from Question Entity
        question = client.get(client.key(QUESTIONS, int(question_id)))
        client.delete(question)

        return redirect('/quizzes/<quiz_id>/questions'), 204


def validate_quiz_data(data):
    if not isinstance(data['QuizName'], str):
        raise ValueError('Quiz name must be a string')

    if not isinstance(data['NumberOfQuestions'], int):
        raise ValueError('Number of questions must be an integer')

    if not isinstance(data['LastModified'], str):
        raise ValueError('LastModified must be a string')


def update_quiz(quiz, data):
    quiz['QuizName'] = data['QuizName']
    quiz['NumberOfQuestions'] = data['NumberOfQuestions']
    quiz['LastModified'] = data['LastModified']
    quiz['UserID'] = quiz['UserID']

    return quiz


def create_quiz(data):
    quiz = datastore.entity.Entity(key=client.key(QUIZZES))
    quiz.update(
        {
            'QuizName': data['QuizName'],
            'NumberOfQuestions': data['NumberOfQuestions'],
            'LastModified': datetime.now().strftime("%m/%d/%Y %H:%M:%S"),
            'UserID': data['sub'],
            'QuestionIDs': [

            ],
            'ScoreIDs': [

            ]
        }
    )

    return quiz


def get_quiz(quiz_id):
    key = client.key(QUIZZES, int(quiz_id))
    return client.get(key)
