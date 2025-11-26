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
    __table_args__ = {"schema": "public"} if __import__('os').getenv('DATABASE_URL', '').startswith('postgresql') else {}

    is_postgres = __import__('os').getenv('DATABASE_URL', '').startswith('postgresql')
    user_fk = "public.users.id" if is_postgres else "users.id"
    chama_fk = "public.chamas.id" if is_postgres else "chamas.id"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey(user_fk), nullable=False)
    chama_id = Column(Integer, ForeignKey(chama_fk), nullable=False)
    role = Column(Enum(MembershipRole), default=MembershipRole.member, nullable=False)

    user = relationship("User", back_populates="memberships")
    chama = relationship("Chama", back_populates="memberships")
    contributions = relationship("Contribution", cascade="all, delete-orphan")
