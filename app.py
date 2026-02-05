from flask import (
    Flask,
    render_template,
    jsonify,
    request,
    session,
    redirect,
    url_for,
)
from flask_login import (
    LoginManager,
    current_user,
)
from flask_migrate import Migrate
from flask_moment import Moment
from flask_babel import Babel, _

from config import VERSION
from models import db, User
from mail import mail
import datetime

from blueprints.main_routes import main_bp
from blueprints.wiki_routes import wiki_bp
from blueprints.api_routes import api_bp

app = Flask(__name__)
app.config.from_pyfile("config.py")
app.jinja_env.add_extension("jinja2.ext.loopcontrols")
version = VERSION

db.init_app(app)
mail.init_app(app)
migrate = Migrate(app, db)
moment = Moment(app)


def get_locale():
    user_locale = session.get("locale")
    if user_locale:
        return user_locale
    return request.accept_languages.best_match(["en", "ja", "fr"])


babel = Babel(app, locale_selector=get_locale)

@app.route("/set_locale/<locale>")
def set_locale(locale):
    if locale in ["en", "es", "ja", "fr"]:
        session["locale"] = locale
    return redirect(request.referrer or url_for("main.home_page"))


app.register_blueprint(main_bp)
app.register_blueprint(wiki_bp)
app.register_blueprint(api_bp)

login_manager = LoginManager(app)
login_manager.login_view = (
    "main.login"
)


@app.context_processor
def inject_global_data():
    return {
        "current_user": current_user,
        "date": datetime.datetime.now(datetime.UTC),
    }


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html", title="YTPMV Sample Database")


@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"error": "One or more of your sample(s) exceeded the file limit. Max supported filesize is 10MB per file."}), 400


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


if __name__ == "__main__":
    app.run(debug=True, host="192.168.7.2", port=5000)

with app.app_context():
    db.create_all()
    db.session.commit()

    users = User.query.all()
