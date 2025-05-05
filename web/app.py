import datetime
import os
import re
import shutil
import uuid

import dotenv
import markdown
import ffmpeg
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    jsonify,
    flash,
    session,
    abort,
)
from flask_login import (
    LoginManager,
    login_user,
    login_required,
    logout_user,
    current_user,
)
from flask_migrate import Migrate
from flask_moment import Moment
from sqlalchemy import func
from werkzeug.utils import secure_filename

from database_functions import add_sample_to_db
from models import db, Sample, User, likes_table, Source

dotenv.load_dotenv()

MB_UPLOAD_LIMIT = 10

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY")
app.config["MAX_CONTENT_LENGTH"] = MB_UPLOAD_LIMIT * 10 * 1000 * 1000
app.jinja_env.add_extension("jinja2.ext.loopcontrols")
version = os.getenv("VERSION")

db.init_app(app)
migrate = Migrate(app, db)
moment = Moment(app)

login_manager = LoginManager(app)
login_manager.login_view = (
    "login"
)


def create_thumbnail(video_path, thumbnail_path):
    shutil.copy(video_path, os.getcwd())

    try:
        if not os.path.exists(os.path.join(os.getcwd(), os.path.basename(video_path))):
            raise FileNotFoundError(
                f"Video file not found: {os.path.join(os.getcwd(), os.path.basename(video_path))}"
            )

        (
            ffmpeg.input(os.path.join(os.getcwd(), os.path.basename(video_path)), ss=0)
            .filter("scale", -1, 480)
            .output(thumbnail_path, vframes=1)
            .run(capture_stdout=True, capture_stderr=True)
        )

        os.remove(os.path.join(os.getcwd(), os.path.basename(video_path)))

        print(f"Thumbnail saved at {thumbnail_path}")

    except Exception as e:
        print(f"An error occurred: {e}")


def reencode_video(filename):
    temp = "temp_" + filename

    filename = os.path.join("static/media/samps", filename)
    temp = os.path.join("static/media/samps", temp)

    probe = ffmpeg.probe(filename)
    video_stream = next(
        (stream for stream in probe["streams"] if stream["codec_type"] == "video"), None
    )

    width = int(video_stream.get("width"))
    height = int(video_stream.get("height"))

    sar = video_stream.get("sample_aspect_ratio")
    if not sar or sar == "0:1":
        sar = f"{width}:{height}"
    else:
        sar = sar

    try:
        (
            ffmpeg.input(filename)
            .output(
                temp,
                format="mp4",
                vcodec="libx264",
                acodec="aac",
                strict="experimental",
                preset="medium",
                vf=f"scale={width}:{height},setsar={sar},setdar={width}/{height}",
            )
            .run(overwrite_output=True)
        )
        os.replace(temp, filename)
        return True

    except ffmpeg.Error as e:
        print(e.stderr)
        return False


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/login/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login_name = request.form["login"].lower()
        password = request.form["password"]

        user = User.query.filter(func.lower(User.email) == login_name).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("home_page"))

        user = User.query.filter(func.lower(User.username) == login_name).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("home_page"))
        flash("Login or password incorrect.", "error")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout/")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home_page"))


@app.route("/register/", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        if User.query.filter(User.username.ilike(username)).first():
            flash("Username is already in use.", "error")
            return redirect(url_for("register"))

        if User.query.filter(User.email.ilike(email)).first():
            flash("Email is already in use.", "error")
            return redirect(url_for("register"))

        user = User(username=username, email=email)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()
        flash("Successfully registered.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.context_processor
def inject_user():
    return {"current_user": current_user}


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html", title="YTPMV Sample Database")


@app.errorhandler(413)
def request_entity_too_large(error):
    flash("File too large. Max supported filesize is 10MB.", "error")
    return redirect(url_for("upload"))


@app.route("/")
def home_page():
    recent_samples = Sample.query.order_by(Sample.upload_date.desc()).limit(8).all()
    top_samples = (
        db.session.query(Sample)
        .outerjoin(likes_table, Sample.id == likes_table.c.sample_id)
        .group_by(Sample.id)
        .order_by(func.count(likes_table.c.user_id).desc())
        .limit(8)
        .all()
    )

    filepath = os.path.join("static/wiki/pages/changelogs", f"{version}.md")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            changelog_md = f.read()
        changelog = markdown.markdown(changelog_md)
    except FileNotFoundError:
        print(f"Changelog {filepath} not found.")
        changelog = None

    return render_template(
        "home.html",
        title="YTPMV Sample Database",
        top_samples=top_samples,
        recent_samples=recent_samples,
        date=datetime.datetime.now(datetime.UTC),
        changelog=changelog if changelog else None,
        version=version,
    )


@app.route("/samples/")
def all_samples():
    sort = request.args.get("sort", "liked")

    if sort == "latest":
        samples = Sample.query.order_by(Sample.upload_date.desc()).all()
    elif sort == "oldest":
        samples = Sample.query.order_by(Sample.upload_date.asc()).all()
    elif sort == "liked":
        samples = (
            db.session.query(Sample)
            .outerjoin(likes_table, Sample.id == likes_table.c.sample_id)
            .group_by(Sample.id)
            .order_by(func.count(likes_table.c.user_id).desc())
            .all()
        )
    else:
        samples = Sample.query.all()

    return render_template(
        "samples.html",
        title="Samples - YTPMV Sample Database",
        samples=samples,
        date=datetime.datetime.now(datetime.UTC),
    )


ALLOWED_UPLOAD_EXTENSIONS = {"mp4"}


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_UPLOAD_EXTENSIONS
    )


def check_video(upload_path):
    try:
        ffmpeg.probe(upload_path)
        return True
    except ffmpeg.Error:
        return False


@app.route("/upload/", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        if "file" not in request.files:
            return redirect(request.url)

        files = request.files.getlist("file")

        if len(files) == 0 or files[0].filename == "":
            return redirect(request.url)

        if len(files) > 10:
            flash(
                "Currently, you can only upload up to 10 files at once. Please select fewer files.",
                "error",
            )
            return redirect(url_for("upload"))

        sample_ids = []

        for file in files:
            if file and allowed_file(file.filename):
                original_filename = secure_filename(file.filename)

                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S%f")[:-3]
                random_id = uuid.uuid4().hex[:6]
                stored_as = f"{os.path.splitext(original_filename)[0]}_{timestamp}_{random_id}.mp4"

                stored_as = re.sub(r"[^\w\s.-]", "", stored_as)

                # current_time = int(time.time() * 100)
                # filename = secure_filename(file.filename + str(current_time))
                upload_path = os.path.join("static/media/samps", stored_as)
                file.save(upload_path)

                if not check_video(upload_path):
                    flash(
                        "There is an error one of your files. Please make sure it is a valid .mp4 file.",
                        "error",
                    )
                    os.remove(upload_path)
                    return redirect(url_for("upload"))

                if os.path.getsize(upload_path) > MB_UPLOAD_LIMIT * 1000 * 1000:
                    os.remove(upload_path)
                    abort(413)

                create_thumbnail(upload_path, f"static/media/thumbs/{timestamp}.png")

                sample_id = str(uuid.uuid4())
                sample_ids.append(sample_id)

                session[f"uploaded_sample_id_{sample_id}"] = sample_id
                session[f"filename_{sample_id}"] = original_filename
                session[f"thumbnail_{sample_id}"] = f"{timestamp}.png"
                session[f"stored_as_{sample_id}"] = stored_as

        if len(sample_ids) == 1:
            return redirect(url_for("edit_sample", sample_id=sample_ids[0]))

        return redirect(url_for("batch_edit_samples", sample_ids=",".join(sample_ids)))

    return render_template("upload.html", title="Upload - YTPMV Sample Database")


def get_metadata(sample_id):
    sample = Sample.query.get_or_404(sample_id)
    file = os.path.join("static/media/samps", sample.stored_as)

    probe = ffmpeg.probe(file)

    return probe


@app.route("/sample/<int:sample_id>/")
def sample_page(sample_id):
    sample = Sample.query.get_or_404(sample_id)
    uploader = User.query.get_or_404(sample.uploader)

    metadata = get_metadata(sample.id)

    return render_template(
        "sample.html",
        title=f"{sample.filename} - YTPMV Sample Database",
        sample=sample,
        uploader=uploader,
        metadata=metadata,
    )


@app.route("/sample/edit/<sample_id>/", methods=["GET", "POST"])
@login_required
def edit_sample(sample_id):
    uploaded_sample_id = session.get(f"uploaded_sample_id_{sample_id}")
    old_filename = session.get(f"filename_{sample_id}")
    thumbnail = session.get(f"thumbnail_{sample_id}")
    stored_as = session.get(f"stored_as_{sample_id}")

    if not uploaded_sample_id or uploaded_sample_id != sample_id:
        flash("Invalid request.", "error")
        return redirect(url_for("upload"))

    if request.method == "POST":
        filename = request.form.get("filename")
        source_id = request.form.get("source_id")
        reencode = request.form.get("reencode")

        filename = re.sub(r"[^\w\s]", "", filename)
        filename = re.sub(r"\s+", "_", filename) + ".mp4"

        # tags = request.form.get('tags', '').split(',')

        if reencode:
            reencode_video(stored_as)

        if source_id == "":
            source_id = None

        add_sample_to_db(
            filename,
            stored_as,
            datetime.datetime.now(datetime.UTC),
            str(thumbnail),
            current_user.id,
            source_id,
        )

        session.pop(f"uploaded_sample_id_{sample_id}", None)
        session.pop(f"filename_{sample_id}", None)
        session.pop(f"thumbnail_{sample_id}", None)
        session.pop(f"stored_as_{sample_id}", None)

        return redirect(url_for("home_page"))

    return render_template(
        "edit_sample.html",
        sample_id=sample_id,
        filename=old_filename,
        stored_as=stored_as,
        thumbnail=thumbnail,
        filename_no_extension=os.path.splitext(old_filename)[0],
    )


@app.route("/sample/batch-edit/<sample_ids>/", methods=["GET", "POST"])
@login_required
def batch_edit_samples(sample_ids):
    sample_ids = sample_ids.split(",")
    sample_data = []

    for sample_id in sample_ids:
        uploaded_sample_id = session.get(f"uploaded_sample_id_{sample_id}")
        filename = session.get(f"filename_{sample_id}")
        thumbnail = session.get(f"thumbnail_{sample_id}")
        stored_as = session.get(f"stored_as_{sample_id}")

        if not uploaded_sample_id or uploaded_sample_id != sample_id:
            flash("Invalid request.", "error")
            return redirect(url_for("upload"))

        sample_data.append(
            {
                "sample_id": sample_id,
                "filename": filename,
                "thumbnail": thumbnail,
                "stored_as": stored_as,
            }
        )

    if request.method == "POST":
        source_id = request.form.get("source_id")
        reencode = request.form.get("reencode")

        if source_id == "":
            source_id = None

        for sample in sample_data:
            filename = sample["filename"]
            sample_id = sample["sample_id"]
            thumbnail = sample["thumbnail"]
            stored_as = sample["stored_as"]

            if reencode:
                reencode_video(stored_as)

            add_sample_to_db(
                filename,
                stored_as,
                datetime.datetime.now(datetime.UTC),
                str(thumbnail),
                current_user.id,
                source_id,
            )

            session.pop(f"uploaded_sample_id_{sample_id}", None)
            session.pop(f"filename_{sample_id}", None)
            session.pop(f"thumbnail_{sample_id}", None)
            session.pop(f"stored_as_{sample_id}", None)

        return redirect(url_for("home_page"))

    return render_template(
        "batch_edit_samples.html",
        samples=sample_data,
    )


@app.route("/sample/like/<int:sample_id>/", methods=["POST"])
@login_required
def like_sample(sample_id):
    sample = Sample.query.get_or_404(sample_id)

    if current_user in sample.likes:
        sample.likes.remove(current_user)
        liked = False
    else:
        sample.likes.append(current_user)
        liked = True

    db.session.commit()
    return jsonify(success=True, likes=len(sample.likes), liked=liked)


@app.route("/sample/delete/<int:sample_id>/", methods=["POST"])
@login_required
def delete_sample(sample_id):
    if not current_user.is_admin:
        return jsonify({"message": "Access denied"}), 403

    sample = Sample.query.get(sample_id)
    if sample:
        os.remove(os.path.join("static/media/thumbs", sample.thumbnail_filename))
        os.remove(os.path.join("static/media/samps", sample.filename))
        db.session.delete(sample)
        db.session.commit()
        return jsonify({"message": "Sample deleted successfully."})
    return jsonify({"message": "There was an error deleting the sample."})


@app.route("/user/<int:user_id>/")
def user_page(user_id):
    user = User.query.get_or_404(user_id)
    samples = (
        Sample.query.filter_by(uploader=user_id)
        .order_by(Sample.upload_date.desc())
        .all()
    )

    return render_template(
        "user.html",
        title=f"{user.username} - YTPMV Sample Database",
        samples=samples,
        user=user,
        date=datetime.datetime.now(datetime.UTC),
    )


@app.route("/sources/")
def all_sources():
    sources = Source.query.order_by(Source.name.asc()).all()

    return render_template(
        "sources.html", title="Sources - YTPMV Sample Database", sources=sources
    )


@app.route("/source/<int:source_id>/")
def source_page(source_id):
    source = Source.query.get_or_404(source_id)
    samples = (
        Sample.query.filter_by(source=source).order_by(Sample.upload_date.desc()).all()
    )

    return render_template(
        "source.html",
        title=f"{source.name} - YTPMV Sample Database",
        samples=samples,
        source=source,
        date=datetime.datetime.now(datetime.UTC),
    )


@app.route("/search_sources/")
def search_sources():
    query = request.args.get("q", "")
    sources = Source.query.filter(Source.name.ilike(f"%{query}%")).limit(10).all()

    return jsonify([{"id": s.id, "name": s.name} for s in sources])


@app.route("/wiki/")
def wiki_main():
    return render_template("wiki/wiki_home.html")


@app.route("/wiki/<page>")
def wiki_page(page):
    filepath = os.path.join("static/wiki/pages", f"{page}.md")

    with open(filepath, "r", encoding="utf-8") as f:
        md_content = f.read()

    title = md_content.split("\n")[0][2:]

    html_content = markdown.markdown(md_content, extensions=["tables", "md_in_html"])

    return render_template(
        "wiki/wiki_page.html", content=html_content, title=title + " - YTPMVSD Wiki"
    )


if __name__ == "__main__":
    app.run(debug=True, host="192.168.7.2", port=5000)

with app.app_context():
    db.create_all()
    db.session.commit()

    users = User.query.all()