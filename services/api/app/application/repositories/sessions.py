from abc import abstractmethod, ABC
import typing as t
import app.application.models as m

class SessionRepository(ABC):
    
    @abstractmethod
    async def create(self, session: m.UserSession, ttl: int) -> None: ...

    @abstractmethod
    async def delete(self, session_id: str) -> None: ...

    @abstractmethod
    async def get_session(self, session_id: str) -> m.UserSession | None: ...

    @abstractmethod
    async def refresh(self, session_id: str, ttl: int) -> None: ...