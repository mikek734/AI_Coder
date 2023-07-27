from google.cloud import datastore
from flask import request, jsonify, redirect, render_template
from flask import Blueprint

client = datastore.Client()
USERS = "users"
QUIZZES = "quizzes"
SCORES = "scores"
QUESTIONS = "questions"
ANSWERS = "answers"

view_answers = Blueprint('view_answers', __name__)


@view_answers.route('/answers', methods=['GET', 'POST'])
def answers_get_post():
    if request.method == 'POST':
        data = request.get_json()

        if not isinstance(data['AnswerText'], str):
            return jsonify({'error': 'Answer text must be a string'}), 400

        if not isinstance(data['IsCorrect'], bool):
            return jsonify({'error': 'IsCorrect must be a boolean'}), 400

        question_key = client.key(QUESTIONS, int(data['QuestionID']))
        if not client.get(question_key):
            return jsonify({'error': 'Invalid question ID'}), 400

        new_answer = datastore.entity.Entity(key=client.key(ANSWERS))
        new_answer.update(
            {
                'AnswerText': data['AnswerText'],
                'IsCorrect': data['IsCorrect'],
                'QuestionID': data['QuestionID']
            }
        )

        client.put(new_answer)

        # Update Question Entity to maintain referential integrity
        question = client.get(question_key)
        question['AnswerIDs'].append(new_answer.id)
        client.put(question)

        return jsonify(answer_to_dict(new_answer)), 201

    elif request.method == 'GET':
        query = client.query(kind=ANSWERS)
        answers = list(query.fetch())
        return jsonify([answer_to_dict(a) for a in answers]), 200


def answer_to_dict(answer):
    return {
        'AnswerID': answer.id,
        'QuestionText': answer['AnswerText'],
        'IsCorrect': answer['IsCorrect'],
        'QuestionID': answer['QuestionID'],
    }


# Endpoint specifically for adding/deleting an answer to/from a question, if desired
@view_answers.route('/questions/<question_id>/answers/<answer_id>', methods=['DELETE', 'POST'])
def add_delete_answer_from_question(question_id, answer_id):
    if request.method == 'POST':

        # POST Answer to Question Entity
        question_key = client.key(QUESTIONS, int(question_id))
        question = client.get(question_key)

        if answer_id not in question['AnswerIDs']:
            question['AnswerIDs'].append(answer_id)
            client.put(question)

        # POST Answer to Answer Entity
        query = client.query(kind=ANSWERS)
        answers = list(query.fetch())
        for answer in answers:
            if int(answer_id) == answer.id:
                return 'Answer already in Answers database', 400

        new_answer = client.get(client.key(ANSWERS, int(answer_id)))
        client.put(new_answer)
        return '', 201

    if request.method == 'DELETE':
        # DELETE Answer from Question Entity
        question = client.get(client.key(QUESTIONS, int(question_id)))
        question['AnswerIDs'].remove(answer_id)
        client.put(question)

        # DELETE Answer from Answer Entity
        answer = client.get(client.key(ANSWERS, int(answer_id)))
        client.delete(answer)

        return '', 204


@view_answers.route('/answers/<answer_id>', methods=['DELETE'])
def answers_delete(answer_id):
    if request.method == 'DELETE':
        # DELETE Answer from any Questions
        query = client.query(kind=QUESTIONS)
        questions = list(query.fetch())
        for question in questions:
            if answer_id in question['AnswerIDs']:
                question['AnswerIDs'].remove(answer_id)
                client.put(question)

        # DELETE Answer from Answer Entity
        answer = client.get(client.key(ANSWERS, int(answer_id)))
        client.delete(answer)
        return '', 204


# Endpoint to GET Question Answers
@view_answers.route('/questions/<question_id>/answers', methods=['GET'])
def get_question_answers(question_id):
    if request.method == 'GET':
        question_key = client.key(QUESTIONS, int(question_id))
        question = client.get(question_key)

        question_text = question['QuestionText']
        answers = []

        for answer_id in question['AnswerIDs']:
            answer = client.get(client.key(ANSWERS, int(answer_id)))
            answers.append(answer)

        return question_text, jsonify([answer_to_dict(a) for a in answers]), 200
