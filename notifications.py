from models import Notification, db


def notify_user(user_id, subject, message):
    notification = Notification(user_id=user_id, subject=subject, message=message)
    db.session.add(notification)
    db.session.commit()
