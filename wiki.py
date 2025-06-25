import os
from flask import render_template
import markdown


def wiki_main():
    return render_template("wiki/wiki_home.html")

def wiki_page(page):
    filepath = os.path.join("static/wiki/pages", f"{page}.md")

    with open(filepath, "r", encoding="utf-8") as f:
        md_content = f.read()

    title = md_content.split("\n")[0][2:]

    html_content = markdown.markdown(md_content, extensions=["tables", "md_in_html"])

    return render_template(
        "wiki/wiki_page.html", content=html_content, title=title + " - YTPMVSD Wiki"
    )
