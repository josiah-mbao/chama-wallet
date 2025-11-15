# backend/models/membership.py
from sqlalchemy import Column, Integer, ForeignKey, Enum
from sqlalchemy.orm import relationship
from backend.database import Base
import enum

class MembershipRole(str, enum.Enum):
    owner = "owner"
    treasurer = "treasurer"
    member = "member"

class Membership(Base):
    __tablename__ = "memberships"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    chama_id = Column(Integer, ForeignKey("chamas.id"), nullable=False)
    role = Column(Enum(MembershipRole), default=MembershipRole.member, nullable=False)

    user = relationship("User", back_populates="memberships")
    chama = relationship("Chama", back_populates="memberships")
    contributions = relationship("Contribution", back_populates="membership", cascade="all, delete-orphan")

