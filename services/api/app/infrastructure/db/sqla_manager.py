from app.common.config import Config
import app.infrastructure.exceptions as exc
import app.infrastructure.interfaces as mgrs

import typing as t
import sqlmodel as sqlm 

from sqlalchemy.ext.asyncio import AsyncConnection,AsyncSession,async_sessionmaker,create_async_engine


import asyncio
import contextlib
import logging

logger = logging.getLogger('app.storage')






class SQLAlchemySessionManager(mgrs.SessionManagerInterface[AsyncConnection, AsyncSession]):
    """DBSessionManager - credit to: Thomas's Aitken article at Medium.com
    Spawns Async sessions and connections to a database using SQLAlchemy and ensures they're closed/rolled back properly
    """

    def __init__(self, host: str, engine_kwargs: dict[str,t.Any] = {}):
        self._engine = create_async_engine(host, **engine_kwargs)
        self._sessionmaker = async_sessionmaker(autocommit=False, bind=self._engine)

    async def close(self) -> None:
        if self._engine is None:
            raise exc.StorageNotInitialzied("[DB Manager] DatabaseSessionManager is not initizalized!")
        await self._engine.dispose()
        self._engine = None 
        self._sessionmaker = None

    @contextlib.asynccontextmanager
    async def connect(self) -> t.AsyncIterator[AsyncConnection]:
        if self._engine is None:
            raise exc.StorageNotInitialzied("[DB Manager] DatabaseSessionManager is not initizalized!")

        async with self._engine.begin() as connection:
            try:
                yield connection 
            except Exception as e:
                await connection.rollback()
                raise e

    @contextlib.asynccontextmanager
    async def session(self, **kwargs) -> t.AsyncIterator[AsyncSession]:
        if self._sessionmaker is None:
            raise exc.StorageNotInitialzied("[DB Manager] DatabaseSessionManager is not initizalized!")

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


    async def wait_for_startup(self, attempts:int = 5, interval_sec: int = 5):
        """Sends SELECT 1 to a DB and waits till response with retries"""

        retries = 0
        async with self.session() as session:
            while retries < attempts:
                try:
                    await session.execute(sqlm.text("SELECT 1"))
                    logger.info("[WAIT FOR DB] SELECT 1 Executed -> Database is up and running!")
                    return
                except Exception as e:
                    logger.debug(e)
                    logger.info(f"[WAIT FOR DB] Database is not ready yet, retrying ({retries}/{attempts})...")
                    retries += 1
                    await asyncio.sleep(interval_sec)
            logger.info(f"[WAIT FOR DB] Database is not available after all {attempts} retries. All other components will launch regardless...")
            raise exc.StorageBootError(f"Database failed to boot within {retries*interval_sec}sec!")

    async def initialize_data_structures(self):
        logger.info('[INIT DB] Configuring models for versioning...')
        async with self._engine.begin() as conn:
            await conn.run_sync(sqlm.SQLModel.metadata.create_all)

    async def flush_data(self):
        logger.info('[DB] Flush_all called -> Dropping all tables.')
        async with self._engine.begin() as conn:
            await conn.run_sync(sqlm.SQLModel.metadata.drop_all)







