from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from schemas import TokenData # Import the schema we created

# You MUST define these settings in your config.py
# from config import settings 
# settings.SECRET_KEY, settings.ALGORITHM, etc.
SECRET_KEY = "juice_wins"  # <-- REPLACE WITH A REAL SECRET KEY!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 # Set to your desired token expiry time


# --- Password Hashing Setup ---
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    """Verifies a plain password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    """Returns a hash of the given password."""
    return pwd_context.hash(password)


# --- JWT Token Setup ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/token")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Creates a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Use the global setting for default expiry
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[TokenData]:
    """Decodes a JWT access token and returns TokenData if valid."""
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
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception

    return token_data


# --- FastAPI Security Dependency ---
def get_current_user_email(token: Annotated[str, Depends(oauth2_scheme)]) -> str:
    """Dependency to get the current user's email from the JWT."""
    # This uses the same credentials_exception as decode_access_token
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token_data = decode_access_token(token)
    if token_data is None or token_data.email is None:
        raise credentials_exception
     
    return token_data.email
