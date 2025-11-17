# backend/models/chama.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, backref
from backend.database import Base

class Chama(Base):
    __tablename__ = "chamas"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    description = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by_user_id = Column(Integer, ForeignKey("users.id"))

    # Relationships
    memberships = relationship("Membership", back_populates="chama")
    contributions = relationship("Contribution", back_populates="chama")