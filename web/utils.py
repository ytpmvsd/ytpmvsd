import os

import ffmpeg
import shutil
from sqlalchemy import create_engine, text

ALLOWED_UPLOAD_EXTENSIONS = {"mp4"}

def add_sample_to_db(filename, stored_as, upload_date, thumbnail, uploader, source_id):
    with engine.connect() as conn:
        try:
            conn.execute(
                text(
                    "INSERT INTO sample (filename, stored_as, tags, upload_date, thumbnail_filename, uploader, source_id) VALUES (:filename, :stored_as, :tags, :upload_date, :thumbnail_filename, :uploader, :source_id)"
                ),
                {
                    "filename": filename,
                    "stored_as": stored_as,
                    "tags": [],
                    "upload_date": upload_date,
                    "thumbnail_filename": thumbnail,
                    "uploader": uploader,
                    "source_id": source_id,
                },
            )
            conn.commit()
        except Exception as e:
            print(f"Error adding sample: {e}")

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



DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
