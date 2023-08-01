from flask import request, json, jsonify, redirect, render_template
from google.cloud import datastore
from flask import Blueprint
from authorization import *
from datetime import datetime
from werkzeug.datastructures import ImmutableMultiDict
from views.questions import questions_get_post, question_to_dict, questions_delete, get_quiz_questions

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

        return render_template("questions.j2", quiz=quiz, quiz_name=quiz_name, questions=questions), 200


# PROTECTED ROUTE
# POST a new blank Quiz if the Auth header contains a valid JWT
@view_quizzes.route('/quizzes/add', methods=['POST', 'GET'])
def quizzes_post():
    if request.method == 'POST':
        # TODO Add Authentication
        data = request.form

        # Rearranging the form data that was sent over by create_quiz.j2
        print(data)
        questions = {}

        # To identify each question, its 4 answer choices, and the correct answer
        for key, value in data.items():
            if 'question' in key:
                question_num = int(key.split('question')[1])
                questions[question_num] = {'question': value, 'answers': {}}
            elif 'correctAnswer' in key:
                questions[question_num]['correct'] = value  # store correct answer
            elif 'answer' in key:
                nums = key.split('_')
                answer_num = int(nums[1])
                questions[question_num]['answers'][answer_num] = value

        # To be able to print out the questions/answers
        # for question_num, question in questions.items():
        #
        #     print(f"Question {question_num}: {question['question']} {question['correct']}")
        #
        #     answers = question['answers']
        #
        #     for answer_num, answer in answers.items():
        #         print(f"  Answer {answer_num}: {answer}")
        #
        #     print()

        # Validate the quiz name
        for key, value in data.items():
            if 'QuizName' in key:
                try:
                    validate_quiz_data(data)
                except ValueError as e:
                    return jsonify({'error': str(e)}), 400

        # Validate the questions

        # Validate the user
        user_key = client.key(USERS, data['UserID'])
        user = client.get(user_key)

        if not user:
            return jsonify({'error': 'Invalid user'}), 400

        quiz = create_quiz(data)
        client.put(quiz)

        result = questions_get_post(request, questions, quiz_id=quiz.id)
        if isinstance(result, tuple) and result[1] != 201:
            return result

        return redirect('/quizzes'), 201

    elif request.method == 'GET':
        return render_template('create_quiz.j2'), 200


# PROTECTED ROUTE
# DELETE, PUT, or PATCH a specific quiz
@view_quizzes.route('/quizzes/<quiz_id>/edit', methods=['DELETE', 'PATCH', 'PUT', 'GET'])
def quizzes_delete_put_patch(quiz_id):
    if request.method == 'PATCH':
        data = request.get_json()

        # TODO Add Authentication
        # Extract and validate quiz data

        # Extract questions from the data
        questions = data.get('questions', [])

        # Process each question
        for question_data in questions:
            if 'id' in question_data:
                # This is an existing question
                if 'delete' in question_data and question_data['delete']:
                    # If the delete field is present and set to true, delete the question
                    delete_question_from_quiz(quiz_id, question_data['id'])
                else:
                    # If the delete field is absent or set to false, update the question
                    update_question_in_quiz(quiz_id, question_data['id'], question_data)
            else:
                # This is a new question, add it
                add_question_to_quiz(quiz_id, question_data)

        return redirect('/quizzes'), 200

    elif request.method == 'PUT':
        data = request.get_json()
        try:
            validate_quiz_data(data)
        except ValueError as e:

            return jsonify({'error': str(e)}), 400

        # Get existing quiz
        key = client.key(QUIZZES, int(quiz_id))
        quiz = client.get(key)

        # Update the quiz with new data
        quiz = update_quiz(quiz, data)
        client.put(quiz)

        # Extract questions from the data
        questions = data.get('questions', [])

        # Process each question
        for question_data in questions:
            if 'id' in question_data:
                # This is an existing question
                if 'delete' in question_data and question_data['delete']:
                    # If the delete field is present and set to true, delete the question
                    delete_question_from_quiz(quiz_id, question_data['id'])
                else:
                    # If the delete field is absent or set to false, update the question
                    update_question_in_quiz(quiz_id, question_data['id'], question_data)
            else:
                # This is a new question, add it
                add_question_to_quiz(quiz_id, question_data)

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
        quiz = client.get(client.key(QUIZZES, int(quiz_id)))
        quiz_name = quiz['QuizName']
        question_answer_pairs = []

        # First, call all the Questions and add them to the viewing list
        for question_id in quiz['QuestionIDs']:
            question = client.get(client.key(QUESTIONS, int(question_id)))
            options = []
            for answer in question['AnswerChoices']:
                options.append(answer)

            # Concatenate the question and its answers into one string
            # Also, include the correct answer in the tuple
            question_answer_pairs.append((question, '|'.join(options), question['CorrectAnswer']))

        return render_template("quizzes_edit.j2", quiz=quiz, quiz_name=quiz_name,
                               question_answer_pairs=question_answer_pairs), 200


def add_question_to_quiz(quiz_id, question_data):
    # TODO Add Authentication

    # POST Question to Quiz Entity
    quiz_key = client.key(QUIZZES, int(quiz_id))
    quiz = client.get(quiz_key)

    # Create a new question
    new_question = datastore.entity.Entity(key=client.key(QUESTIONS))
    new_question.update(question_data)
    client.put(new_question)

    # Add the question ID to the Quiz
    if new_question.id not in quiz['QuestionIDs']:
        quiz['QuestionIDs'].append(new_question.id)
        client.put(quiz)

    return new_question


def delete_question_from_quiz(quiz_id, question_id):
    # DELETE Question from Quiz Entity
    quiz = client.get(client.key(QUIZZES, int(quiz_id)))
    quiz['QuestionIDs'].remove(question_id)
    client.put(quiz)

    # DELETE Question from Question Entity
    question = client.get(client.key(QUESTIONS, int(question_id)))
    client.delete(question)


def update_question_in_quiz(quiz_id, question_id, question_data):
    # TODO Add Authentication

    # Get the existing question
    question_key = client.key(QUESTIONS, int(question_id))
    question = client.get(question_key)

    # Update the question with the new data
    question.update(question_data)

    # Put the updated question back into the datastore
    client.put(question)

    return question


def validate_quiz_data(data):
    if not isinstance(data['QuizName'], str):
        raise ValueError('Quiz name must be a string')


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
            'UserID': data['UserID'],
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
