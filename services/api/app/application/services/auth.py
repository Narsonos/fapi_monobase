import app.application.intefraces as iapp
import app.application.security as security
import app.presentation.schemas as schemas
import typing as t

TLoginReturn = t.TypeVar("TLoginReturn")

class AuthService:
    def __init__(self, auth_strategy: iapp.AuthStrategy):
        self.auth_strategy = auth_strategy

    async def authenticate(self, credentials: dict) -> schemas.UserDTO:
        user = await self.auth_strategy.authenticate(credentials)
        return schemas.UserDTO.model_validate(user)


class LoginLogoutMixin(t.Generic[TLoginReturn]):
    async def login(self, credentials: dict) -> TLoginReturn:
        return await self.auth_strategy.login(credentials)
 
    async def logout(self, session_id: str) -> None: 
        await self.auth_strategy.logout(session_id)

class PasswordServiceMixin:
    def verify_password(self, password:str, password_hash: str) -> bool:
        return self.auth_strategy.verify_password(password, password_hash)

    def hash_password(self, password: str) -> str:
        return self.auth_strategy.hash_password(password)


class TokenServiceMixin:
    async def refresh(self, refresh_token:str) -> schemas.TokenResponse:
        return await self.auth_strategy.refresh(refresh_token)




class StatefulOAuthService(
    AuthService,
    LoginLogoutMixin[schemas.TokenResponse],
    PasswordServiceMixin,
    TokenServiceMixin
):
    """Полноценный сервис для stateful/stateful OAuth2."""


class PasswordAuthService(AuthService, PasswordServiceMixin):
    """Сервис для BasicAuth или похожих схем."""

class TokenAuthService(AuthService, TokenServiceMixin):
    """Сервис для JWT-only авторизации."""
