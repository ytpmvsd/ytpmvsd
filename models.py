import datetime
from flask_bcrypt import Bcrypt
from flask_login import UserMixin


from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import TIMESTAMP
from sqlalchemy.dialects.postgresql import ARRAY

db = SQLAlchemy()
bcrypt = Bcrypt()


class Sample(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String, nullable=False)
    tags = db.Column(ARRAY(db.String), nullable=False, default=[])
    upload_date = db.Column(TIMESTAMP(timezone=True) , nullable=False, default=datetime.datetime.now(datetime.UTC))
    thumbnail_filename = db.Column(db.String, nullable=False)
    likes = db.Column(db.Integer, nullable=False, default=0)
    uploader = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(80), unique=True)
    username = db.Column(db.String(30), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_uploader = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)