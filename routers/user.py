from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import timedelta
from config import settings
from database import get_db
from models import User, Class
from routers.auth import get_current_user, create_access_token, verify_password, pwd_context
import jwt
import smtplib
from decouple import config
from crud import create_user, verify_confirmation_code, activate_user
import crud
import random
from email_utils import send_confirmation_email, send_recovery_email
router = APIRouter()

# ---- Models ----

class ProfileUpdate(BaseModel):
    name: str
    bio: str = None  # Optional

class PasswordRecoveryRequest(BaseModel):
    email: EmailStr

class PasswordReset(BaseModel):
    token: str
    new_password: str

class EmailCheck(BaseModel):
    email: EmailStr

class UsernameCheck(BaseModel):
    username: str

class PasswordCheck(BaseModel):
    password: str

class UserRegistration(BaseModel):
    username: str
    email: EmailStr
    password: str

class EmailConfirmationRequest(BaseModel):
    email: EmailStr
    code: int

# ---- Utility Functions ----

def is_password_strong(password: str) -> bool:
    """
    Validate if a password is strong enough.
    """
    import re
    strong_password_regex = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^a-zA-Z0-9]).{8,}$"
    return bool(re.match(strong_password_regex, password))


# ---- Routes ----

@router.get("/me")
def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Retrieve the current user's profile.
    """
    return {"username": current_user.username, "email": current_user.email}

@router.put("/me")
def update_user_profile(
    profile: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update the profile of the current user.
    """
    current_user.name = profile.name
    current_user.bio = profile.bio
    db.commit()
    db.refresh(current_user)
    return {"message": "Profile updated", "user": {"name": current_user.name, "bio": current_user.bio}}

@router.post("/password-recovery")
def password_recovery(
    request: PasswordRecoveryRequest,
    db: Session = Depends(get_db),
):
    """
    Request password recovery.
    """
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email no encontrado",
        )
    # Generate a recovery token
    recovery_token_expires = timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES)
    recovery_token = create_access_token(data={"sub": user.email}, expires_delta=recovery_token_expires)
    # Send the token via email
    if not send_recovery_email(request.email, recovery_token):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al enviar el correo de recuperación. Inténtalo de nuevo."
        )
    return {"message": "Correo de recuperación enviado."}


@router.post("/reset-password")
def reset_password(data: PasswordReset, db: Session = Depends(get_db)):
    """
    Reset a user's password.
    """
    try:
        # Decode the recovery token
        payload = jwt.decode(data.token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token",
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token",
        )

    # Retrieve the user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email no encontrado",
        )

    # Validate new password strength
    if not is_password_strong(data.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña es débil. Debe tener al menos 8 caracteres, una letra mayúscula, un número y un carácter especial.",
        )

    # Update password
    hashed_password = pwd_context.hash(data.new_password)
    user.hashed_password = hashed_password
    db.commit()
    return {"message": "Password updated successfully."}




@router.post("/register")
def register_user(
    user_data: UserRegistration, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
    """
    Register a new user and send an email confirmation code.
    """
    # Validate username and email first
    if crud.get_user_by_username(db, user_data.username):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken.")
    if crud.get_user_by_email(db, user_data.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered.")

    if not is_password_strong(user_data.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is too weak. Must contain at least 8 characters, one uppercase letter, one number, and one special character.",
        )

    # Generate a confirmation code
    confirmation_code = random.randint(100000, 999999)

    # Try to send the email first
    if not send_confirmation_email(user_data.email,str(confirmation_code)):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send confirmation email. Please try again later."
        )

    # Only create user if email was sent successfully
    try:
        create_user(
            db=db,
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            confirmation_code=confirmation_code,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user account."
        )

    return {"message": "User registered successfully. A confirmation email has been sent."}


class ConfirmEmailRequest(BaseModel):
    email: str
    confirmation_code: int

@router.post("/confirm-email")
def confirm_email(request: ConfirmEmailRequest, db: Session = Depends(get_db)):
    """
    Confirm user's email using the confirmation code.
    """
    # Verificar si el código de confirmación es válido
    user = verify_confirmation_code(db, email=request.email, code=request.confirmation_code)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid confirmation code or email.",
        )

    # Activar al usuario
    activate_user(db, user)
    return {"message": "Email confirmed successfully!"}
