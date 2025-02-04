#database.py
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os
# Declare the Base
Base = declarative_base()

# Database URL
SQLALCHEMY_DATABASE_URL = os.getenv("MYSQLDATABASE_URL")  # Replace with your actual DB URL

# Create the Engine and SessionLocal
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Dependency for getting the DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
