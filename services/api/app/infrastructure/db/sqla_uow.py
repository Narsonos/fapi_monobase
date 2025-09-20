import typing as t
from sqlalchemy.ext.asyncio import AsyncSession
import app.infrastructure.interfaces as iabc


class SQLAlchemyUnitOfWork(iabc.IUnitOfWork[AsyncSession]):
    def __init__(self, session: AsyncSession):
        self._session = session
        self._post_commit_hooks: list[t.Callable] = []
    
    @property
    def session(self):
        return self._session

    async def commit(self):
        await self._session.commit()
        for hook in self._post_commit_hooks:
            await hook()

    async def rollback(self):
        await self._session.rollback()

    def add_post_commit_hook(self, hook: t.Callable) -> None:
        self._post_commit_hooks.append(hook)
    

        