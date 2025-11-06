from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class Contribution(Base):
    __tablename__ = "contributions"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id"))
    chama_id = Column(Integer, ForeignKey("chamas.id"))

    # Relationships
    contributor = relationship("User", backref="contributions_made")
    chama = relationship("Chama", back_populates="contributions")