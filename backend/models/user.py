from sqlalchemy import Column, Integer, String, Boolean, text, Enum
from sqlalchemy.orm import relationship
import enum
from backend.database import Base

class UserRole(str, enum.Enum):
    owner = "owner"
    treasurer = "treasurer"
    member = "member"


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "public"} if __import__('os').getenv('DATABASE_URL', '').startswith('postgresql') else {}

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(320), unique=True, index=True, nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    hashed_password = Column(String(256), nullable=False)
    is_active = Column(Boolean, nullable=False, server_default=text("true"))

    role = Column(Enum(UserRole), nullable=False, server_default="member")
    memberships = relationship("Membership", back_populates="user", cascade="all, delete-orphan")
