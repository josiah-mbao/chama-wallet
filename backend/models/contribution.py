# backend/models/contribution.py
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.database import Base

class Contribution(Base):
    __tablename__ = "contributions"
    # No schema specified - uses tenant schema via search_path

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    membership_id = Column(Integer, ForeignKey("memberships.id"))
    chama_id = Column(Integer, ForeignKey("public.chamas.id"))

    chama = relationship("Chama", back_populates="contributions")
