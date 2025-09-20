from fastapi import Depends, Request
import typing as t

import app.infrastructure.db as db
from app.infrastructure.cache.redis_manager import RedisConnectionManager
from app.infrastructure.db.sqla_manager import SQLAlchemySessionManager
import app.infrastructure.repositories as repos
from app.common.config import Config

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from redis.asyncio import Redis

#Connection level
DatabaseManager = SQLAlchemySessionManager(Config.DB_URL, Config.DB_KWARGS)
DatabaseSessionType = AsyncSession

CacheManager =  RedisConnectionManager(host="redis",port=6379,password=Config.REDIS_PASS,decode_responses=True,db=0)
CacheConnectionType = Redis

UnitOfWork = db.SQLAlchemyUnitOfWork

DatabaseDependency = t.Annotated[DatabaseSessionType, Depends(DatabaseManager.get_db_session)]
CacheDependency = t.Annotated[CacheConnectionType, Depends(CacheManager.connect)]


async def get_uow(session: DatabaseDependency) -> t.AsyncIterable[UnitOfWork]:
    uow = UnitOfWork(session)
    yield uow
    await uow.commit() #Rollback is executed by SessionManager. Session is already wrapped in try/except with rollback on except, close on finally.

UoWDependency = t.Annotated[UnitOfWork, Depends(get_uow)]

#Repositories
UserDB = repos.SQLAUserRepository
UserRepository = repos.RedisCacheUserRepository
SessionRepository = repos.RedisSessionRepository

async def get_user_repo(cache: CacheDependency, uow: UoWDependency):
    user_db = UserDB(uow.session)
    user_repo = UserRepository(user_db, cache, uow)
    return user_repo

async def get_session_repo(cache: CacheDependency):
    return SessionRepository(cache)



UserRepoDependency = t.Annotated[UserRepository, Depends(get_user_repo)]
SessionRepoDependency = t.Annotated[SessionRepository, Depends(get_session_repo)]