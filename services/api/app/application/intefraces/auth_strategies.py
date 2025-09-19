from abc import ABC, abstractmethod
from app.domain.models import User
from app.domain.services import IPasswordHasher
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
    def hasher(self) -> IPasswordHasher:
        return self.hasher

    def hash_password(self, password: str) -> str:
        return self.hasher.hash(password)

    def verify_password(self, password: str, password_hash: str) -> bool:
        return self.hasher.verify(password, password_hash)

class ITokenMixin(ABC):
    @abstractmethod
    async def refresh(self, refresh_token: str) -> schemas.TokenResponse: ...
