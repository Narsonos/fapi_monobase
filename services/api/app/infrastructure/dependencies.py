from fastapi import Depends
import typing as t

import app.infrastructure.interfaces as mgrs
from app.infrastructure.cache.redis_manager import RedisConnectionManager
from app.infrastructure.db.sqla_manager import SQLAlchemySessionManager
import app.infrastructure.repositories as repos
from app.common.config import Config

from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

#Connection level
DatabaseManager = SQLAlchemySessionManager(Config.DB_URL, Config.DB_KWARGS)
DatabaseSessionType = AsyncSession

CacheManager =  RedisConnectionManager(host="redis",port=6379,password=Config.REDIS_PASS,decode_responses=True,db=0)
CacheConnectionType = Redis

DatabaseDependency = t.Annotated[DatabaseSessionType, Depends(DatabaseManager.get_db_session)]
CacheDependency = t.Annotated[CacheConnectionType, Depends(CacheManager.connect)]


#Repositories
UserDB = repos.SQLAUserRepository
UserRepository = repos.RedisCacheUserRepository
SessionRepository = repos.RedisSessionRepository

def get_user_repo(dbsession: DatabaseDependency, cache: CacheDependency):
    user_db = UserDB(dbsession)
    user_repo = UserRepository(user_db, cache)
    return user_repo

def get_session_repo(cache: CacheDependency):
    return SessionRepository(cache)

UserRepoDependency = t.Annotated[UserRepository, Depends(get_user_repo)]
SessionRepoDependency = t.Annotated[SessionRepository, Depends(get_session_repo)]