import datetime
import os
import re
import uuid
import pathlib
import secrets

from flask import jsonify

from models import Sample, db
from utils import add_sample_to_db, allowed_file, check_video, create_thumbnail, reencode_video

from werkzeug.utils import secure_filename

from constants import MB_UPLOAD_LIMIT
    
def edit_sample(filename, stored_as, thumbnail, uploader, source_id, reencode):
    if reencode:
        reencode_video(stored_as)


    add_sample_to_db(
        filename,
        stored_as,
        datetime.datetime.now(datetime.UTC),
        str(thumbnail),
        uploader,
        source_id,
    )

def upload(file, sample_ids):
    if file and allowed_file(file.filename):
        original_filename = secure_filename(file.filename)

        filename_shortened = os.path.splitext(original_filename)[0]
        if len(filename_shortened) >= 100:
            filename_shortened = filename_shortened[:99]

        random_id = secrets.token_hex(100)
        
        stored_as = f"{filename_shortened}_{random_id}.mp4"
        stored_as = re.sub(r"[^\w\s.-]", "", stored_as)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S%f")[:-3]

        # Make sure the directories actually exist
        pathlib.Path("static/media/samps").mkdir(parents=True,exist_ok=True)
        pathlib.Path("static/media/thumbs").mkdir(parents=True,exist_ok=True)

        upload_path = os.path.join("static/media/samps", stored_as)
        file.save(upload_path)

        if not check_video(upload_path):
            os.remove(upload_path)
            raise Exception("There is an error one of your files. Please make sure it is a valid .mp4 file.")
        
        if os.path.getsize(upload_path) > MB_UPLOAD_LIMIT * 1000 * 1000:
            os.remove(upload_path)
            raise Exception("Content is too large")

        create_thumbnail(upload_path, f"static/media/thumbs/{timestamp}.png")

        sample_id = str(uuid.uuid4())
        sample_ids.append(sample_id)
    else:
        if not allowed_file(file):
            raise Exception("Disallowed file type")
        else:
            raise Exception("No file")

    return (sample_id, original_filename, timestamp, stored_as)

def delete_sample(sample_id):
    sample = Sample.query.get(sample_id)
    if sample:
        warnings = []
        try:
            os.remove(os.path.join("static/media/thumbs", sample.thumbnail_filename))
        except FileNotFoundError as _:
            warnings.append("Thumbnail file wasn't found, couldn't be deleted")
        try:
            os.remove(os.path.join("static/media/samps", sample.stored_as))
        except FileNotFoundError as _:
            warnings.append("Sample file wasn't found, couldn't be deleted")
        db.session.delete(sample)
        db.session.commit()
        return jsonify({"message": "Sample deleted successfully.", "warnings": warnings})
    return jsonify({"message": "There was an error deleting the sample."})

