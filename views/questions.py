from google.cloud import datastore
from flask import request, jsonify, redirect, render_template
from flask import Blueprint

client = datastore.Client()
USERS = "users"
QUIZZES = "quizzes"
SCORES = "scores"
QUESTIONS = "questions"
ANSWERS = "answers"

view_questions = Blueprint('view_questions', __name__)


# INTERNAL METHOD
# GET or POST a Question
@view_questions.route('/questions', methods=['GET', 'POST'])
def questions_get_post(request, questions):
    if request.method == 'POST':
        data = request.get_json()

        if not isinstance(data['QuestionText'], str):
            return jsonify({'error': 'Question text must be a string'}), 400

        if not isinstance(data['QuizID'], int):
            return jsonify({'error': 'Quiz ID must be an integer'}), 400

        if not isinstance(data['AnswerChoices'], list):
            return jsonify({'error': 'Quiz ID must be an integer'}), 400

        if not isinstance(data['CorrectAnswer'], int):
            return jsonify({'error': 'Correct Answer must be an integer'}), 400

        quiz_key = client.key(QUIZZES, int(data['QuizID']))
        if not client.get(quiz_key):
            return jsonify({'error': 'Invalid quiz ID'}), 400

        new_question = datastore.entity.Entity(key=client.key(QUESTIONS))
        new_question.update(
            {
                'QuestionText': data['QuestionText'],
                'QuizID': data['QuizID'],
                'AnswerChoices': data['AnswerChoices'],
                'CorrectAnswer': data['CorrectAnswer']
            }
        )

        client.put(new_question)

        # Update Quiz Entity to maintain referential integrity
        quiz = client.get(quiz_key)
        quiz['QuestionIDs'].append(new_question.id)
        client.put(quiz)

        return jsonify(question_to_dict(new_question)), 201

    elif request.method == 'GET':
        query = client.query(kind=QUESTIONS)
        questions = list(query.fetch())
        return jsonify([question_to_dict(q) for q in questions]), 200


def question_to_dict(question):
    return {
        'QuestionText': question['QuestionText'],
        'QuizID': question['QuizID'],
        'AnswerChoices': question['AnswerChoices'],
        'CorrectAnswer': question['CorrectAnswer']
    }


# INTERNAL METHOD
# GET all Quiz Questions
@view_questions.route('/quizzes/<quiz_id>/questions', methods=['GET'])
def get_quiz_questions(quiz_id):

    if request.method == 'GET':

        quiz = client.get(client.key(QUIZZES, int(quiz_id)))

        quiz_name = quiz['QuizName']
        questions = []

        # First, call all the Questions and add them to the viewing list
        for question_id in quiz['QuestionIDs']:
            question = client.get(client.key(QUESTIONS, int(question_id)))
            questions.append(question)

        return render_template("questions.j2", quiz=quiz, quiz_name=quiz_name, questions=questions), 200


@view_questions.route('/questions/<question_id>', methods=['DELETE'])
def questions_delete(question_id):
    if request.method == 'DELETE':
        # DELETE Question from any Quizzes
        query = client.query(kind=QUIZZES)
        quizzes = list(query.fetch())
        for quiz in quizzes:
            if question_id in quiz['QuestionIDs']:
                quiz['QuestionIDs'].remove(question_id)
                client.put(quiz)

        # DELETE Question from Question Entity
        question = client.get(client.key(QUESTIONS, int(question_id)))
        client.delete(question)
        return '', 204
