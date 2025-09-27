#NOTE: Only lines not covered by broader tests are tested here. (probably due to pytest-cov bugs, idk)
import pytest
from app.common.config import Config
import app.infrastructure.db.sqla_manager as sqlamgr
import app.infrastructure.exceptions as iexc
import sqlalchemy as sa

@pytest.fixture(scope='function')
def mgr():
    return sqlamgr.SQLAlchemySessionManager(Config.DB_URL, Config.DB_KWARGS)

@pytest.mark.asyncio
async def test_sqla_connect_and_close(mgr: sqlamgr.SQLAlchemySessionManager):
    async with mgr.connect() as conn:
        result = await conn.execute(sa.text("SELECT 1"))
        value = result.scalar_one() 
        assert value == 1
    
    with pytest.raises(Exception):
        async with mgr.connect() as conn:
            raise Exception()


#to avoid copypaste with pytest raises blocks...
@pytest.mark.parametrize(
    "call", 
    [
        lambda mgr: mgr.close(),
        lambda mgr: mgr.connect(),
        lambda mgr: mgr.session(),
        lambda mgr: mgr.wait_for_startup(),
        lambda mgr: mgr.initialize_data_structures(),
        lambda mgr: mgr.flush_data(),
    ]
)
@pytest.mark.asyncio
async def test_sqla_raises_when_closed(mgr: sqlamgr.SQLAlchemySessionManager, call):
    await mgr.close()
    with pytest.raises(iexc.StorageNotInitialzied):
        res = call(mgr)
        if hasattr(res, "__aenter__"):  #if async context manager
            async with res:
                pass
        else:
            await res


@pytest.mark.asyncio
async def test_sqla_sessions(mgr: sqlamgr.SQLAlchemySessionManager):
    async with mgr.session(bind=mgr._engine,autoflush=True) as sess: #to trigger the creation of a new sessionmaker
        result = await sess.execute(sa.text("SELECT 1"))
        value = result.scalar_one()   
        assert value == 1

    with pytest.raises(Exception):
        async with mgr.session(): 
            raise Exception()


@pytest.mark.asyncio
async def test_sqla_startup(mgr: sqlamgr.SQLAlchemySessionManager):
    await mgr.wait_for_startup(1,1)

    with pytest.raises(iexc.StorageBootError):
        mgr = sqlamgr.SQLAlchemySessionManager('mysql+aiomysql://user:password@127.0.0.1:3306/mydb')
        await mgr.wait_for_startup(1,1)