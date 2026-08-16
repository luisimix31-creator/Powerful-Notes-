import uuid
from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    practice_name = db.Column(db.String(255), default="")
    options_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    clients = db.relationship("Client", backref="user", cascade="all, delete-orphan")
    notes = db.relationship("SavedNote", backref="user", cascade="all, delete-orphan")
    generated_notes = db.relationship("GeneratedNote", backref="user", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Client(db.Model):
    id = db.Column(db.String(16), primary_key=True, default=lambda: str(uuid.uuid4())[:8])
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    dob = db.Column(db.String(20), default="")
    diagnosis = db.Column(db.String(255), default="")
    guardian_name = db.Column(db.String(255), default="")
    guardian_relationship = db.Column(db.String(255), default="")
    rbt_name = db.Column(db.String(255), default="")
    replacement_programs = db.Column(db.JSON, default=list)
    maladaptive_behaviors = db.Column(db.JSON, default=list)
    intervention_strategies = db.Column(db.JSON, default=list)
    training_topics = db.Column(db.JSON, default=list)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "dob": self.dob or "",
            "diagnosis": self.diagnosis or "",
            "guardian_name": self.guardian_name or "",
            "guardian_relationship": self.guardian_relationship or "",
            "rbt_name": self.rbt_name or "",
            "replacement_programs": self.replacement_programs or [],
            "maladaptive_behaviors": self.maladaptive_behaviors or [],
            "intervention_strategies": self.intervention_strategies or [],
            "training_topics": self.training_topics or [],
            "created_at": self.created_at.isoformat(timespec="seconds") if self.created_at else "",
        }


class GeneratedNote(db.Model):
    """Log of every note the generator produces (saved or not), used only to
    check new notes for excess similarity against recent output of the same type."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    note_type = db.Column(db.String(30), nullable=False, index=True)
    note_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class SavedNote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    client_id = db.Column(db.String(16), db.ForeignKey("client.id"), nullable=False, index=True)
    client_name = db.Column(db.String(255), default="")
    filename = db.Column(db.String(255), nullable=False)
    note_type = db.Column(db.String(30), nullable=False)
    session_date = db.Column(db.String(20), default="")
    note_text = db.Column(db.Text, nullable=False)
    word_count = db.Column(db.Integer, default=0)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "filename": self.filename,
            "client_id": self.client_id,
            "client_name": self.client_name,
            "note_type": self.note_type,
            "session_date": self.session_date,
            "saved_at": self.saved_at.isoformat(timespec="seconds") if self.saved_at else "",
            "word_count": self.word_count,
        }
