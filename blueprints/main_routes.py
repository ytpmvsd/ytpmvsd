import datetime
import os
import re
import math
import markdown
from flask import Blueprint, render_template, request, redirect, session, url_for, jsonify, flash, send_file
from flask_login import login_required, current_user, login_user, logout_user
from sqlalchemy import func

from config import REQUIRE_USER_APPROVAL, VERSION, SAMPLES_PER_PAGE
from models import db, Sample, User, Source
from utils import update_metadata
from mail import generate_token, send_verification_email, confirm_token
import api
import samples

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def home_page():
    recent_samples = api.get_recent_samples()
    top_samples = api.get_top_samples()

    filepath = os.path.join("static/wiki/pages/changelogs", f"{VERSION}.md")

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
        changelog=changelog if changelog else None,
        version=VERSION,
    )

@main_bp.route("/samples/<int:index>/")
def samples_list(index):
    sort = request.args.get("sort", "liked")

    if sort == "latest":
        res_samples = api.get_samples(api.SampleSort.LATEST, index)
    elif sort == "oldest":
        res_samples = api.get_samples(api.SampleSort.OLDEST, index)
    elif sort == "liked":
        res_samples = api.get_samples(api.SampleSort.LIKED, index)
    else:
        res_samples = api.get_samples(api.SampleSort.NONE, index)

    return render_template(
        "samples.html",
        title="Samples - YTPMV Sample Database",
        samples=res_samples,
        index=index,
        page_num = int(math.ceil(api.get_samples_len() / SAMPLES_PER_PAGE))
    )

@main_bp.route("/samples/")
def samples_list_base():
    return samples_list(1)

@main_bp.route("/sample/<int:sample_id>/")
def sample_page(sample_id):
    sample = api.get_sample_info(sample_id)

    if sample is None:
        return render_template("404.html", title="YTPMV Sample Database")

    if not sample.is_public:
        if not current_user.is_authenticated or (not current_user.is_admin and current_user.id != sample.uploader):
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

@main_bp.route("/sample/edit/<sample_id>/", methods=["GET", "POST"])
@login_required
def edit_sample(sample_id):
    sample = Sample.query.get(sample_id)

    # defaults
    tags = ""
    source_id = None
    source_name = ""
    force_reencode = False

    uploaded_sample_id = session.get(f"uploaded_sample_id_{sample_id}")
    if uploaded_sample_id:
        uploaded_sample_id = str(uploaded_sample_id)
    
    if uploaded_sample_id and uploaded_sample_id == sample_id:
        is_initial_upload = True
        old_filename = session.get(f"filename_{sample_id}")
        thumbnail = session.get(f"thumbnail_{sample_id}")
        stored_as = session.get(f"stored_as_{sample_id}")
        force_reencode = session.get(f"force_reencode")

    elif sample:
        is_initial_upload = False
        if not (current_user.is_admin or current_user.id == sample.uploader):
            flash("You do not have permission to edit this sample.", "error")
            return redirect(url_for("main.sample_page", sample_id=sample_id))
            
        old_filename = sample.filename
        thumbnail = sample.thumbnail_filename
        stored_as = sample.stored_as
        tags = " ".join([tag.name for tag in sample.tags])
        source_id = sample.source_id
        source_name = sample.source.name if sample.source else ""

    else:
        flash("Sample not found.", "error")
        return redirect(url_for("main.upload"))

    if request.method == "POST":
        filename = request.form.get("filename")
        source_id = request.form.get("source_id")
        tags = request.form.get('tags', '').split(' ')
        reencode = request.form.get("reencode") if is_initial_upload else False

        filename = re.sub(r"[^\w\s]", "", filename)
        filename = re.sub(r"\s+", "_", filename) + ".mp4"

        if source_id == "":
            source_id = None

        edit_status = samples.edit_sample(
            sample_id,
            filename,
            source_id,
            tags,
            reencode
        )

        session.pop(f"uploaded_sample_id_{sample_id}", None)
        session.pop(f"filename_{sample_id}", None)
        session.pop(f"thumbnail_{sample_id}", None)
        session.pop(f"stored_as_{sample_id}", None)
        session.pop(f"force_reencode", None)

        if edit_status:
            flash("Failed to edit sample.", "error")
            if uploaded_sample_id:
                return redirect(url_for("main.upload"))
            else:
                return redirect(url_for("main.sample_page", sample_id=sample_id))

        return redirect(url_for("main.sample_page", sample_id=sample_id))

    return render_template(
        "edit_sample.html",
        sample_id=sample_id,
        filename=old_filename,
        stored_as=stored_as,
        thumbnail=thumbnail,
        filename_no_extension=os.path.splitext(old_filename)[0],
        force_reencode=force_reencode,

        # relevant for post-upload edits only
        is_initial_upload=is_initial_upload,
        tags=tags,
        source_id=source_id,
        source_name=source_name
    )

@main_bp.route("/sample/batch-edit/<sample_ids>/", methods=["GET", "POST"])
@login_required
def batch_edit_samples(sample_ids):
    sample_ids_list = sample_ids.split(",")
    sample_data = []

    force_reencode = False

    for sample_id in sample_ids_list:
        uploaded_sample_id = str(session.get(f"uploaded_sample_id_{sample_id}"))
        filename = session.get(f"filename_{sample_id}")
        thumbnail = session.get(f"thumbnail_{sample_id}")
        stored_as = session.get(f"stored_as_{sample_id}")
        if not force_reencode:
            force_reencode = session.get(f"force_reencode")

        if not uploaded_sample_id:
            flash("Sample ID empty.", "error")
            return redirect(url_for("main.upload"))

        if uploaded_sample_id != sample_id:
            flash("Sample ID doesn't match.", "error")
            return redirect(url_for("main.upload"))

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

        for sample_item in sample_data:
            filename = sample_item["filename"]
            sample_id = sample_item["sample_id"]

            edit_status = samples.edit_sample(sample_id, filename, source_id, [], reencode)

            session.pop(f"uploaded_sample_id_{sample_id}", None)
            session.pop(f"filename_{sample_id}", None)
            session.pop(f"thumbnail_{sample_id}", None)
            session.pop(f"stored_as_{sample_id}", None)
            session.pop(f"force_reencode", None)

            if edit_status:
                flash("Failed to upload one or more sample(s). Please reencode or try another video.", "error")
                return redirect(url_for("main.upload"))

        return redirect(url_for("main.user_page", user_id=current_user.id))

    return render_template(
        "batch_edit_samples.html",
        samples=sample_data,
        force_reencode=force_reencode,
    )

# TODO: This could be added as an api call, but first an oauth system needs to be implemented so that we don't rely on flask.
@main_bp.route("/sample/like/<int:sample_id>/", methods=["POST"])
@login_required
def like_sample(sample_id):
    sample = Sample.query.get_or_404(sample_id)

    if not current_user.is_verified:
        return jsonify(success=False, message="Please verify your account to like samples.")

    if current_user in sample.likes:
        sample.likes.remove(current_user)
        liked = False
    else:
        sample.likes.append(current_user)
        liked = True

    db.session.commit()
    return jsonify(success=True, likes=len(sample.likes), liked=liked)

@main_bp.route("/sample/delete/<int:sample_id>/", methods=["POST"])
@login_required
def delete_sample(sample_id):
    sample = Sample.query.get(sample_id)
    if not current_user or (not current_user.is_admin and sample.uploader != current_user.id):
        return jsonify({"message": "Access denied"}), 403

    return samples.delete_sample(sample_id)

@main_bp.route("/sample/<int:sample_id>/download/")
def download_sample(sample_id):
    sample = Sample.query.get_or_404(sample_id)
    if not sample.is_public:
        if not current_user.is_authenticated or (not current_user.is_admin and current_user.id != sample.uploader):
            return render_template("404.html", title="YTPMV Sample Database"), 404
    file_path = os.path.join("static/media/samps", sample.stored_as)
    return send_file(file_path, as_attachment=True, download_name=sample.filename)

@main_bp.route("/user/<int:user_id>/")
def user_page(user_id):
    user = User.query.get_or_404(user_id)
    res_samples = api.get_user_samples(
        user_id,
        viewer_id=current_user.id if current_user.is_authenticated else None,
        is_admin=current_user.is_authenticated and current_user.is_admin
    )

    samples = []
    private_samples = []
    for sample in res_samples:
        if not sample.is_public:
            private_samples.append(sample)
        else:
            samples.append(sample)

    return render_template(
        "user.html",
        title=f"{user.username} - YTPMV Sample Database",
        samples=samples,
        samples_under_review=private_samples,
        user=user,
    )

@main_bp.route("/sources/")
def all_sources():
    sources = Source.query.order_by(Source.name.asc()).all()

    return render_template(
        "sources.html", title="Sources - YTPMV Sample Database", sources=sources
    )

@main_bp.route("/source/<int:source_id>/")
def source_page(source_id):
    source = api.get_source_info(source_id)
    res_samples = (
        Sample.query.filter_by(source=source, is_public=True).order_by(Sample.upload_date.desc()).all()
    )

    return render_template(
        "source.html",
        title=f"{source.name} - YTPMV Sample Database",
        samples=res_samples,
        source=source,
    )

@main_bp.route("/search")
def search_results():
    query = request.args.get("q", "")

    results = api.search_samples(query)

    return render_template(
        "search.html",
        title="YTPMV Sample Database",
        samples=results,
    )

@main_bp.route("/tags/")
def tags_list():
    tags = api.get_tags()
    categories = api.get_tag_categories()

    grouped_tags = {category.id: [] for category in categories}

    for tag in tags:
        grouped_tags[tag.category_id].append(tag)

    return render_template(
        "tags.html",
        title="Tags - YTPMV Sample Database",
        categories=categories,
        tags=grouped_tags,
    )

@main_bp.route("/upload/", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        sample_ids = []

        if "file" not in request.files:
            return jsonify({"error": "Bad request"}), 400

        files = request.files.getlist("file")

        if len(files) == 0 or files[0].filename == "":
            return jsonify({"error": "No files selected"}), 400

        if len(files) > 10:
            return jsonify({"error": "Too many files"}), 400

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
                return jsonify({"error": str(ex)}), 400

        return jsonify({"sample_id": sample_ids[0]})

    return render_template("upload.html", title="Upload - YTPMV Sample Database", require_user_approval=REQUIRE_USER_APPROVAL)

@main_bp.route("/login/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login_name = request.form["login"].lower()
        password = request.form["password"]

        user = User.query.filter(func.lower(User.email) == login_name).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("main.home_page"))

        user = User.query.filter(func.lower(User.username) == login_name).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("main.home_page"))
        flash("Login or password incorrect.", "error")
        return redirect(url_for("main.login"))

    return render_template("login.html")

@main_bp.route("/logout/", methods=["GET", "POST"])
def logout():
    logout_user()
    return redirect(url_for("main.home_page"))

@main_bp.route("/register/", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        if User.query.filter(User.username.ilike(username)).first():
            flash("Username is already in use.", "error")
            return redirect(url_for("main.register"))

        if User.query.filter(User.email.ilike(email)).first():
            flash("Email is already in use.", "error")
            return redirect(url_for("main.register"))
        
        if len(username) >= 64:
            flash("Username cannot be over 64 characters", "error")
            return redirect(url_for("main.register"))

        user = User(username=username, email=email, join_date=datetime.datetime.now(datetime.UTC))
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        token = generate_token(email)
        verify_url = url_for("main.verify", token=token, _external=True)
        send_verification_email(email, verify_url)

        flash("Successfully registered. Please check your email to verify your account.", "success")
        return redirect(url_for("main.login"))

    return render_template("register.html")

@main_bp.route("/verify/<token>", methods=["GET", "POST"])
def verify(token):
    msg = "Click below to confirm your email."
    email = confirm_token(token)
    on_confirm_screen = True
    if not email:
        msg = "Invalid or expired verification link."
        on_confirm_screen = False
    elif request.method == "POST":
        user = User.query.filter_by(email=email).first()
        if user and not user.is_verified:
            user.is_verified = True
            db.session.commit()
            msg = "Your account is now verified."
            on_confirm_screen = False
        else:
            # no message saying your account is already verified, in case somehow
            # the link shows up in search results.
            return redirect(url_for("main.home_page"))
    return render_template("email/verify.html",
        msg=msg,
        on_confirm_screen=on_confirm_screen
    )
