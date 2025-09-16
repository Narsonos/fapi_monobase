from app.common.config import Config
import app.infrastructure.exceptions as exc
import app.infrastructure.interfaces as mgrs

import typing as t
import sqlmodel as sqlm 

from sqlalchemy.ext.asyncio import AsyncConnection,AsyncSession,async_sessionmaker,create_async_engine

import asyncio
import contextlib
import logging

logger = logging.getLogger('app.db')






class SQLAlchemySessionManager(mgrs.SessionManagerInterface[AsyncConnection, AsyncSession]):
    """DBSessionManager - credit to: Thomas's Aitken article at Medium.com
    Spawns Async sessions and connections to a database using SQLAlchemy and ensures they're closed/rolled back properly
    """

    def __init__(self, host: str, engine_kwargs: dict[str,t.Any] = {}):
        self._engine = create_async_engine(host, **engine_kwargs)
        self._sessionmaker = async_sessionmaker(autocommit=False, bind=self._engine)

    async def close(self) -> None:
        if self._engine is None:
            raise exc.CustomDatabaseException("[DB Manager] DatabaseSessionManager is not initizalized!")
        await self._engine.dispose()
        self._engine = None 
        self._sessionmaker = None

    @contextlib.asynccontextmanager
    async def connect(self) -> t.AsyncIterator[AsyncConnection]:
        if self._engine is None:
            raise exc.CustomDatabaseException("[DB Manager] DatabaseSessionManager is not initizalized!")

        async with self._engine.begin() as connection:
            try:
                yield connection 
            except Exception as e:
                await connection.rollback()
                raise e

    @contextlib.asynccontextmanager
    async def session(self, **kwargs) -> t.AsyncIterator[AsyncSession]:
        if self._sessionmaker is None:
            raise exc.CustomDatabaseException("[DB Manager] DatabaseSessionManager is not initizalized!")

        if kwargs:
            session = AsyncSession(**kwargs)
        else:
            session = self._sessionmaker()

        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise e 
        finally:
            await session.close() 

    async def get_db_session(self):
        """Extenral interface for the sessionmaker. Used for FastAPI dependency"""
        async with self.session() as session:
            yield session

    @staticmethod
    async def get_engine_by_session(session: AsyncSession):
        """Gets sqlalchemy session binding"""
        engine = session.get_bind()
        return engine

    
    async def wait_for_db(self):
        """Sends SELECT 1 to a DB and waits till response with retries"""

        retries = 0
        max_retries = Config.DB_WAIT_MAX_RETRIES
        wait_interval = Config.DB_WAIT_INTERVAL_SECONDS
        async with self.session() as session:
            while retries < max_retries:
                try:
                    await session.execute(sqlm.text("SELECT 1"))
                    logger.info("[WAIT FOR DB] SELECT 1 Executed -> Database is up and running!")
                    return True
                except Exception as e:
                    logger.debug(e)
                    logger.info(f"[WAIT FOR DB] Database is not ready yet, retrying ({retries}/{max_retries})...")
                    retries += 1
                    await asyncio.sleep(wait_interval)
            logger.info(f"[WAIT FOR DB] Database is not available after all {max_retries} retries. All other components will launch regardless...")
            return False

    async def init_db(self):
        """Creates tables using SQLModel models"""
        logger.info('[INIT DB] Creating database tables...(if needed)')
        async with self.connect() as conn:
            await conn.run_sync(sqlm.SQLModel.metadata.create_all)









