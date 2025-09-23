import abc, typing as t

SessionType = t.TypeVar("SessionType")

class IUnitOfWork(t.Generic[SessionType], abc.ABC):
    @property
    @abc.abstractmethod
    def session(self) -> SessionType: ...

    @abc.abstractmethod
    async def commit(self): ...
    
    @abc.abstractmethod
    async def rollback(self): ...

    @abc.abstractmethod
    def add_post_commit_hook(self, coro: t.Callable): ...

    @abc.abstractmethod
    async def run_hooks(self):
        '''Vital for testing, when need to you execute hooks without committing'''