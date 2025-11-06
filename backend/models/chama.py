from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Chama(Base):
    __tablename__ = "chamas"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Foreign key linking the Chama creator to the User model
    created_by_user_id = Column(Integer, ForeignKey("users.id"))
    creator = relationship("User", backref="created_chamas")

    # Relationship to the Membership model
    memberships = relationship("Membership", back_populates="chama")
    contributions = relationship("Contribution", back_populates="chama")
