import os
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base

# Declare the Base
Base = declarative_base()

# Database URL from environment variable
DATABASE_URL = os.getenv("MYSQLDATABASE_URL")

# Validar que la variable esté definida
if not DATABASE_URL:
    raise ValueError("❌ ERROR: La variable de entorno 'MYSQLDATABASE_URL' no está definida.")

# Asegurar que usa el driver correcto para MySQL
if DATABASE_URL.startswith("mysql://"):
    DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+pymysql://")

# Create the Engine and SessionLocal
engine = create_engine(DATABASE_URL, pool_pre_ping=True)  # pool_pre_ping=True para evitar desconexiones

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Dependency for getting the DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        print(f"❌ Error en la sesión de la base de datos: {e}")
        db.rollback()  # Deshacer cambios en caso de error
    finally:
        db.close()