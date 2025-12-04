from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# Association table for Many-to-Many relationship between User and Model
unlocked_models = db.Table('unlocked_models',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('model_id', db.Integer, db.ForeignKey('model.id'), primary_key=True),
    db.Column('unlocked_at', db.DateTime, default=datetime.utcnow)
)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), default='student')  # student, professor, admin
    xp = db.Column(db.Integer, default=0)
    level = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    unlocked_content = db.relationship('Model', secondary=unlocked_models, lazy='subquery',
        backref=db.backref('users', lazy=True))

    def __repr__(self):
        return f'<User {self.username}>'

class Model(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    file_path = db.Column(db.String(255), nullable=False)  # Path to .glb file
    thumbnail_path = db.Column(db.String(255), nullable=True)
    source = db.Column(db.String(50), default='generated')  # generated, upload, sketchfab
    is_public = db.Column(db.Boolean, default=False)
    uploader_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Model {self.name}>'
