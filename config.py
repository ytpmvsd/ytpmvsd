import toml

settings = toml.load("config.toml")

USER_APPROVAL = settings["user_approval"]
VERSION = settings["version"]
SECRET_KEY = settings["flask_secret_key"]
SQLALCHEMY_DATABASE_URI = settings["database_url"]
MB_UPLOAD_LIMIT = settings["mb_upload_limit"]
MAX_CONTENT_LENGTH = MB_UPLOAD_LIMIT * 10 * 1000 * 1000
SAMPLES_PER_PAGE = settings["samples_per_page"]
ALLOWED_UPLOAD_EXTENSIONS = settings["allowed_upload_extensions"]
SQLALCHEMY_TRACK_MODIFICATIONS = False

MAIL_SERVER = settings["mail_server"] or "smtp.example.com"
MAIL_PORT = int(settings["mail_port"] or 587)
MAIL_USE_TLS = settings["mail_use_tls"] or True  # Use TLS for most SMTP providers
MAIL_USE_SSL = settings["mail_use_ssl"] or False  # Use SSL only if required (never enable both)
MAIL_USERNAME = settings["MAIL_USERNAME"] or "your_email@example.com"
MAIL_PASSWORD = settings["MAIL_PASSWORD"] or "hackme"
