# backend/security.py
from datetime import datetime, timedelta, timezone
from typing import Optional

import os
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from backend import crud, schemas
from backend.database import get_db
from backend.models.user import UserRole
from backend.models.user import User
from backend.models.membership import Membership, MembershipRole
from backend.routers.users import get_current_user


# Config (must come from env in production)
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY not set in environment")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

# Password hashing - ensure argon2-cffi or bcrypt is installed
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/token")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp())
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> schemas.TokenData:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            # sometimes sub stored differently; handle gracefully
            raise credentials_exception
        return schemas.TokenData(email=email)
    except JWTError:
        raise credentials_exception


# Dependency that returns the full DB user
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    token_data = decode_access_token(token)
    user = crud.get_user_by_email(db, email=token_data.email)
    if user is None or not getattr(user, "is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive or invalid user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_role(*allowed_roles: UserRole):
    """
    A dependency factory: require_role(UserRole.owner, UserRole.treasurer)
    """
    def wrapper(current_user_email: str = Depends(get_current_user), db: Session = Depends(get_db)):
        user = db.query(User).filter(User.email == current_user_email).first()

        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User role '{user.role}' does not have permission."
            )

        return user  # Return full user object for router use

    return wrapper

def require_role(chama_id: int, allowed_roles: list[MembershipRole]):
    """Factory dependency to check a user's role in a Chama."""
    def role_dependency(
        current_user: str = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
        user = db.query(User).filter(User.email == current_user).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        membership = db.query(Membership).filter(
            Membership.user_id == user.id,
            Membership.chama_id == chama_id
        ).first()
        
        if not membership:
            raise HTTPException(status_code=403, detail="Not a member of this Chama")
        
        if membership.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Requires role: {', '.join([r.value for r in allowed_roles])}"
            )
        
        return membership
    return role_dependency
