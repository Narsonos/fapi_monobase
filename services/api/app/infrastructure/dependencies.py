from fastapi import Depends
import typing as t

import app.infrastructure.db.base as mgrs
from app.infrastructure.cache.redis_manager import RedisConnectionManager
from app.infrastructure.db.sqla_manager import SQLAlchemySessionManager
from app.common.config import Config

from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis


DatabaseManager = SQLAlchemySessionManager(Config.DB_URL, Config.DB_KWARGS)
DatabaseSessionType = AsyncSession

CacheManager =  RedisConnectionManager(host="redis",port=6379,password=Config.REDIS_PASS,decode_responses=True,db=0)
CacheConnectionType = Redis

DatabaseDependency = t.Annotated[DatabaseSessionType, Depends(DatabaseManager.get_db_session)]
CacheDependency = t.Annotated[CacheConnectionType, Depends(CacheManager.connect)]
