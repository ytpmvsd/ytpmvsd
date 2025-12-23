import wiki
from flask import Blueprint

wiki_bp = Blueprint("wiki", __name__, url_prefix="/wiki")

@wiki_bp.route("/")
def wiki_main():
    return wiki.wiki_main()

@wiki_bp.route("/<page>")
def wiki_page(page):
    return wiki.wiki_page(page)
