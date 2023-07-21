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

view_questions = Blueprint('view_questions', __name__)


@view_questions.route('/questions', methods=['GET', 'POST'])
def questions_get_post():
    if request.method == 'POST':
        data = request.get_json()

        if not isinstance(data['QuestionText'], str):
            return jsonify({'error': 'Question text must be a string'}), 400

        if not isinstance(data['QuizID'], int):
            return jsonify({'error': 'Quiz ID must be an integer'}), 400

        quiz_key = client.key(QUIZZES, data['QuizID'])
        if not client.get(quiz_key):
            return jsonify({'error': 'Invalid quiz ID'}), 400

        new_question = datastore.entity.Entity(key=client.key(QUESTIONS))
        new_question.update(
            {
                'QuestionText': data['QuestionText'],
                'QuizID': data['QuizID'],
                'answer_ids': [

                ]
            }
        )

        # Update Quiz Entity to maintain referential integrity
        quiz = client.get(quiz_key)
        quiz['question_ids'].append(new_question.id)
        client.put(quiz)

        client.put(new_question)

        return jsonify(question_to_dict(new_question)), 201

    elif request.method == 'GET':
        query = client.query(kind=QUESTIONS)
        questions = list(query.fetch())
        return jsonify([question_to_dict(q) for q in questions]), 200


def question_to_dict(question):
    return {
        'QuestionID': question.id,
        'QuestionText': question['QuestionText'],
        'QuizID': question['QuizID'],
        'answer_ids': question['answer_ids']
    }


# Endpoint specifically for adding/deleting a question to/from a quiz, if desired
@view_questions.route('/quizzes/<quiz_id>/questions/<question_id>', methods=['DELETE', 'POST'])
def add_delete_question_from_quiz(quiz_id, question_id):

    if request.method == 'POST':

        # POST Question to Quiz Entity
        quiz_key = client.key(QUIZZES, quiz_id)
        quiz = client.get(quiz_key)

        if question_id not in quiz['question_ids']:
            quiz['question_ids'].append(question_id)
            client.put(quiz)

        # POST Question to Question Entity
        query = client.query(kind=QUESTIONS)
        questions = list(query.fetch())
        for question in questions:
            if question_id == question.id:
                return 'Question already in Questions database', 400

        new_question = client.get(client.key(QUESTIONS, question_id))
        client.put(new_question)
        return '', 201

    if request.method == 'DELETE':

        # DELETE Question from Quiz Entity
        quiz = client.get(client.key(QUIZZES, quiz_id))
        quiz['question_ids'].remove(question_id)
        client.put(quiz)

        # DELETE Question from Question Entity
        question = client.get(client.key(QUESTIONS, question_id))
        client.delete(question)

        return '', 204


@view_questions.route('/questions/<question_id>', methods=['DELETE'])
def questions_delete(question_id):
    if request.method == 'DELETE':
        # DELETE Question from any Quizzes
        query = client.query(kind=QUIZZES)
        quizzes = list(query.fetch())
        for quiz in quizzes:
            if question_id in quiz['question_ids']:
                quiz['question_ids'].remove(question_id)
                client.put(quiz)

        # DELETE Question from Question Entity
        question = client.get(client.key(QUESTIONS, question_id))
        client.delete(question)
        return '', 204


# Endpoint to GET Quiz Questions
@view_questions.route('/quizzes/<quiz_id>/questions', methods=['GET'])
def get_quiz_questions(quiz_id):
    if request.method == 'GET':
      quiz_key = client.key('Quiz', int(quiz_id))
      quiz = client.get(quiz_key)

      quiz_name = quiz['QuizName']
      questions = []

      for question_id in quiz['question_ids']:
        question = client.get(client.key('Question', question_id))
        questions.append(question)

      return quiz_name, jsonify([question_to_dict(q) for q in questions]), 200