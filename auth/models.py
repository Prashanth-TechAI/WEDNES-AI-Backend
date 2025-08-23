from sqlalchemy import Column, Integer, String
from .database import Base
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from datetime import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True)
    hashed_password = Column(String)
    oauth_provider = Column(String, nullable=True)

    full_name = Column(String)
    phone_number = Column(String, nullable=True)
    bio = Column(String, nullable=True)
    profile_picture_url = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)  # ✅ ADD THIS LINE


class Pipeline(Base):
    __tablename__ = "pipelines"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    agent_type = Column(String)
    config = Column(String)
    session_id = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class ApiKey(Base):
    __tablename__ = "api_keys"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    provider = Column(String)
    key = Column(String)  # Encrypted
    created_at = Column(DateTime, default=datetime.utcnow)
