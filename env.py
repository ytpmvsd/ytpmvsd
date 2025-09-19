import os, dotenv

dotenv.load_dotenv()
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
SAMPLES_PER_PAGE = int(os.getenv("SAMPLES_PER_PAGE"))
VERSION = os.getenv("VERSION")
MB_UPLOAD_LIMIT = int(os.getenv("MB_UPLOAD_LIMIT")) 
USER_APPROVAL = os.getenv("USER_APPROVAL")

MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.example.com")
MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
MAIL_USE_TLS = True  # Use TLS for most SMTP providers
MAIL_USE_SSL = False  # Use SSL only if required (never enable both)
MAIL_USERNAME = os.getenv("MAIL_USERNAME", "your_email@example.com")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "your_email_password")
