from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String) # 'client', 'dispatcher', 'admin'
    is_blocked = Column(Boolean, default=False)
    block_until = Column(DateTime, nullable=True)

class Request(Base):
    __tablename__ = "requests"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String)
    status = Column(String, default="Новая")
    dispatcher = Column(String, nullable=True)
    created_by = Column(String, nullable=True)
    comments_enabled = Column(Boolean, default=True) # Плашка "Комментарии"
    created_at = Column(DateTime, default=datetime.utcnow)

class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("requests.id"))
    author = Column(String)
    text = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("requests.id"))
    sender = Column(String) # 'client', 'dispatcher', 'admin'
    text = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)