import app.application.dependencies as adeps
import app.infrastructure.dependencies as ideps
import app.domain.models as dmod
import app.presentation.schemas as schemas
import pytest
import pytest_asyncio as pytestaio
from tests.integration.conftest import build_sess_repo, build_user_repo

username, password = 'admin', 'password'




async def create_user(user_repo, uow):
    user = dmod.User.create(
        username=username,
        password=password,
        role='admin',
        hasher=ideps.PasswordHasherType(),
    )
    await user_repo.create(user)
    await uow.commit()


async def valid_admin_tokens(user_repo, sess_repo):
    username, password = 'admin', 'password'
    auth_start = ideps.AuthStrategyType(user_repo=user_repo, session_repo=sess_repo, password_hasher=ideps.PasswordHasherType())
    tokens = await auth_start.login(dict(username=username, password=password))
    return tokens


@pytest.mark.asyncio
async def test_get_user(async_client, uow, cache_client):
    user_repo = await build_user_repo(uow, cache_client)
    await create_user(user_repo, uow)

    response = await async_client.get('/users/1')
    assert response.status_code == 200
    assert schemas.UserDTO.model_validate(response.json())


    