from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import user, auth, chat, classes, students  # Import modularized routers
import models
import database
import logging




# ---- Application Initialization ----
app = FastAPI()

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
allow_origins=["http://localhost:3000"],  # URL del frontend en desarrollo    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(user.router, prefix="/users", tags=["users"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(classes.router, prefix="/classes", tags=["classes"])
app.include_router(students.router, prefix="/students", tags=["students"])

# Create Database Tables
models.Base.metadata.create_all(bind=database.engine)



logger = logging.getLogger('uvicorn.error')
logger.debug("Logger initialized")
# ---- Root Endpoint ----
@app.get("/")
def read_root():
    logger.debug("GET request to / endpoint")
    return {"message": "Welcome to the API!"}