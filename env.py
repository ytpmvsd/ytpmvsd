import os, dotenv

dotenv.load_dotenv()
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
SAMPLES_PER_PAGE = int(os.getenv("SAMPLES_PER_PAGE"))
VERSION = os.getenv("VERSION")
MB_UPLOAD_LIMIT = os.getenv("MB_UPLOAD_LIMIT")