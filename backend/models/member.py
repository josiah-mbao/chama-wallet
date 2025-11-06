from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from database import Base

class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)

    # Define the relationship to Contribution (from contribution.py)
    contributions = relationship("Contribution", back_populates="member")
