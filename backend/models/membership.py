from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Membership(Base):
    __tablename__ = "memberships"

    id = Column(Integer, primary_key=True, index=True)
    
    # Relationships to User and Chama
    user_id = Column(Integer, ForeignKey("users.id"))
    chama_id = Column(Integer, ForeignKey("chamas.id"))

    # The role of the user within this specific chama (e.g., 'admin', 'member')
    role = Column(String, default="member") 

    # Define the actual relationships
    user = relationship("User", back_populates="memberships")
    chama = relationship("Chama", back_populates="memberships")
