from flask import Blueprint, jsonify, request
import api
import math
from config import SAMPLES_PER_PAGE

api_bp = Blueprint("api", __name__, url_prefix="/api")

def sample_jsonify(sample):
    if sample is None:
        return {}
    uploader_name = api.get_user_info(sample.uploader).username
    source_id = -1
    if sample.source is not None:
        source_id = sample.source.id
    return {"id":sample.id,"filename":sample.filename,"tags":sample.tags,"upload_date":sample.upload_date,"thumbnail_filename":sample.thumbnail_filename,"uploader":uploader_name,"likes":len(sample.likes), "source": source_id, "stored_as": sample.stored_as}

@api_bp.route("/recent_samples")
def api_recent_samples():
    res = api.get_recent_samples()
    samples = list(map(lambda f: sample_jsonify(f), res))
    return jsonify(samples)

@api_bp.route("/top_samples")
def api_top_samples():
    res = api.get_top_samples()
    samples = list(map(lambda f: sample_jsonify(f), res))
    return jsonify(samples)

@api_bp.route("/samples/<string:sort>/<int:index>")
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

@api_bp.route("/samples/<string:sort>")
def api_samples_base(sort):
    return api_samples(sort, 1)

@api_bp.route("/metadata/<int:sample_id>")
def api_metadata(sample_id):
    return api.get_metadata(sample_id)

@api_bp.route("/search/<string:query>")
def api_search_sources(query):
    res = api.search_sources(query)
    return jsonify({"id":res.id,"name":res.name,"samples":res.samples})

@api_bp.route("/source/<int:source_id>")
def api_source_info(source_id):
    res = api.get_source_info(source_id)
    samples = list(map(lambda f: f.id, res.samples))
    return jsonify({"id":res.id,"name":res.name,"samples":samples})

@api_bp.route("/sample/<int:sample_id>")
def api_sample_info(sample_id):
    if sample_id is None:
        return jsonify({})
    res = sample_jsonify(api.get_sample_info(sample_id))
    return jsonify(res)

@api_bp.route("/samples_len")
def api_samples_len():
    return jsonify({"len": int(math.ceil(api.get_samples_len() / SAMPLES_PER_PAGE))})

@api_bp.route("/search_samples")
def api_search_samples():
    query = request.args.get("q", "")
    samples = api.search_samples(query)

    return jsonify([{"id": s.id, "name": s.filename} for s in samples])

@api_bp.route("/search_sources")
def search_sources():
    query = request.args.get("q", "")
    sources = api.search_sources(query)

    return jsonify([{"id": s.id, "name": s.name} for s in sources])
