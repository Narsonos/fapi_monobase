from abc import abstractmethod, ABC
import app.domain.models.users as m
import app.presentation.schemas as schemas
import typing as t

class UserRepository(ABC):
    """Abstract base for UserRepository. Specific implementations must inherit this base class."""

    @abstractmethod
    async def get_by_id(self, user_id: int) -> m.User | None: ...

    @abstractmethod
    async def get_by_username(self, username: str) -> m.User | None: ...

    @abstractmethod
    async def list(self, limit: int = 100, offset: int = 0, filters: schemas.UserFilterSchema = None, filter_mode: t.Literal["and","or"] = "and") -> list[m.User]: ...
    
    @abstractmethod
    async def create(self, user: m.User, return_result:bool = True) -> m.User | None: ...

    @abstractmethod
    async def update(self, user: m.User, return_result:bool = True) -> m.User | None: ...

    @abstractmethod
    async def update_fields(self, user_id:int, fields: dict[str, t.Any], return_result:bool = True) -> m.User | None: ...

    @abstractmethod
    async def delete(self, user_id: int) -> None: ...

    @abstractmethod
    async def ensure_admin_exists(self) -> None: ...
