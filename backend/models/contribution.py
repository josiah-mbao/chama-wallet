# backend/models/contribution.py
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.database import Base

class Contribution(Base):
    __tablename__ = "contributions"
    # No schema specified - uses tenant schema via search_path in PostgreSQL, no schema in SQLite

    is_postgres = __import__('os').getenv('DATABASE_URL', '').startswith('postgresql')
    membership_fk = "public.memberships.id" if is_postgres else "memberships.id"
    chama_fk = "public.chamas.id" if is_postgres else "chamas.id"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    membership_id = Column(Integer, ForeignKey(membership_fk))
    chama_id = Column(Integer, ForeignKey(chama_fk))

    chama = relationship("Chama", back_populates="contributions")
