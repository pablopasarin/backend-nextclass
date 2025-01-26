# crud.py
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from models import User
from sqlalchemy.exc import NoResultFound

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Check if the username exists

def get_user_by_username(db: Session, username: str):
    user = db.query(User).filter(User.username == username).first()
    print(f"Buscando usuario: {username}, Resultado: {user}")
    return user
def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, username: str, email: str, password: str, confirmation_code: str):
    hashed_password = pwd_context.hash(password)
    new_user = User(
        username=username,
        email=email,
        hashed_password=hashed_password,
        confirmation_code=confirmation_code,  # Save the confirmation code
        is_email_confirmed=False,            # Default to not confirmed
        is_teacher=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def verify_confirmation_code(db: Session, email: str, code: int):
    user = db.query(User).filter(User.email == email, User.confirmation_code == code).first()
    return user

def activate_user(db: Session, user: User):
    user.is_email_confirmed = True
    db.commit()
    db.refresh(user)
