from flask_mail import Message, Mail
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from config import SECRET_KEY
import secrets
import string
import time

mail = Mail()

s = URLSafeTimedSerializer(SECRET_KEY)
email_hash = secrets.token_hex(4096)

email_matches = {}

def generate_id(email):
    secure_str = ''.join((secrets.choice(string.ascii_letters) for i in range(6)))
    epoch_time = int(time.time())
    email_matches[secure_str] = (email, epoch_time)
    verifier = s.dumps(email, salt=email_hash)
    print((secure_str, verifier))
    return (secure_str, verifier)

def decode_email(verifier, expiration=86400):
    try:
        return s.loads(verifier, salt=email_hash, max_age=expiration)
    except SignatureExpired:
        print("signature expired")
        return False
    except BadSignature:
        print("bad signature")
        return False

def confirm_token(token, expiration=86400000):
    if not token in email_matches:
        return False
    id = email_matches[token]
    expr_time = int(time.time()) + expiration
    if id[1] > expr_time:
        return False
    del email_matches[token]
    return id[0]

def send_verification_email(to, verify_url, token):
    print(token, verify_url)
    try:
        msg = Message(
            subject="Verify your account at YTPMVSD",
            recipients=[to],
            sender="account@ytpmvsd.com",
            html=f"""
            <div style="font-family: 'Noto Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;">
            <table>
                <tr align="center"><td style="padding: 0.5em;"><center><img src="https://ytpmvsd.com/static/img/logo.png"/ width="50%"></center></td></tr>
                <tr align="center"><td><h3 style="margin: 0">Please confirm your email address to use YTPMVSD</h3></td></tr>
                <tr align="center"><td><p style="margin: 0">by entering the following code in the <a href="{verify_url}">verification page</a></p></td></tr>
                <tr align="center"><td style="padding: 0.5em;"><p style="display: block; background: #324ca8; padding: 0.5em; color: white; font-weight: bold; border-radius: 5px; width: 5em; text-decoration: none; font-size: 2em">{token}</p></td></tr>
                <tr align="center"><td>This link expires in 24 hours.</td></tr>
                <tr align="center"><td>Do not click this link if you didn't sign up for this site.</td></tr>
            </table>
            """
        )
        mail.send(msg)
    except Exception as e:
        print(e)
