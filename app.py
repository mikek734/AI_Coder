from flask import Flask, render_template

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/account')
def view_account():
    return render_template('view_account.html')


@app.route('/account/edit')
def edit_account():
    return render_template('edit_account.html')


@app.route('/account/delete')
def delete_account():
    return render_template('delete_account.html')


@app.route('/quizzes')
def view_all_quizzes():
    return render_template('view_all_quizzes.html')


@app.route('/quiz/edit')
def edit_quiz():
    return render_template('edit_quiz.html')


@app.route('/scores')
def view_all_scores():
    return render_template('view_all_scores.html')


@app.route('/score/<int:score_id>')
def view_score(score_id):
    return render_template('score.html', score_id=score_id)


if __name__ == "__main__":
    app.run(host='127.0.0.1', port=8080, debug=True)
