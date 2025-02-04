from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import user, auth, chat, classes, students  # Import modularized routers
import models
import database
import logging
import uvicorn
import os


# ---- Application Initialization ----
app = FastAPI()

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # URL del frontend en desarrollo
        "https://nextclass.vercel.app",  # URL del frontend en producción
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Permitir todos los métodos HTTP (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Permitir todos los encabezados
)

# Include Routers
app.include_router(user.router, prefix="/users", tags=["users"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(classes.router, prefix="/classes", tags=["classes"])
app.include_router(students.router, prefix="/students", tags=["students"])

# Crear las tablas cuando la aplicación arranque
@app.on_event("startup")
def startup():
    print("🔹 Creando tablas en la base de datos (si no existen)...")
    models.Base.metadata.create_all(bind=database.engine)
    print("✅ Tablas creadas.")


logger = logging.getLogger('uvicorn.error')
logger.debug("Logger initialized")
# ---- Root Endpoint ----
@app.get("/")
def read_root():
    logger.debug("GET request to / endpoint")
    return {"message": "Welcome to the API!"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))  # Usa el puerto asignado por Railway
    uvicorn.run(app, host="0.0.0.0", port=port)