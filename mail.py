from flask_mail import Message, Mail
import secrets
import string
import time

mail = Mail()

pending_verifications = {}

def generate_id(email):
    code = ''.join((secrets.choice(string.ascii_letters) for i in range(6)))
    verifier = secrets.token_urlsafe(32)
    pending_verifications[verifier] = (email, code, int(time.time()))
    return (code, verifier)

def decode_email(verifier, expiration=86400):
    entry = pending_verifications.get(verifier)
    if entry is None:
        return False
    email, _, created = entry
    if int(time.time()) - created > expiration:
        del pending_verifications[verifier]
        return False
    return email

def confirm_token(verifier, token, expiration=86400):
    email = decode_email(verifier, expiration)
    if not email:
        return False
    if not secrets.compare_digest(pending_verifications[verifier][1].encode(), token.encode()):
        return False
    del pending_verifications[verifier]
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
