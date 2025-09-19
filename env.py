import toml

settings = toml.load("config.toml")

USER_APPROVAL = settings["user_approval"]
VERSION = settings["version"]
FLASK_SECRET_KEY = settings["flask_secret_key"]
DATABASE_URL = settings["database_url"]
MB_UPLOAD_LIMIT = settings["mb_upload_limit"]
SAMPLES_PER_PAGE = settings["samples_per_page"]
ALLOWED_UPLOAD_EXTENSIONS = settings["allowed_upload_extensions"]