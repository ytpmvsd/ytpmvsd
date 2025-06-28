from enum import Enum
import os

import ffmpeg
from models import Source, User, db, Sample, likes_table
from sqlalchemy import func
SAMPLES_PER_PAGE = int(os.getenv("SAMPLES_PER_PAGE"))

class SampleSort(Enum):
    LATEST = 0
    OLDEST = 1
    LIKED = 2
    NONE = 3

def get_recent_samples():
    return Sample.query.order_by(Sample.upload_date.desc()).limit(8).all()

def get_top_samples():
    return (
        db.session.query(Sample)
        .outerjoin(likes_table, Sample.id == likes_table.c.sample_id)
        .group_by(Sample.id)
        .order_by(func.count(likes_table.c.user_id).desc())
        .limit(8)
        .all()
    )

def get_samples(sort: SampleSort, index: int):
    index -= 1
    if sort is None:
        return Sample.query.limit(SAMPLES_PER_PAGE).offset(SAMPLES_PER_PAGE * index)
    match sort:
        case SampleSort.LATEST:
            return Sample.query.order_by(Sample.upload_date.desc()).limit(SAMPLES_PER_PAGE).offset(SAMPLES_PER_PAGE * index)
        case SampleSort.OLDEST:
            return Sample.query.order_by(Sample.upload_date.asc()).limit(SAMPLES_PER_PAGE).offset(SAMPLES_PER_PAGE * index)
        case SampleSort.LIKED:
            return (
            db.session.query(Sample)
                .outerjoin(likes_table, Sample.id == likes_table.c.sample_id)
                .group_by(Sample.id)
                .order_by(func.count(likes_table.c.user_id).desc())
                .limit(SAMPLES_PER_PAGE).offset(SAMPLES_PER_PAGE * index)
            )
        case _:
            return Sample.query.limit(SAMPLES_PER_PAGE)
        
def get_metadata(sample_id):
    sample = Sample.query.get(sample_id)
    file = os.path.join("static/media/samps", sample.stored_as)

    probe = ffmpeg.probe(file)

    return probe

def get_samples_len():
    return Sample.query.count()
        
def search_sources(query):
    return Source.query.filter(Source.name.ilike(f"%{query}%")).limit(10).all()

def get_source_info(source_id):
    return Source.query.get(source_id)

def get_sample_info(sample_id):
    return Sample.query.get(sample_id)

def get_user_info(uploader):
    return User.query.get(uploader)



