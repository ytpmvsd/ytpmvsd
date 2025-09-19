import os
import re
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session,
    url_for,
    jsonify,
    flash, send_file,
)
from flask_login import (
    LoginManager,
    login_required,
    current_user,
    login_user,
    logout_user,
)
from flask_migrate import Migrate
from flask_moment import Moment
from sqlalchemy import func

from env import USER_APPROVAL, VERSION, SAMPLES_PER_PAGE
from models import db, Sample, User, Source
from utils import err_sanitize, update_metadata

import markdown
import datetime

import api
import samples
import wiki
import math

app = Flask(__name__)
app.config.from_pyfile("env.py")
app.jinja_env.add_extension("jinja2.ext.loopcontrols")
version = VERSION

db.init_app(app)
migrate = Migrate(app, db)
moment = Moment(app)

login_manager = LoginManager(app)
login_manager.login_view = (
    "login"
)


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
    recent_samples = api.get_recent_samples()
    top_samples = api.get_top_samples()

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

@app.route("/samples/<int:index>/")
def samples_list(index):
    sort = request.args.get("sort", "liked")

    if sort == "latest":
        samples = api.get_samples(api.SampleSort.LATEST, index)
    elif sort == "oldest":
        samples = api.get_samples(api.SampleSort.OLDEST, index)
    elif sort == "liked":
        samples = api.get_samples(api.SampleSort.LIKED, index)
    else:
        samples = api.get_samples(api.SampleSort.NONE, index)

    return render_template(
        "samples.html",
        title="Samples - YTPMV Sample Database",
        samples=samples,
        date=datetime.datetime.now(datetime.UTC),
        index=index,
        page_num = int(math.ceil(api.get_samples_len() / SAMPLES_PER_PAGE))
    )

@app.route("/samples/")
def samples_list_base():
    return samples_list(1)

@app.route("/sample/<int:sample_id>/")
def sample_page(sample_id):
    sample = api.get_sample_info(sample_id)

    if sample is None:
        return render_template("404.html", title="YTPMV Sample Database")

    uploader = api.get_user_info(sample.uploader)

    metadata = api.get_metadata(sample.id)
    if metadata is None:
        update_metadata(sample_id)
        metadata = api.get_metadata(sample.id)

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
    force_reencode = session.get(f"force_reencode")

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

        if source_id == "":
            source_id = None

        edit_status = samples.edit_sample(
            filename,
            stored_as,
            str(thumbnail),
            current_user.id,
            source_id,
            reencode
        )

        session.pop(f"uploaded_sample_id_{sample_id}", None)
        session.pop(f"filename_{sample_id}", None)
        session.pop(f"thumbnail_{sample_id}", None)
        session.pop(f"stored_as_{sample_id}", None)
        session.pop(f"force_reencode", None)

        if edit_status:
            flash("Failed to upload sample. Please reencode or try another video.", "error")
            return redirect(url_for("upload"))

        return redirect(url_for("home_page"))

    return render_template(
        "edit_sample.html",
        sample_id=sample_id,
        filename=old_filename,
        stored_as=stored_as,
        thumbnail=thumbnail,
        filename_no_extension=os.path.splitext(old_filename)[0],
        force_reencode=force_reencode,
    )


@app.route("/sample/batch-edit/<sample_ids>/", methods=["GET", "POST"])
@login_required
def batch_edit_samples(sample_ids):
    sample_ids = sample_ids.split(",")
    sample_data = []

    force_reencode = False

    for sample_id in sample_ids:
        uploaded_sample_id = session.get(f"uploaded_sample_id_{sample_id}")
        filename = session.get(f"filename_{sample_id}")
        thumbnail = session.get(f"thumbnail_{sample_id}")
        stored_as = session.get(f"stored_as_{sample_id}")
        if not force_reencode:
            force_reencode = session.get(f"force_reencode")

        if not uploaded_sample_id or uploaded_sample_id != sample_id:
            flash("Invalid request.", "error")
            return redirect(url_for("upload"))

        sample_data.append(
            {
                "sample_id": sample_id,
                "filename": filename,
                "thumbnail": thumbnail,
                "stored_as": stored_as,
                "force_reencode": force_reencode,
            }
        )

    if request.method == "POST":
        source_id = request.form.get("source_id")
        reencode = request.form.get("reencode")
        if session.get(f"force_reencode") == "True":
            reencode = True

        if source_id == "":
            source_id = None

        for sample in sample_data:
            filename = sample["filename"]
            stored_as = sample["stored_as"]
            thumbnail = sample["thumbnail"]
            sample_id = sample["sample_id"]

            edit_status = samples.edit_sample(filename, stored_as, thumbnail, current_user.id, source_id, reencode)

            session.pop(f"uploaded_sample_id_{sample_id}", None)
            session.pop(f"filename_{sample_id}", None)
            session.pop(f"thumbnail_{sample_id}", None)
            session.pop(f"stored_as_{sample_id}", None)
            session.pop(f"force_reencode", None)

            if edit_status:
                flash("Failed to upload one or more sample(s). Please reencode or try another video.", "error")
                return redirect(url_for("upload"))

        return redirect(url_for("home_page"))

    return render_template(
        "batch_edit_samples.html",
        samples=sample_data,
        force_reencode=force_reencode,
    )


# TODO: This could be added as an api call, but first an oauth system needs to be implemented so that we don't rely on flask.
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
    sample = Sample.query.get(sample_id)
    if not current_user or (not current_user.is_admin and sample.uploader != current_user.id):
        return jsonify({"message": "Access denied"}), 403

    return samples.delete_sample(sample_id)

@app.route("/sample/<int:sample_id>/download/")
def download_sample(sample_id):
    sample = Sample.query.get_or_404(sample_id)
    file_path = os.path.join("static/media/samps", sample.stored_as)
    return send_file(file_path, as_attachment=True, download_name=sample.filename)

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
    source = api.get_source_info(source_id)
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
    sources = api.search_sources(query)

    return jsonify([{"id": s.id, "name": s.name} for s in sources])


@app.route("/upload/", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        sample_ids = []

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

        for file in files:
            try:
                (sample_id, original_filename, timestamp, stored_as, force_reencode) = samples.upload(file)
                sample_ids.append(sample_id)
                session[f"uploaded_sample_id_{sample_id}"] = sample_id
                session[f"filename_{sample_id}"] = original_filename
                session[f"thumbnail_{sample_id}"] = f"{timestamp}.png"
                session[f"stored_as_{sample_id}"] = stored_as
                session[f"force_reencode"] = force_reencode

            except Exception as ex:
                flash(err_sanitize(ex), "error")
                return redirect(url_for("upload"))

        if len(sample_ids) == 1:
            return redirect(url_for("edit_sample", sample_id=sample_ids[0]))

        return redirect(url_for("batch_edit_samples", sample_ids=",".join(sample_ids)))

    return render_template("upload.html", title="Upload - YTPMV Sample Database", user_approval=USER_APPROVAL.lower() == "true")

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

@app.route("/logout/", methods=["GET", "POST"])
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
        
        if len(username) >= 64:
            flash("Username cannot be over 64 characters", "error")
            return redirect(url_for("register"))

        user = User(username=username, email=email)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()
        flash("Successfully registered.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/wiki/")
def wiki_main():
    return wiki.wiki_main()

@app.route("/wiki/<page>")
def wiki_page(page):
    return wiki.wiki_page(page)

def sample_jsonify(sample):
    if sample is None:
        return {}
    uploader_name = api.get_user_info(sample.uploader).username
    source_id = -1
    if sample.source is not None:
        source_id = sample.source.id
    return {"id":sample.id,"filename":sample.filename,"tags":sample.tags,"upload_date":sample.upload_date,"thumbnail_filename":sample.thumbnail_filename,"uploader":uploader_name,"likes":len(sample.likes), "source": source_id, "stored_as": sample.stored_as}

@app.route("/api/recent_samples")
def api_recent_samples():
    res = api.get_recent_samples()
    samples = list(map(lambda f: sample_jsonify(f), res))
    return jsonify(samples)

@app.route("/api/top_samples")
def api_top_samples():
    res = api.get_top_samples()
    samples = list(map(lambda f: sample_jsonify(f), res))
    return jsonify(samples)

@app.route("/api/samples/<string:sort>/<int:index>")
def api_samples(sort, index):
    if sort == "latest":
        res = api.get_samples(api.SampleSort.LATEST, index)
    elif sort == "oldest":
        res = api.get_samples(api.SampleSort.OLDEST, index)
    elif sort == "liked":
        res = api.get_samples(api.SampleSort.LIKED, index)
    else:
        res = api.get_samples(api.SampleSort.NONE, index)
    return jsonify(list(map(lambda f: sample_jsonify(f),res)))

@app.route("/api/samples/<string:sort>")
def api_samples_base(sort):
    return api_samples(sort, 1)

@app.route("/api/metadata/<int:sample_id>")
def api_metadata(sample_id):
    return api.get_metadata(sample_id)

@app.route("/api/search/<string:query>")
def api_search_sources(query):
    res = api.search_sources(query)
    return jsonify({"id":res.id,"name":res.name,"samples":res.samples})

@app.route("/api/source/<int:source_id>")
def api_source_info(source_id):
    res = api.get_source_info(source_id)
    samples = list(map(lambda f: f.id, res.samples))
    return jsonify({"id":res.id,"name":res.name,"samples":samples})

@app.route("/api/sample/<int:sample_id>")
def api_sample_info(sample_id):
    if sample_id is None:
        return jsonify({})
    res = sample_jsonify(api.get_sample_info(sample_id))
    return jsonify(res)

@app.route("/api/samples_len")
def api_samples_len():
    return jsonify({"len": int(math.ceil(api.get_samples_len() / SAMPLES_PER_PAGE))})

if __name__ == "__main__":
    app.run(debug=True, host="192.168.7.2", port=5000)

with app.app_context():
    db.create_all()
    db.session.commit()

    users = User.query.all()
