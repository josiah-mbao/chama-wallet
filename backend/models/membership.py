# backend/models/membership.py
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base

class Membership(Base):
    __tablename__ = "memberships"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    chama_id = Column(Integer, ForeignKey("chamas.id"))
    role = Column(String, default="member") 

    # Relationships
    user = relationship("User", back_populates="memberships")
    chama = relationship("Chama", back_populates="memberships")
    contributions = relationship("Contribution", back_populates="member")