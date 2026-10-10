import datetime
import os
import re
import pathlib
import secrets
import file_type

from flask import jsonify
from flask_babel import gettext as _
from flask_login import current_user

from config import MB_UPLOAD_LIMIT
from models import Metadata, Sample, db, Tag
from utils import add_sample_to_db, check_video, create_thumbnail, reencode_video, add_tag_to_db, update_metadata

from werkzeug.utils import secure_filename

ALLOWED_UPLOAD_EXTENSIONS=["mp4"]
ALLOWED_UPLOAD_EXTENSIONS_WITH_REENCODE=["m4v"]


def edit_sample(sample_id, filename, source_id, tags, reencode):
    sample = Sample.query.get(sample_id)
    if not sample:
        return 1

    if reencode:
        reencode_video(sample.stored_as)
        update_metadata(sample.id)

    sample.filename = filename
    sample.source_id = source_id

    sample.tags = [] # clear tags in the case of re-edits
    for sample_tag in tags:
        tag = Tag.query.filter_by(name=sample_tag).first()
        if tag is None:
            if sample_tag == '':
                continue
            add_tag_to_db(sample_tag, 5)
            tag = Tag.query.filter_by(name=sample_tag).first()
        if tag not in sample.tags:
            sample.tags.append(tag)
    
    try:
        db.session.commit()
    except Exception as e:
        print(e)
        db.session.rollback()
        return 1

    return 0

def upload(file):
    force_reencode = False
    if file:
        original_filename = secure_filename(file.filename)

        filename = os.path.splitext(original_filename)[0]
        if len(filename) >= 100:
            raise Exception(_("upload_error_filename_too_long"))

        random_id = secrets.token_hex(10)
        
        stored_as = f"{filename}_{random_id}.mp4"
        stored_as = re.sub(r"[^\w\s.-]", "", stored_as)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S%f")[:-3]

        # Make sure the directories actually exist
        pathlib.Path("static/media/samps").mkdir(parents=True,exist_ok=True)
        pathlib.Path("static/media/thumbs").mkdir(parents=True,exist_ok=True)

        upload_path = os.path.join("static/media/samps", stored_as)
        file.save(upload_path)

        ext = file_type.filetype_from_file(upload_path).extensions()
        invalid_file = True
        for allowed_ext in ALLOWED_UPLOAD_EXTENSIONS:
            if allowed_ext in ext:
                invalid_file = False
                break
        
        # if we hit an invalid file, go through the extensions that can be submitted but with a reencode
        if invalid_file:
            for allowed_ext in ALLOWED_UPLOAD_EXTENSIONS_WITH_REENCODE:
                if allowed_ext in ext:
                    invalid_file = False
                    force_reencode = True
                    break


        if not check_video(upload_path):
            invalid_file = True
            
        if invalid_file:
            os.remove(upload_path)
            raise Exception(_("upload_error_invalid_file"))
        
        if os.path.getsize(upload_path) > MB_UPLOAD_LIMIT * 1000 * 1000:
            os.remove(upload_path)
            raise Exception(_("upload_error_file_too_large"))

        thumbnail_filename = f"{timestamp}.png"
        create_thumbnail(upload_path, f"static/media/thumbs/{thumbnail_filename}")

        is_public = current_user.is_uploader
        
        try:
            sample_id = add_sample_to_db(
                original_filename,
                stored_as,
                datetime.datetime.now(datetime.UTC),
                thumbnail_filename,
                current_user.id,
                None,
                is_public
            )
            update_metadata(sample_id)
        except Exception as e:
            print(e)
            if os.path.exists(upload_path):
                os.remove(upload_path)
            thumb_path = f"static/media/thumbs/{thumbnail_filename}"
            if os.path.exists(thumb_path):
                os.remove(thumb_path)
            raise Exception(_("upload_error_database", error=e))

    else:
        raise Exception(_("upload_error_no_file"))

    return sample_id, original_filename, timestamp, stored_as, force_reencode

def delete_sample(sample_id):
    # (note: we do not need err_sanitize here as these errors should only be visible to admins)
    try:
        sample = Sample.query.get(sample_id)
    except Exception as ex:
        return jsonify({"success": False, "message": _("delete_error_failed", error=str(ex))})
    if sample:
        try:
            metadata = Metadata.query.get(sample_id)
        except Exception as ex:
            return jsonify({"success": False, "message": _("delete_error_failed", error=str(ex))})
        if sample:
            try:
                db.session.delete(metadata)
            except Exception as ex:
                return jsonify({"success": False, "message": _("delete_error_metadata_failed", error=str(ex))})
            try:
                db.session.delete(sample)
            except Exception as ex:
                return jsonify({"success": False, "message": _("delete_error_failed", error=str(ex))})
            try: 
                db.session.commit()
            except Exception as ex:
                db.session.rollback()
                return jsonify({"success": False, "message": _("delete_error_commit_failed", error=str(ex))})
                
            warnings = []
            try:
                os.remove(os.path.join("static/media/thumbs", sample.thumbnail_filename))
            except FileNotFoundError:
                warnings.append(_("delete_warning_thumbnail_missing"))
            try:
                os.remove(os.path.join("static/media/samps", sample.stored_as))
            except FileNotFoundError:
                warnings.append(_("delete_warning_file_missing"))

        return jsonify({"success": True, "message": _("delete_success"), "warnings": warnings})
    
    return jsonify({"success": False, "message": _("delete_error_not_found")})

