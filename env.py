import toml

settings = toml.load("config.toml")

USER_APPROVAL = settings["user_approval"]
VERSION = settings["version"]
SECRET_KEY = settings["flask_secret_key"]
SQLALCHEMY_DATABASE_URI = settings["database_url"]
MB_UPLOAD_LIMIT = settings["mb_upload_limit"]
MAX_CONTENT_LENGTH = MB_UPLOAD_LIMIT * 10
SAMPLES_PER_PAGE = settings["samples_per_page"]
ALLOWED_UPLOAD_EXTENSIONS = settings["allowed_upload_extensions"]
SQLALCHEMY_TRACK_MODIFICATIONS = False