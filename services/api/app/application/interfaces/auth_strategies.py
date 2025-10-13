from abc import ABC, abstractmethod
from app.domain.models import User
from app.domain.services import IPasswordHasherAsync
import app.presentation.schemas as schemas
import typing as t


class IAuthStrategy(ABC):
    @abstractmethod
    async def authenticate(self, credentials: str, **kwargs) -> User:
        """Takes in credentials, validates them and does not create a session. Returns a User."""


class ILoginLogoutMixin(ABC):
    @abstractmethod
    async def login(self, credentials: dict) -> t.Any:
        """Validate credentials and optionally create access/session"""
        ...

    @abstractmethod
    async def logout(self, credentials: t.Any) -> None:
        """Retract granted access"""
        ...

class IPasswordMixin(ABC):
    @property
    @abstractmethod
    def hasher(self) -> IPasswordHasherAsync:
        return self.hasher

    async def hash_password(self, password: str) -> str:
        return await self.hasher.hash(password)

    async def verify_password(self, password: str, password_hash: str) -> bool:
        return await self.hasher.verify(password, password_hash)

class ITokenMixin(ABC):
    @abstractmethod
    async def refresh(self, refresh_token: str) -> schemas.TokenResponse: ...
