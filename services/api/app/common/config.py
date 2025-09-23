import os
import ssl

#For PostgreSQL
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE


class Config():
    #Basic app settings
    APP_NAME = 'api' #Is gonna match the app root 
    UVICORN_PORT = 8000
    UVICORN_HOST = '0.0.0.0'
    BASE_URL_LOCAL = f"http://{UVICORN_HOST}:{UVICORN_PORT}" #Utilized by telegram proxy mechanisms
    GIT_COMMIT = os.getenv("GIT_COMMIT", "[commit hash unknown]")
    MODE = os.getenv("MODE", "Local build")

    #Security settings
    DEFAULT_ADMIN_USERNAME = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
    DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD")
    JWT_SECRET = os.getenv("JWT_SECRET")
    REFRESH_SECRET = os.getenv("REFRESH_SECRET")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 240
    REFRESH_TOKEN_EXPIRE_HOURS = 7*24
    LOCK_TIME = 60 #TTL for locks. I.e. in 60s the lock is considered as deadlock => gets auto-unlocked.

    #Redis
    REDIS_PASS = os.getenv("REDIS_PASS")
    REDIS_URL = f'redis://:{REDIS_PASS}@redis:6379/0'
    USER_CACHE_TTL_SECONDS = int(os.getenv("USER_CACHE_TTL_SECONDS", "300"))

    #MySQL Template
    DB_USER = os.getenv("MYSQL_USER")
    DB_PASS = os.getenv("MYSQL_PASSWORD")
    DB_NAME = os.getenv("MYSQL_DATABASE")
    DB_HOST = 'db'
    DB_PORT = 3306
    DB_URL = f"mysql+aiomysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    #PostgreSQL Template
    #DB_USER = os.getenv("POSTGRES_USER")
    #DB_PASS = os.getenv("POSTGRES_PASSWORD")
    #DB_NAME = os.getenv("POSTGRES_DB")
    #DB_HOST = 'db'
    #DB_PORT = 5432
    #DB_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    #DB Common
    DB_WAIT_INTERVAL_SECONDS = 10  #seconds
    DB_WAIT_MAX_RETRIES = 10
    DB_KWARGS = {
        'echo': False,
    }




