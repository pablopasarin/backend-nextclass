from decouple import config

class Settings:
    ENVIRONMENT = config("ENVIRONMENT", default="development")
    SECRET_KEY = config("SECRET_KEY")
    ALGORITHM = config("ALGORITHM", default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = config("ACCESS_TOKEN_EXPIRE_MINUTES", cast=int, default=30)
    PASSWORD_RESET_EXPIRE_MINUTES = config("PASSWORD_RESET_EXPIRE_MINUTES", cast=int, default=10)
    FRONTEND_URL = config("FRONTEND_URL") 
    LOGO_URL = config("LOGO_URL")
    SSL_CERTFILE = config("SSL_CERTFILE", default=None)
    SSL_KEYFILE = config("SSL_KEYFILE", default=None)
    USE_HTTPS = ENVIRONMENT == "production"
    SQLALCHEMY_DATABASE_URL = config("MYSQLDATABASE_URL")

settings = Settings()