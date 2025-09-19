from flask_mail import Message, Mail
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from env import FLASK_SECRET_KEY

mail = Mail()

s = URLSafeTimedSerializer(FLASK_SECRET_KEY)

def generate_token(email):
    return s.dumps(email, salt="email-confirm")

def confirm_token(token, expiration=86400):
    try:
        return s.loads(token, salt="email-confirm", max_age=expiration)
    except SignatureExpired:
        return False
    except BadSignature:
        return False

def send_verification_email(to, verify_url):
    try:
        msg = Message(
            subject="Verify your account at YTPMVSD",
            recipients=[to],
            sender="account@ytpmvsd.com",
            html=f"""
            <p>Click the link below to verify your email:</p>
            <p><a href="{verify_url}">{verify_url}</a></p>
            """
        )
        mail.send(msg)
    except Exception as e:
        print(e)