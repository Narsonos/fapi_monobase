from app.config import Config
import app.utils.exceptions as exc
import app.models.common as models

from sqlalchemy.ext.asyncio import AsyncConnection,AsyncSession,async_sessionmaker,create_async_engine
from sqlalchemy import text, MetaData, Integer, Float, Boolean, DateTime, Table, Column, Text, BigInteger, select, ScalarResult
from sqlmodel import SQLModel
from redis.asyncio.client import Redis

from typing import Annotated, Any, AsyncIterator, Literal, List
from fastapi import Depends, Request, HTTPException

import asyncio
import contextlib
import logging

logger = logging.getLogger('app.db')


###############
#    REDIS    #
###############

redis_client = Redis(
    host="redis",
    port=6379,
    password=Config.REDIS_PASS,
    decode_responses=True,
    db=0
)

def get_redis(request: Request):
    """Retrieves redis from app state"""
    return request.app.state.redis


################
#   DATABASE   #
################

class DatabaseSessionManager:
    """DBSessionManager - credit to: Thomas's Aitken article at Medium.com
    Spawns Async sessions and connections to a database using SQLAlchemy and ensures they're closed/rolled back properly
    """

    def __init__(self, host: str, engine_kwargs: dict[str,Any] = {}):
        self._engine = create_async_engine(host, **engine_kwargs)
        self._sessionmaker = async_sessionmaker(autocommit=False, bind=self._engine)

    async def close(self):
        if self._engine is None:
            raise exc.CustomDatabaseException("[DB Manager] DatabaseSessionManager is not initizalized!")
        await self._engine.dispose()
        self._engine = None 
        self._sessionmaker = None

    @contextlib.asynccontextmanager
    async def connect(self) -> AsyncIterator[AsyncConnection]:
        if self._engine is None:
            raise exc.CustomDatabaseException("[DB Manager] DatabaseSessionManager is not initizalized!")

        async with self._engine.begin() as connection:
            try:
                yield connection 
            except Exception as e:
                await connection.rollback()
                raise e

    @contextlib.asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        if self._sessionmaker is None:
            raise exc.CustomDatabaseException("[DB Manager] DatabaseSessionManager is not initizalized!")

        session = self._sessionmaker()
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise e 
        finally:
            await session.close() 

async def get_db_session():
    """Extenral interface for the sessionmaker. Used for dependency"""

    async with sessManagerObject.session() as session:
        yield session

async def get_engine_by_session(session: AsyncSession):
    """Gets sqlalchemy session binding"""
    engine = session.get_bind()
    return engine

    
async def wait_for_db():
    """Sends SELECT 1 to a DB and waits till response with retries"""

    retries = 0
    max_retries = 5
    wait_interval = 1
    async with sessManagerObject.session() as session:
        while retries < max_retries:
            try:
                await session.execute(text("SELECT 1"))
                logger.info("[WAIT FOR DB] SELECT 1 Executed -> Database is up and running!")
                return True
            except Exception as e:
                logger.debug(e)
                logger.info(f"[WAIT FOR DB] Database is not ready yet, retrying ({retries}/{max_retries})...")
                retries += 1
                await asyncio.sleep(3)
        logger.info(f"[WAIT FOR DB] Database is not available after all {max_retries} retries. All other components will launch regardless...")
        return False



async def init_db():
    """Creates tables using SQLModel models"""

    logger.info('[INIT DB] Creating database tables...(if needed)')
    async with sessManagerObject.connect() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


#Pass eq conditions as kwargs. Only valid fields accepted!
async def get_users(db_session: AsyncSession, **kwargs) -> ScalarResult[models.User]:
    query = select(models.User)
    for requested_field,value in kwargs.items():
        if requested_field in models.User.__fields__: #if field is valid for User model
            query = query.where(getattr(models.User,requested_field) == value)
        else:
            raise exc.CustomDatabaseException(f'"{requested_field}" field does not exist in table User')
        
    users = await db_session.scalars(query)
    return users 




################
#     REST     #
################

sessManagerObject = DatabaseSessionManager(Config.DB_URL, Config.DB_KWARGS)
DBDependency = Annotated[AsyncSession, Depends(get_db_session)]
RedisDependency = Annotated[Redis, Depends(get_redis)]