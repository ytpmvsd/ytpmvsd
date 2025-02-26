import datetime
import os
import time

import dotenv
import ffmpeg
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate
from flask_moment import Moment
from sqlalchemy import func
from werkzeug.utils import secure_filename

import database_functions
from models import db, Sample, User

dotenv.load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')

db.init_app(app)
migrate = Migrate(app, db)
moment = Moment(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'  # Redirect users to 'login' page if not authenticated


def create_thumbnail(video_path, thumbnail_path):
    try:
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        (
            ffmpeg
            .input(video_path, ss=0)
            .filter('scale', -1, 480)
            .output(thumbnail_path, vframes=1)
            .run(capture_stdout=True, capture_stderr=True)
        )

        print(f"Thumbnail saved at {thumbnail_path}")

    except Exception as e:
        print(f"An error occurred: {e}")


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_name = request.form['login'].lower()
        password = request.form['password']

        user = User.query.filter(func.lower(User.email) == login_name).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('home_page'))

        user = User.query.filter(func.lower(User.username) == login_name).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('home_page'))

        return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home_page'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            return redirect(url_for('login'))

        if User.query.filter_by(username=email).first():
            return redirect(url_for('login'))

        user = User(username = username, email = email)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template('register.html')


@app.context_processor
def inject_user():
    return {'current_user': current_user}


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html', title='YTPMV Sample Database')


@app.route('/')
def home_page():
    recent_samples = Sample.query.order_by(Sample.upload_date.desc()).limit(8).all()
    top_samples = Sample.query.order_by(Sample.likes.desc()).limit(8).all()
    return render_template('home.html', title='YTPMV Sample Database', top_samples=top_samples,
                           recent_samples=recent_samples, date=datetime.datetime.now(datetime.UTC))

@app.route('/samples')
def all_samples():
    samples = Sample.query.all()
    return render_template('samples.html', title='YTPMV Sample Database', samples=samples, date=datetime.datetime.now(datetime.UTC))


ALLOWED_UPLOAD_EXTENSIONS = {'mp4'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_UPLOAD_EXTENSIONS


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)

        file = request.files['file']

        if file.filename == '':
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            upload_path = os.path.join('static/media/samps', filename)
            file.save(upload_path)
            current_time = int(time.time() * 100)
            create_thumbnail(upload_path, f"static/media/thumbs/{current_time}.png")

            database_functions.add_sample_to_db(filename, datetime.datetime.now(datetime.UTC),
                                                str(current_time) + '.png', current_user.id)
            return redirect(url_for('home_page'))

    return render_template('upload.html', title='YTPMV Sample Database')


@app.route('/sample/<int:sample_id>')
def sample_page(sample_id):
    sample = Sample.query.get_or_404(sample_id)
    uploader = User.query.get_or_404(sample.uploader)

    return render_template('sample.html', title=f"{sample.filename}", sample=sample, uploader=uploader)

@app.route('/sample/like/<int:sample_id>', methods=['POST'])
@login_required
def like_sample(sample_id):
    sample = Sample.query.get(sample_id)
    if sample:
        sample.likes += 1
        db.session.commit()
        return jsonify(success=True, likes=Sample.query.get(sample_id).likes)
    return jsonify(success=False)

if __name__ == '__main__':
    app.run(debug=True, host='192.168.7.2', port=5000)
