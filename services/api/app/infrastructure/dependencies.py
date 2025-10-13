from fastapi import Depends, Request
import typing as t


import opentelemetry.instrumentation.redis as otel_redis
import opentelemetry.instrumentation.sqlalchemy as otel_sqla

import app.infrastructure.db as db
from app.infrastructure.cache.redis_manager import RedisConnectionManager
from app.infrastructure.db.sqla_manager import SQLAlchemySessionManager
import app.infrastructure.repositories as repos
import app.infrastructure.security as security
import app.infrastructure.tasks as tasks
import app.infrastructure.telemetry.traces as tracing
import app.infrastructure.adapters as adap
from app.common.config import Config, CeleryConfig

from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from celery import Celery


#Auth infrastructure choices
AuthStrategyType = security.StatefulOAuthStrategy

_PasswordHasherType = security.BCryptHasher
PasswordHasherType = lambda: adap.AsyncHasher(_PasswordHasherType())

#BackgroundTasks
_celery = Celery(Config.APP_NAME)
_celery.config_from_object(CeleryConfig)
_celery.autodiscover_tasks(['app.application.tasks'], related_name='__init__.py')
TaskProcessorType = tasks.CeleryTaskProcessor
TaskProcessor = TaskProcessorType(_celery)

#Dependeny itself is left in module to allow the use of decorator globally
TracerDependency = t.Annotated[tracing.TracerType, Depends(tracing.get_tracer)]


#####################################
#       Caches and databases        #
#####################################

DatabaseManagerType = SQLAlchemySessionManager
DatabaseSessionType = AsyncSession
DatabaseManager = DatabaseManagerType(Config.DB_URL, Config.DB_KWARGS)

####
#OTEL WRAPPERS
otel_redis.RedisInstrumentor().instrument()
otel_sqla.SQLAlchemyInstrumentor().instrument(engine=DatabaseManager._engine.sync_engine)
####


CacheManagerType =  RedisConnectionManager
CacheConnectionType = Redis
cache_args = dict(
    host="redis",
    port=6379,
    password=Config.REDIS_PASS,
    decode_responses=True,
    db=0
)
CacheManager = CacheManagerType(**cache_args)

UnitOfWork = db.SQLAlchemyUnitOfWork

async def get_db_session():
    async with DatabaseManager.session() as session:
        yield session

async def get_cache():
    async with CacheManager.connect() as connection:
        yield connection

DatabaseDependency = t.Annotated[DatabaseSessionType, Depends(get_db_session)]
CacheDependency = t.Annotated[CacheConnectionType, Depends(get_cache)]

async def get_uow(session: DatabaseDependency) -> t.AsyncIterable[UnitOfWork]:
    uow = UnitOfWork(session)
    yield uow
    await uow.commit() #Rollback is executed by SessionManager. Session is already wrapped in try/except with rollback on except, close on finally.
UoWDependency = t.Annotated[UnitOfWork, Depends(get_uow)]



#####################################
#            Repositories           # 
#####################################

UserDB = repos.SQLAUserRepository
UserRepository = repos.RedisCacheUserRepository
SessionRepository = repos.RedisSessionRepository
MetricActiveUsersRepository = repos.RedisMetricActiveUserStorage

async def get_user_repo(cache: CacheDependency, uow: UoWDependency):
    user_db = UserDB(uow.session)
    user_repo = UserRepository(user_db, cache, uow)
    return user_repo

async def get_session_repo(cache: CacheDependency):
    return SessionRepository(cache)

async def get_metric_active_users_repo(cache: CacheDependency):
    return MetricActiveUsersRepository(cache)


UserRepoDependency = t.Annotated[UserRepository, Depends(get_user_repo)]
SessionRepoDependency = t.Annotated[SessionRepository, Depends(get_session_repo)]
MetricActiveUsersRepoDependency = t.Annotated[MetricActiveUsersRepository, Depends(get_metric_active_users_repo)]


