import app.domain.models as dmod
import app.application.dependencies as adeps
import app.infrastructure.dependencies as ideps
import app.presentation.schemas as schemas
import app.application.models as amod
import app.infrastructure.security as security
from tests.helpers.tokens import OAuthTokenizer
import pytest
from tests.helpers.users import build_sess_repo,build_user_repo

@pytest.mark.asyncio
async def test_login(async_client, cache_client, uow):
    username = 'test'
    password = '123123123'

    user_repo = await build_user_repo(uow, cache_client)

    user =  await dmod.User.create(username='test', password='123123123', role='user', hasher=ideps.PasswordHasherType())
    await user_repo.create(user)
    await uow.commit()

    response = await async_client.post('/auth/login', data={'username':username, 'password':password})
    assert response.status_code == 200
    assert schemas.TokenResponse.model_validate(response.json())

@pytest.mark.asyncio
async def test_login_user_not_exists(async_client):
    response = await async_client.post('/auth/login', data={'username':'username', 'password':'password'})
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_logout(async_client, cache_client):
    session = amod.RotatingTokenSession(
        user_id=1,
        roles=['user'],
        refresh_token='sometoken'
    )

    sess_repo = await build_sess_repo(cache_client)

    await sess_repo.create(session, 3600)
    stored_session = await sess_repo.get_session(session.id)
    assert isinstance(stored_session, amod.RotatingTokenSession)
    assert stored_session.id == session.id


    hasher = ideps.PasswordHasherType()
    strat = ideps.AuthStrategyType(session_repo=None, user_repo=None, password_hasher=hasher)

    tokenizer = OAuthTokenizer(
        refresh_secret=strat.refresh_secret,
        jwt_secret=strat.jwt_secret,
        algorithm=strat.algorithm,
        access_expires_mins=strat.access_expires_mins,
        refresh_expires_hours=strat.refresh_expires_hours,
    )
    tokens = tokenizer.create_a_pair_of_tokens(payload={'session_id': session.id})

    response = await async_client.get(url='/auth/logout' ,headers={'Authorization':f'Bearer {tokens.access_token}'})
    assert response.status_code == 200

    sess_after = await sess_repo.get_session(session.id)
    assert sess_after is None


@pytest.mark.asyncio
async def test_refresh(async_client, cache_client):
    session = amod.RotatingTokenSession(
        user_id=1,
        roles=['user'],
        refresh_token='this_value_is_replaced_below'
    )

    sess_repo = await build_sess_repo(cache_client)

    hasher = ideps.PasswordHasherType()
    strat = ideps.AuthStrategyType(session_repo=None, user_repo=None, password_hasher=hasher)
    tokenizer = OAuthTokenizer(
        refresh_secret=strat.refresh_secret,
        jwt_secret=strat.jwt_secret,
        algorithm=strat.algorithm,
        access_expires_mins=strat.access_expires_mins,
        refresh_expires_hours=strat.refresh_expires_hours,
    )
    tokens = tokenizer.create_a_pair_of_tokens(payload={'session_id': session.id})
    session.refresh_token = tokens.refresh_token

    await sess_repo.create(session, 3600)
    stored_session = await sess_repo.get_session(session.id)
    assert isinstance(stored_session, amod.RotatingTokenSession)
    assert stored_session.id == session.id


    response = await async_client.get(url='/auth/refresh' ,headers={'Authorization':f'Bearer {tokens.refresh_token}'})
    assert response.status_code == 200

    tokens = schemas.TokenResponse.model_validate(response.json())
    sess_after = await sess_repo.get_session(session.id)
    assert sess_after.refresh_token == tokens.refresh_token


