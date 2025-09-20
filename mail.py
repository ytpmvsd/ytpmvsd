from flask_mail import Message, Mail
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from config import SECRET_KEY
import secrets

mail = Mail()

s = URLSafeTimedSerializer(SECRET_KEY)
email_hash = secrets.token_hex(4096)

def generate_token(email):
    return s.dumps(email, salt=email_hash)

def confirm_token(token, expiration=86400):
    try:
        return s.loads(token, salt=email_hash, max_age=expiration)
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
            <div style="font-family: 'Noto Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;">
            <table>
                <tr align="center"><td style="padding: 0.5em;"><center><img src="https://ytpmvsd.com/static/img/logo.png"/ width="50%"></center></td></tr>
                <tr align="center"><td style="padding: 0.5em;"><h3>Please confirm your email address to use YTPMVSD.</h3></td></tr>
                <tr align="center"><td style="padding: 0.5em;"><a style="display: block; background: #324ca8; padding: 1em; color: white; font-weight: bold; border-radius: 5px; width: 5em; text-decoration: none;" href="{verify_url}">Verify</a></td></tr>
                <tr align="center"><td>This link expires in 24 hours.</td></tr>
                <tr align="center"><td>Do not click this link if you didn't sign up for this site.</td></tr>
            </table>
            """
        )
        mail.send(msg)
    except Exception as e:
        print(e)