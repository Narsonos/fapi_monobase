from abc import abstractmethod, ABC
import app.domain.models.users as domain
import app.presentation.schemas as schemas
import typing as t

class IUserRepository(ABC):
    """Abstract base for UserRepository. Specific implementations must inherit this base class."""

    @abstractmethod
    async def get_by_id(self, user_id: int) -> domain.User | None: ...

    @abstractmethod
    async def get_by_username(self, username: str) -> domain.User | None: ...

    @abstractmethod
    async def list(self, limit: int = 100, offset: int = 0, filters: schemas.UserFilterSchema = None, filter_mode: t.Literal["and","or"] = "and") -> list[domain.User]: ...
    
    @abstractmethod
    async def create(self, user: domain.User) -> domain.User: ...

    @abstractmethod
    async def update(self, user: domain.User) -> domain.User: ...

    @abstractmethod
    async def delete(self, user: domain.User) -> None: ...

    @abstractmethod
    async def ensure_admin_exists(self) -> None: ...
