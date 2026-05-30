import json
from app import db
from datetime import datetime


# ──────────────────────────────────────────
# User Table
# ──────────────────────────────────────────
class User(db.Model):
    __tablename__ = 'users'

    id           = db.Column(db.Integer, primary_key=True)
    name         = db.Column(db.String(100), nullable=False)
    email        = db.Column(db.String(150), unique=True, nullable=False)
    password     = db.Column(db.String(200), nullable=False)
    denomination = db.Column(db.String(100), default='Protestant (General)')
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    conversations = db.relationship('Conversation', back_populates='user',
                                    cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id':           self.id,
            'name':         self.name,
            'email':        self.email,
            'denomination': self.denomination,
            'created_at':   self.created_at.isoformat()
        }

    def __repr__(self):
        return f'<User {self.email}>'


# ──────────────────────────────────────────
# Conversation Table
# ──────────────────────────────────────────
class Conversation(db.Model):
    __tablename__ = 'conversations'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title      = db.Column(db.String(200), default='New Conversation')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow)

    user     = db.relationship('User', back_populates='conversations')
    messages = db.relationship('Message', back_populates='conversation',
                               cascade='all, delete-orphan',
                               order_by='Message.created_at')

    def to_dict(self):
        return {
            'id':         self.id,
            'user_id':    self.user_id,
            'title':      self.title,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    def __repr__(self):
        return f'<Conversation {self.title}>'


# ──────────────────────────────────────────
# Message Table
# ──────────────────────────────────────────
class Message(db.Model):
    __tablename__ = 'messages'

    id              = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'),
                                nullable=False)
    role            = db.Column(db.String(20), nullable=False)
    content         = db.Column(db.Text, nullable=False)
    verses_used     = db.Column(db.Text, default='')
    image_url       = db.Column(db.String(500), default='')
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    conversation = db.relationship('Conversation', back_populates='messages')

    @property
    def verses_used_list(self):
        """Parse verses_used JSON string into a Python list safely."""
        if not self.verses_used:
            return []
        try:
            data = json.loads(self.verses_used)
            if isinstance(data, list):
                return data
            return []
        except Exception:
            return []

    def to_dict(self):
        return {
            'id':              self.id,
            'conversation_id': self.conversation_id,
            'role':            self.role,
            'content':         self.content,
            'verses_used':     self.verses_used,
            'verses_list':     self.verses_used_list,
            'image_url':       self.image_url,
            'created_at':      self.created_at.isoformat()
        }

    def __repr__(self):
        return f'<Message {self.role}: {self.content[:40]}>'


# ──────────────────────────────────────────
# GeneratedImage Table
# ──────────────────────────────────────────
class GeneratedImage(db.Model):
    __tablename__ = 'generated_images'

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    prompt      = db.Column(db.Text, nullable=False)
    safe_prompt = db.Column(db.Text, default='')
    image_url   = db.Column(db.String(500), nullable=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User')

    def to_dict(self):
        return {
            'id':          self.id,
            'user_id':     self.user_id,
            'prompt':      self.prompt,
            'safe_prompt': self.safe_prompt,
            'image_url':   self.image_url,
            'created_at':  self.created_at.isoformat()
        }

    def __repr__(self):
        return f'<GeneratedImage {self.prompt[:40]}>'