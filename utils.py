import os

import ffmpeg
import shutil
from sqlalchemy import create_engine, text

from env import DATABASE_URL, ALLOWED_UPLOAD_EXTENSIONS
from models import Sample

def add_sample_to_db(filename, stored_as, upload_date, thumbnail, uploader, source_id):
    with engine.connect() as conn:
        try:
            sample = conn.execute(
                text(
                    "INSERT INTO sample (filename, stored_as, tags, upload_date, thumbnail_filename, uploader, source_id) VALUES (:filename, :stored_as, :tags, :upload_date, :thumbnail_filename, :uploader, :source_id) RETURNING id"
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
            try:
                sample_id = sample.scalar()
                metadata = get_metadata(sample_id)
                for stream in metadata['streams']:
                    if stream['codec_type'] == "video":
                        video_stream = stream
                        break
                framerate = video_stream['r_frame_rate'].split('/')
                framerate = int(framerate[0]) / int(framerate[1])
                conn.execute(
                    text(
                        "INSERT INTO metadata (sample_id, filesize, width, height, aspect_ratio, framerate, codec) VALUES (:sample_id, :filesize, :width, :height, :aspect_ratio, :framerate, :codec)"
                    ),
                    {
                        "sample_id": sample_id,
                        "filesize": metadata['format']['size'],
                        "width": video_stream['width'],
                        "height": video_stream['height'],
                        "aspect_ratio": video_stream['display_aspect_ratio'],
                        "framerate": framerate,
                        "codec": video_stream['codec_name'],
                    },
                )
                conn.commit()
            except Exception as e:
                conn.execute(
                    text("DELETE FROM sample WHERE id = :sample_id"),
                    {"sample_id": sample_id},
                )
                conn.commit()
                raise ValueError(f"Error adding metadata: {e}")
        except Exception as e:
            print(f"Error adding sample: {e}")
            raise


def update_metadata(sample_id):
    with engine.connect() as conn:
        try:
            sample = conn.execute(
                text(
                    "SELECT id from sample WHERE id = :sample_id"
                ),
                {"sample_id": sample_id},
            )
            sample_id = sample.scalar()
            metadata = get_metadata(sample_id)
            for stream in metadata['streams']:
                if stream['codec_type'] == "video":
                    video_stream = stream
                    break
            framerate = video_stream['r_frame_rate'].split('/')
            framerate = int(framerate[0]) / int(framerate[1])
            conn.execute(
                text(
                    "INSERT INTO metadata (sample_id, filesize, width, height, aspect_ratio, framerate, codec) VALUES (:sample_id, :filesize, :width, :height, :aspect_ratio, :framerate, :codec)"
                ),
                {
                    "sample_id": sample_id,
                    "filesize": metadata['format']['size'],
                    "width": video_stream['width'],
                    "height": video_stream['height'],
                    "aspect_ratio": video_stream['display_aspect_ratio'],
                    "framerate": framerate,
                    "codec": video_stream['codec_name'],
                },
            )
            conn.commit()
        except Exception as e:
            print(f"Error adding sample: {e}")
            raise ValueError(f"Error adding metadata: {e}")


def create_thumbnail(video_path, thumbnail_path):
    shutil.copy(video_path, os.getcwd())

    try:
        if not os.path.exists(os.path.join(os.getcwd(), os.path.basename(video_path))):
            raise FileNotFoundError(
                f"Video file not found: {os.path.join(os.getcwd(), os.path.basename(video_path))}"
            )

        (
            ffmpeg.input(os.path.join(os.getcwd(), os.path.basename(video_path)), ss=0)
            .filter("pad", width="max(iw,ih*(16/9))", height="ow/(16/9)", x="(ow-iw)/2", y="(oh-ih)/2")
            .filter("scale", -1, 480)
            .output(thumbnail_path, vframes=1)
            .run(capture_stdout=True, capture_stderr=True)
        )

        os.remove(os.path.join(os.getcwd(), os.path.basename(video_path)))

        print(f"Thumbnail saved at {thumbnail_path}")

    except Exception as e:
        print('stdout:', e.stdout.decode('utf8'))
        print('stderr:', e.stderr.decode('utf8'))
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

# sanitize the given string of anything with a path seperator, as it could reveal information about the filesystem.
def err_sanitize(err):
    strerr = str(err)
    parts = strerr.split(" ")
    for part in parts:
        if os.path.sep in part:
            strerr = strerr.replace(part, "<stripped>")
    return strerr

def get_metadata(sample_id):
    sample = Sample.query.get(sample_id)
    file = os.path.join("static/media/samps", sample.stored_as)

    probe = ffmpeg.probe(file)

    return probe

engine = create_engine(DATABASE_URL)
