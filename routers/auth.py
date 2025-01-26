from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from datetime import datetime, timedelta
from typing import Union
import jwt
from fastapi import Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from decouple import config
import smtplib
from email.mime.text import MIMEText
import crud
from database import get_db
from models import User
from pydantic import BaseModel
from config import settings

router = APIRouter()



# Encryption context for passwords
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2PasswordBearer for token-based authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# ---- Utilities for Passwords ----

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify if a plain password matches its hashed version.
    """
    return pwd_context.verify(plain_password, hashed_password)


def authenticate_user(db: Session, email: str, password: str):
    """
    Authenticate the user by email and verify the password.
    """
    user = crud.get_user_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password) or not user.is_email_confirmed:
        return None
    return user


# ---- Token Creation ----

def create_access_token(data: dict, expires_delta: timedelta) -> str:
    """
    Generate a JWT access token with expiration.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    
   
# ---- Token Verification ----

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """
    Dependency to get the current user from a JWT token.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales incorrectas",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user = crud.get_user_by_email(db, email)
        if user is None or not user.is_email_confirmed:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario no encontrado o cuenta no activada",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token ha expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ---- Login for Access Token ----

async def login_for_access_token(email: str, password: str, db: Session):
    """
    Validate user credentials and return an access token.
    """
    user = authenticate_user(db, email, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Contraseña o email incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.email, "user_id": user.id, "username": user.username, "is_teacher": user.is_teacher}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}



class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/token")
async def get_access_token(data: LoginRequest, db: Session = Depends(get_db)):
    """
    Generate an access token for the user, accepting JSON payload.
    """
    return await login_for_access_token(email=data.email, password=data.password, db=db)

class TokenValidationRequest(BaseModel):
    token: str

@router.post("/validate-token")
def validate_token(data: TokenValidationRequest):
    """
    Validate the recovery token.
    """
    try:
        # Decode the token
        payload = jwt.decode(data.token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return {"message": "Token válido"}
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token ha expirado.",
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token no válido.",
        )


