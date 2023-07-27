from google.cloud import datastore
from flask import request, jsonify, redirect, render_template
from flask import Blueprint

client = datastore.Client()
USERS = "users"
QUIZZES = "quizzes"
SCORES = "scores"
QUESTIONS = "questions"
ANSWERS = "answers"

view_quizzes = Blueprint('view_quizzes', __name__)


# View all Quizzes made by User
@view_quizzes.route('/quizzes', methods=['GET'])
def quizzes_get():

    if request.method == 'GET':

        query = client.query(kind=QUIZZES)
        quizzes = list(query.fetch())

        return render_template("quizzes.j2", quizzes=quizzes), 200


# View one Quiz during quiz-taking
@view_quizzes.route('/quizzes/<quiz_id>', methods=['POST', 'GET'])
def quizzes_get_quiz(quiz_id):

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

        # TODO
        # Calculate quiz scores when the candidate hits Submit Quiz
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

        # TODO
        # Where to redirect candidate after they hit 'Submit Quiz' ????
        return redirect('/'), 201

    elif request.method == 'GET':

        quiz = client.get(client.key(QUIZZES, int(quiz_id)))

        quiz_name = quiz['QuizName']
        questions = []
        answers = []

        # First, call all the Questions and add them to the viewing list
        for question_id in quiz['QuestionIDs']:
            question = client.get(client.key(QUESTIONS, question_id))
            questions.append(question)

        # Second, call the Answer Choices of each Question and add them to the results
        for question in questions:
            choices = []
            for answer_id in question['AnswerIDs']:
                answer = client.get(client.key(ANSWERS, answer_id))
                choices.append(answer['AnswerText'])
            answers.append(choices)

        return render_template("questions.j2", quiz_name=quiz_name, questions=questions, answers=answers), 200


# POST a new blank Quiz if the Auth header contains a valid JWT
@view_quizzes.route('/quizzes/add', methods=['POST', 'GET'])
def quizzes_post():

    if request.method == 'POST':

        # TODO
        # Verify JWT First
        data = request.get_json()

        try:
            validate_quiz_data(data)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400

        user_key = client.key(USERS, int(data['UserID']))
        user = client.get(user_key)

        if not user:
            return jsonify({'error': 'Invalid user ID'}), 400

        quiz = create_quiz(data)

        client.put(quiz)

        return redirect('/quizzes'), 201

    elif request.method == 'GET':

        return render_template('quizzes_add.j2'), 200


# DELETE, PUT, or PATCH a specific quiz
@view_quizzes.route('/quizzes/<quiz_id>/edit', methods=['DELETE', 'PATCH', 'PUT', 'GET'])
def quizzes_delete_put_patch(quiz_id):

    if request.method == 'PATCH':
        data = request.get_json()

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

        # Delete Quiz from any Users
        query = client.query(kind=USERS)
        users = list(query.fetch())
        for user in users:
            if quiz_id in user['QuizIDs']:
                user['QuizIDs'].remove(quiz_id)
                client.put(user)

        # Delete all Questions and Answers associated with Quiz
        quiz = client.get(client.key(QUIZZES, int(quiz_id)))
        query = client.query(kind=QUESTIONS)
        questions = list(query.fetch())
        for question in questions:
            if question.id in quiz['QuestionIDs']:
                for answer_id in question['AnswerIDs']:
                    answer = client.get(client.key(ANSWERS, answer_id))
                    client.delete(answer)
                client.delete(question)

        # Delete Quiz from Quiz Entity
        client.delete(quiz)

        return redirect('/quizzes'), 204

    elif request.method == 'GET':

        # TODO
        quiz = client.get(client.key(QUIZZES, int(quiz_id)))
        questions = []
        answers = []

        return render_template('quizzes_edit.j2', quiz=quiz, questions=questions, answers=answers)


def validate_quiz_data(data):
    if not isinstance(data['QuizName'], str):
        raise ValueError('Quiz name must be a string')

    if not isinstance(data['NumberOfQuestions'], int):
        raise ValueError('Number of questions must be an integer')

    if not isinstance(data['LastModified'], str):
        raise ValueError('LastModified must be a string')

    if not isinstance(data['UserID'], int):
        raise ValueError('UserID must be an integer')


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
            'LastModified': data['LastModified'],
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


# Endpoint specifically for adding/deleting a quiz from a user, if desired
@view_quizzes.route('/users/<user_id>/quizzes/<quiz_id>', methods=['DELETE', 'POST'])
def add_delete_quiz_from_user(user_id, quiz_id):
    if request.method == 'POST':

        # POST Quiz to User Entity
        user_key = client.key(USERS, int(user_id))
        user = client.get(user_key)

        if quiz_id not in user['QuizIDs']:
            user['QuizIDs'].append(quiz_id)
            client.put(user)
        elif quiz_id in user['QuizIDs']:
            return 'Quiz already exists in the User quizzes', 400

        # POST Quiz to Quiz Entity
        quiz = client.get(client.key(QUIZZES, quiz_id))
        if quiz_id == quiz.id:
            return 'Quiz already exists inside Quizzes', 400

        client.put(quiz)
        return redirect('/users'), 201

    if request.method == 'DELETE':
        # DELETE Quiz from User Entity
        user = client.get(client.key(USERS, int(user_id)))
        user['QuizIDs'].remove(quiz_id)
        client.put(user)

        # DELETE Quiz from Quiz Entity
        quiz = client.get(client.key(QUIZZES, int(quiz_id)))
        client.delete(quiz)

        return redirect('/users'), 204
