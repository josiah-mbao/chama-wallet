from datetime import datetime, timedelta, timezone
from typing import Optional, List

import os
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from backend import crud, schemas
from backend.database import get_db, current_tenant
from backend.models.user import UserRole, User
from backend.models.membership import Membership, MembershipRole
from backend.exceptions import AuthenticationError, AuthorizationError, InactiveUserError


# --- Config (should come from environment in production) ---
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    import warnings
    warnings.warn(
        "SECRET_KEY not set in environment. Using default for development only!",
        RuntimeWarning,
        stacklevel=2
    )
    SECRET_KEY = "default_dev_secret_key_change_in_production"
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))


# --- Password hashing ---
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# --- OAuth2 setup ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/token")


# --- JWT token helpers ---
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
            raise credentials_exception
        return schemas.TokenData(email=email)
    except JWTError:
        raise credentials_exception


# --- Dependency: Get current DB user ---
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    token_data = decode_access_token(token)
    user = crud.get_user_by_email(db, email=token_data.email)
    if user is None or not getattr(user, "is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive or invalid user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


# --- Global role check (user-level, not Chama-specific) ---
def require_user_role(*allowed_roles: UserRole):
    """
    Dependency factory to check user's global role.
    Example: require_user_role(UserRole.owner, UserRole.treasurer)
    """
    def wrapper(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User role '{current_user.role}' does not have permission."
            )
        return current_user
    return wrapper


# --- Chama-specific role check ---
def require_chama_role(chama_id: int, allowed_roles: List[MembershipRole]):
    """
    Dependency factory to check a user's role within a specific Chama.
    Example: require_chama_role(chama_id, [MembershipRole.owner, MembershipRole.treasurer])
    """
    def wrapper(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
        membership = db.query(Membership).filter(
            Membership.user_id == current_user.id,
            Membership.chama_id == chama_id
        ).first()
        if not membership:
            raise HTTPException(status_code=403, detail="User is not a member of this Chama")
        if membership.role not in allowed_roles:
            allowed_roles_str = ", ".join([r.value for r in allowed_roles])
            raise HTTPException(
                status_code=403,
                detail=f"Requires role: {allowed_roles_str}"
            )
        return membership
    return wrapper


# --- Multi-tenant billing dependency ---
def get_current_tenant_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency that returns the current authenticated user with tenant context.
    For billing operations, tenant context is managed separately.

    This is a wrapper around get_current_user that can be extended for tenant-specific
    billing operations if needed.
    """
    return current_user
