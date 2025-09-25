import pytest

import app.application.services as svc
import app.presentation.schemas as schemas
import app.domain.models as dmod
import app.domain.exceptions as domexc
import app.common.exceptions as appexc
from fastapi import HTTPException



@pytest.mark.asyncio
async def test_auth_service_authenticate(mocker):
	mock_strategy = mocker.AsyncMock()
	# prepare domain user returned by strategy
	domain_user = dmod.User(id=1, username='bob', role=dmod.Role.USER, status=dmod.Status.ACTIVE, password_hash='h', version=0)
	mock_strategy.authenticate.return_value = domain_user

	service = svc.AuthService(mock_strategy)
	creds = {'username': 'bob', 'password': 'secret'}
	user = await service.authenticate(creds)
	assert isinstance(user, schemas.UserDTO)
	assert user.username == 'bob'
	mock_strategy.authenticate.assert_awaited_once_with(creds)



@pytest.mark.asyncio
async def test_authenticate_raises_propagates(mocker):
	mock_strategy = mocker.AsyncMock()
	mock_strategy.authenticate.side_effect = domexc.UserDoesNotExist('no')
	service = svc.AuthService(mock_strategy)
	with pytest.raises(domexc.UserDoesNotExist):
		await service.authenticate({'username':'x','password':'y'})



@pytest.mark.asyncio
async def test_stateful_oauth_login_logout_and_refresh(mocker):
	mock_strategy = mocker.AsyncMock()
	mock_strategy.login.return_value = schemas.TokenResponse(access_token='at', refresh_token='rt', access_expires=1.0, refresh_expires=2.0)
	mock_strategy.refresh.return_value = schemas.TokenResponse(access_token='new_at', refresh_token='new_rt', access_expires=10.0, refresh_expires=20.0)

	service = svc.StatefulOAuthService(mock_strategy)

	# login
	token = await service.login({'username': 'bob', 'password': 'x'})
	assert isinstance(token, schemas.TokenResponse)
	assert token.access_token == 'at'
	mock_strategy.login.assert_awaited_once()

	# logout should delegate
	await service.logout('sess-1')
	mock_strategy.logout.assert_awaited_once_with('sess-1')

	# refresh
	new_token = await service.refresh('rt')
	assert isinstance(new_token, schemas.TokenResponse)
	assert new_token.access_token == 'new_at'
	mock_strategy.refresh.assert_awaited_once_with('rt')



@pytest.mark.asyncio
async def test_login_raises_propagates(mocker):
	mock_strategy = mocker.AsyncMock()
	mock_strategy.login.side_effect = domexc.ActionNotAllowedForRole('no')
	service = svc.StatefulOAuthService(mock_strategy)
	with pytest.raises(domexc.ActionNotAllowedForRole):
		await service.login({'username':'x','password':'y'})



@pytest.mark.asyncio
async def test_refresh_raises_propagates(mocker):
	mock_strategy = mocker.AsyncMock()
	# the real strategy raises app-level HTTP exceptions for invalid/expired tokens
	mock_strategy.refresh.side_effect = appexc.TokenExpiredException()
	service = svc.StatefulOAuthService(mock_strategy)
	with pytest.raises(HTTPException):
		await service.refresh('rt-bad')


def test_password_mixin_hash_and_verify(mocker):
	mock_strategy = mocker.MagicMock()
	mock_strategy.hash_password.return_value = 'hash:mypw'
	mock_strategy.verify_password.return_value = True

	service = svc.PasswordAuthService(mock_strategy)
	pw = 'mypw'
	hashed = service.hash_password(pw)
	assert hashed == 'hash:mypw'
	assert service.verify_password(pw, hashed) is True
	# ensure delegation was to underlying strategy
	mock_strategy.hash_password.assert_called_once_with(pw)
	mock_strategy.verify_password.assert_called_once_with(pw, hashed)


