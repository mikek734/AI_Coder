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
        payload = verify_jwt(request)
        if not payload:
            return f'''
                <script>
                    window.location.href = '/';
                </script>
            ''', 201
        user_query = client.query(kind=USERS)
        all_users = []
        users = list(user_query.fetch())
        all_users.extend(users)
        # print(f'all users: {all_users}')
        for user in all_users:
            # print(f'This is a user: {user}')
            if user["sub"] == payload["sub"]:
                quiz_query = client.query(kind=QUIZZES)
                quizzes = list(quiz_query.fetch())
                results = []
                for quiz in quizzes:
                    if user["sub"] == quiz["UserID"]:
                        results.append(quiz)

                return render_template("quizzes.j2", quizzes=results), 200
        return redirect("/"), 201


# ROUTE WHERE CANDIDATE TAKES THE QUIZ
@view_quizzes.route('/quizzes/<quiz_id>', methods=['POST', 'GET'])
def quizzes_get_quiz(quiz_id):
    # This is what the candidate does when hitting 'Submit Quiz'
    if request.method == 'POST':

        candidate_name, percent_score, raw_score, time_taken = submit_quiz(quiz_id)

        quiz_key = client.key(QUIZZES, int(quiz_id))
        if not client.get(quiz_key):
            return jsonify({'error': 'Invalid quiz ID'}), 400

        new_score = datastore.entity.Entity(key=client.key(SCORES))
        new_score.update(
            {
                'CandidateName': candidate_name,
                'PercentScore': percent_score,
                'RawScore': raw_score,
                'TimeTaken': time_taken,
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

        return f'''
            <script>
                window.location.href = '/quizzes/{quiz_id}/scores/{new_score.id}';
            </script>
        ''', 201

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

        payload = verify_jwt(request)
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

        # Validate the quiz name
        for key, value in data.items():
            if 'QuizName' in key:
                try:
                    validate_quiz_data(data)
                except ValueError as e:
                    return jsonify({'error': str(e)}), 400

        # Validate the user
        user_key = client.key(USERS, payload["sub"])
        user = client.get(user_key)

        if not user:
            return jsonify({'error': 'User does not exist. Please create one.'}), 400

        quiz = create_quiz(data, payload)
        client.put(quiz)

        result = questions_get_post(request, questions, quiz_id=quiz.id)
        if isinstance(result, tuple) and result[1] != 201:
            return result

        return redirect('/quizzes'), 201

    elif request.method == 'GET':
        return render_template('create_quiz.j2'), 200


# PROTECTED ROUTE
# DELETE, PUT, or PATCH a specific quiz
@view_quizzes.route('/quizzes/<quiz_id>/edit', methods=['DELETE', 'PATCH', 'GET'])
def quizzes_delete_put_patch(quiz_id):
    if request.method == 'PATCH':
        data = request.form
        questions = []
        print('data:', data)

        # Process delete flags first
        for key, value in data.items():
            if '[delete]' in key and value == 'true':
                question_id_str = key.split('[')[1].split(']')[0]
                question_id = int(question_id_str)
                delete_question_from_quiz(quiz_id, question_id)

        # Determine the number of questions based on the keys in the data
        num_questions = len([key for key in data.keys() if '[QuestionText]' in key])

        # Update the Quiz entity with the new NumberOfQuestions value
        quiz_key = client.key(QUIZZES, int(quiz_id))
        quiz = client.get(quiz_key)
        quiz['NumberOfQuestions'] = num_questions  # Update the attribute
        client.put(quiz)  # Save the changes

        for i in range(1, num_questions + 1):
            question_text = data.get(f'questions[{i}][QuestionText]')
            answers = [data.get(f'questions[{i}][answers][{j}]') for j in range(4)]  # Assuming 4 answers
            correct_answer = data.get(f'questions[{i}][correctAnswer]')
            question_id = data.get(f'questions[{i}][id]')  # Extract the ID

            question = {
                'QuestionText': question_text,
                'AnswerChoices': answers,
                'CorrectAnswer': correct_answer,
                'QuizID': int(quiz_id)
            }
            questions.append(question)

            if question_id is None:
                # This is a new question, add it
                add_question_to_quiz(quiz_id, question)
            else:
                # If the delete field is absent or set to false, update the question
                update_question_in_quiz(int(question_id), question)

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
        questions = []

        # Get the Questions and add them to the viewing list
        for question_id in quiz['QuestionIDs']:
            question = client.get(client.key(QUESTIONS, int(question_id)))
            questions.append(question)

        return render_template("quizzes_edit.j2", quiz=quiz, quiz_name=quiz_name, questions=questions), 200


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
    question = client.get(client.key(QUESTIONS, question_id))
    client.delete(question)


def update_question_in_quiz(question_id, question_data):
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


def update_quiz(quiz, data, payload):
    quiz['QuizName'] = data['QuizName']
    quiz['NumberOfQuestions'] = data['NumberOfQuestions']
    quiz['LastModified'] = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
    quiz['UserID'] = payload["sub"]

    return quiz


def create_quiz(data, payload):
    quiz = datastore.entity.Entity(key=client.key(QUIZZES))
    quiz.update(
        {
            'QuizName': data['QuizName'],
            'NumberOfQuestions': data['NumberOfQuestions'],
            'LastModified': datetime.now().strftime("%m/%d/%Y %H:%M:%S"),
            'UserID': payload["sub"],
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


def submit_quiz(quiz_id):
    quiz = get_quiz(quiz_id)
    question_bank = {}

    # First, get the questions from the question bank
    for question_id in quiz['QuestionIDs']:
        question = client.get(client.key(QUESTIONS, int(question_id)))
        question_bank[question_id] = {
            'id': question_id,
            'question': question['QuestionText'],
            'answers': question['AnswerChoices'],
            'correct_answer': question['CorrectAnswer']
        }

    data = request.form

    result = calculate_score(question_bank, data)

    candidate_name = data['CandidateName']
    score = result['score']
    total = result['total']
    percent = (score / total) * 100
    percent = "{:.2f}".format(percent)
    percent_score = f' { percent } % '
    raw_score = f' { score } of { total } '
    time_taken = data['timeTaken']

    return candidate_name, percent_score, raw_score, time_taken


def calculate_score(questions, selected_answers):
    score = 0
    answers_lhs = []
    answers_rhs = []
    for question in questions:
        answers_lhs.append(questions[question]['correct_answer'])
    for key, value in selected_answers.items():
        if 'CandidateName' in key or 'timeTaken' in key:
            continue
        answers_rhs.append(int(value))

    for i in range(len(questions)):
        if answers_lhs[i] == answers_rhs[i]:
            score += 1

    result = {
        'score': score,
        'total': len(questions)
    }

    return result
