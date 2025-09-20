import datetime
import os
import re
import uuid
import pathlib
import secrets
import file_type

from flask import jsonify

from config import MB_UPLOAD_LIMIT
from models import Metadata, Sample, db
from utils import add_sample_to_db, check_video, create_thumbnail, reencode_video

from werkzeug.utils import secure_filename

ALLOWED_UPLOAD_EXTENSIONS=["mp4"]
ALLOWED_UPLOAD_EXTENSIONS_WITH_REENCODE=["m4v"]


def edit_sample(filename, stored_as, thumbnail, uploader, source_id, reencode):
    if reencode:
        reencode_video(stored_as)

    try:
        add_sample_to_db(
            filename,
            stored_as,
            datetime.datetime.now(datetime.UTC),
            str(thumbnail),
            uploader,
            source_id,
        )
    except Exception as e:
        print(e)
        return 1

    return 0

def upload(file):
    force_reencode = False
    if file:
        original_filename = secure_filename(file.filename)

        filename = os.path.splitext(original_filename)[0]
        if len(filename) >= 100:
            raise Exception("Filename must not exceed 100 bytes")

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
            raise Exception("There is an error one of your files. Please make sure it is a valid .mp4 file.")
        
        if os.path.getsize(upload_path) > MB_UPLOAD_LIMIT * 1000 * 1000:
            os.remove(upload_path)
            raise Exception("Content is too large")

        create_thumbnail(upload_path, f"static/media/thumbs/{timestamp}.png")

        sample_id = str(uuid.uuid4())
    else:
        raise Exception("No file")

    return sample_id, original_filename, timestamp, stored_as, force_reencode

def delete_sample(sample_id):
    # (note: we do not need err_sanitize here as these errors should only be visible to admins)
    try:
        sample = Sample.query.get(sample_id)
    except Exception as ex:
        return jsonify({"success": False, "message": "Sample could not be deleted: "+str(ex)})
    if sample:
        try:
            metadata = Metadata.query.get(sample_id)
        except Exception as ex:
            return jsonify({"success": False, "message": "Sample could not be deleted: "+str(ex)})
        if sample:
            try:
                db.session.delete(metadata)
            except Exception as ex:
                return jsonify({"success": False, "message": "Sample metadata could not be deleted: "+str(ex)})
            try:
                db.session.delete(sample)
            except Exception as ex:
                return jsonify({"success": False, "message": "Sample could not be deleted: "+str(ex)})
            try: 
                db.session.commit()
            except Exception as ex:
                return jsonify({"success": False, "message": "Sample deletion could not be committed: "+str(ex)})
                
            warnings = []
            try:
                os.remove(os.path.join("static/media/thumbs", sample.thumbnail_filename))
            except FileNotFoundError as _:
                warnings.append("Thumbnail file wasn't found, couldn't be deleted")
            try:
                os.remove(os.path.join("static/media/samps", sample.stored_as))
            except FileNotFoundError as _:
                warnings.append("Sample file wasn't found, couldn't be deleted")

        return jsonify({"success": False, "message": "Sample deleted successfully.", "warnings": warnings})
    
    return jsonify({"success": False, "message": "Tried to delete a sample that doesn't exist."})

