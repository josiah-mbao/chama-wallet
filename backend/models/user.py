# backend/models/user.py
from sqlalchemy import Column, Integer, String, Boolean, text
from sqlalchemy.orm import relationship
from backend.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(320), unique=True, index=True, nullable=False)  # RFC 5321 max 320
    hashed_password = Column(String(256), nullable=False)
    is_active = Column(Boolean, nullable=False, server_default=text("true"))

    # Relationship: a user can have many memberships
    memberships = relationship("Membership", back_populates="user")