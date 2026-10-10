from flask_mail import Message, Mail
from itsdangerous import URLSafeSerializer, BadSignature
from config import SECRET_KEY
import hashlib
import hmac
import secrets
import string
import time

mail = Mail()

s = URLSafeSerializer(SECRET_KEY, salt="email-verification")

def _sign(token, email, epoch):
    msg = f"{token}:{email}:{epoch}".encode()
    return hmac.new(SECRET_KEY.encode(), msg, hashlib.sha256).hexdigest()

def generate_id(email):
    token = ''.join((secrets.choice(string.ascii_letters) for i in range(6)))
    epoch_time = int(time.time())
    verifier = s.dumps({"email": email, "epoch": epoch_time, "hash": _sign(token, email, epoch_time)})
    return (token, verifier)

def _load_verifier(verifier, expiration):
    try:
        data = s.loads(verifier)
        email, epoch, digest = data["email"], int(data["epoch"]), data["hash"]
    except (BadSignature, KeyError, TypeError, ValueError):
        return None
    if int(time.time()) > epoch + expiration:
        return None
    return (email, epoch, digest)

def decode_email(verifier, expiration=86400):
    data = _load_verifier(verifier, expiration)
    if data is None:
        return False
    return data[0]

def confirm_token(verifier, token, expiration=86400):
    data = _load_verifier(verifier, expiration)
    if data is None:
        return False
    email, epoch, digest = data
    if not hmac.compare_digest(_sign(token, email, epoch), digest):
        return False
    return email

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
