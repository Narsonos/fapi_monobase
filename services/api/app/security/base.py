from fastapi import Depends, HTTPException, Security
from typing import Annotated, List, Optional
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer
from app.config import Config
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
from app.utils import exceptions as exc
import jwt
import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession
import app.models.common as models
import app.db as db
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import logging,pathlib

TOKEN_URL = f"/{Config.APP_NAME}/users/token"
oauth2 = OAuth2PasswordBearer(tokenUrl=TOKEN_URL)
oauth2_optional = OAuth2PasswordBearer(tokenUrl=TOKEN_URL, auto_error=False)
logger = logging.getLogger('app')



########################################
#   AUTHORIZATION AND AUTHENTICATION   #
########################################

#helper just to reduce codebase bloating
async def exctract_token_data(token:Annotated[str, Depends(oauth2)],refresh:bool=False):
    secret = Config.REFRESH_SECRET if refresh else Config.JWT_SECRET
    try:
        payload = jwt.decode(token, secret, algorithms=[Config.ALGORITHM])
        user_id = payload.get("user_id")
        session_id = payload.get("session_id")
        return (user_id,session_id)
    except InvalidTokenError as e:
        raise exc.CredentialsException()
    except ExpiredSignatureError as e:
        raise exc.TokenExpiredException()

def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password=pwd_bytes,salt=salt)

def verify_password(password: str, password_hash: str) -> bool:
    pwd_bytes = password.encode('utf-8')
    hash_bytes = password_hash.encode('utf-8')
    return bcrypt.checkpw(password=pwd_bytes,hashed_password=hash_bytes) 

async def authenticate_user(dbsession: AsyncSession, given_user: models.UserLoginModel) -> models.User | None:
    user: List[models.User] = (await db.get_users(dbsession, username=given_user.username, status='active')).one_or_none()
    if not user:
        raise exc.UserDoesNotExist()
    return user if verify_password(given_user.password,user.password_hash) else None

def create_access_token(user_id: int,session_id: str, expires_delta: timedelta, refresh: bool = False) -> str:
    secret = Config.REFRESH_SECRET if refresh else Config.JWT_SECRET
    encoded_jwt = jwt.encode({"user_id":user_id,"session_id":session_id, "exp":datetime.now(timezone.utc) + expires_delta}, secret, algorithm=Config.ALGORITHM)
    return encoded_jwt

def create_access_and_refresh(user_id, session_id=None, return_session_id=False):
    if not session_id:
        session_id = uuid4().hex
    access_token_expires = timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(user_id=user_id, session_id=session_id, expires_delta=access_token_expires)
    refresh_token_expires = timedelta(days=Config.REFRESH_TOKEN_EXPIRE_HOURS)
    refresh_token = create_access_token(user_id=user_id, session_id=session_id, expires_delta=refresh_token_expires, refresh=True)
    
    return (access_token, refresh_token) if not return_session_id else (access_token, refresh_token, session_id)



def get_current_user(require_active: bool = True, optional: bool = False):
    """
    Dependency factory.
    - require_active: если True -> проверяем current_user.status == "active"
    - optional: если True -> возвращаем None вместо выбрасывания ошибок при отсутствии/невалидности токена
    """

    token_dep = oauth2 if not optional else oauth2_optional

    async def _dep(dbsession: db.DBDependency, redis:db.RedisDependency, access_token: Annotated[str, Depends(token_dep)]) -> Optional[models.User]:
        """
        Main principle: You're logged in - as long as you're in Redis
        - Sessions are stored at "user_session:<user_id>:<session_id>
        """
        if not access_token:
            if optional:
                return None
            raise exc.CredentialsException()
        
        user_id,session_id = await exctract_token_data(access_token)

        #Get user session from redis
        user_session = await redis.hgetall(f"user_session:{user_id}:{session_id}")
        if not user_session: #If not in redis || token valid -> you're logged out
            raise exc.LoggedOutException()

        stored_token = user_session.get("access_token")
        if stored_token is None:
            logger.info("Debug: get_current_user: Session key exists but token does not -> The token has expired")
            raise exc.TokenExpiredException()
        if stored_token != access_token:
            logger.info("Debug: get_current_user: access_token differs from the one in redis")
            raise exc.TokenExpiredException()

        user = (await db.get_users(dbsession, id=user_id)).one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail={"msg":"User not found. Considering, the session exists => User has been deleted recently"})

        if require_active and user.status != "active":
            raise HTTPException(status_code=403, detail="Current user is inactve")

        return user  
    return _dep



async def create_admin_on_startup_if_not_exists():
    async with db.sessManagerObject.session() as sess:
        admin = (await db.get_users(sess, role='admin')).first()
        logger.info(f'HERE IS THE EXISTING ADMIN: {admin}')
        if not admin:
            logger.info('[INIT DB] Found no Admin user in user table -> Creating default admin.')
            admin = models.User(username=Config.DEFAULT_ADMIN_USERNAME, password_hash=hash_password(Config.DEFAULT_ADMIN_PASSWORD), role='admin', description='Default admin profile', b24id='default_admin')
            sess.add(admin)
            await sess.commit()

###################################################
#  FROM HERE AND FURTHER THIS DEPENDENCY IS USED  #
###################################################

CurrentUserDependency = Annotated[models.User,Depends(get_current_user(require_active=True))]
OptionalCurentUserDependency = Annotated[models.User, Depends(get_current_user(require_active=True, optional=True))]


