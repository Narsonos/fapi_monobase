import app.application.dependencies as adeps
import app.infrastructure.dependencies as ideps
import app.domain.models as dmod
import app.presentation.schemas as schemas
import pytest

username, password = 'admin', 'password'


async def get_user_repo(cache, uow):
    cache_client = await cache.connect()
    db = ideps.UserDB(uow.session)
    user_repo = ideps.UserRepoDependency(user_db_repo=db, connection=cache_client, uow=uow)
    return user_repo


async def get_sess_repo(cache):
    cache_client = await cache.connect()
    sess_repo = ideps.SessionRepository(cache_client)
    return sess_repo


async def create_user(uow, user_repo: ideps.UserRepository):
    user = dmod.User.create(
        username=username,
        password=password,
        role='admin',
        hasher=ideps.PasswordHasherType()
    )
    await user_repo.create(user)
    await uow.commit()


@pytest.fixture
async def valid_admin_tokens(user_repo: ideps.UserRepository, sess_repo: ideps.SessionRepository):
    username, password = 'admin', 'password'
    auth_start = ideps.AuthStrategyType(user_repo=user_repo, session_repo=sess_repo, password_hasher=ideps.PasswordHasherType())
    tokens = await auth_start.login(dict(username=username, password=password))
    return tokens
    



async def test_get_user(async_client, cache, uow):
    user_repo = await get_user_repo(cache, uow)
    sess_repo = await get_sess_repo(cache)
    await create_user(uow, user_repo)

    response = await async_client.get('/users/1')
    assert response.status_code == 200
    assert schemas.UserDTO.model_validate(response.json())


    