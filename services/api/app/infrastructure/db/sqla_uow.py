import typing as t
import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession
import app.infrastructure.interfaces as iabc

logger = logging.getLogger('app')

class SQLAlchemyUnitOfWork(iabc.IUnitOfWork[AsyncSession]):
    def __init__(self, session: AsyncSession):
        self._session = session
        self._post_commit_hooks: list[t.Callable[[], t.Awaitable[t.Any]]] = []

    @property
    def session(self) -> AsyncSession:
        return self._session

    async def commit(self) -> None:
        await self._session.commit()
        await self.run_hooks()

    async def rollback(self) -> None:
        await self._session.rollback()

    def add_post_commit_hook(self, hook: t.Callable[[], t.Awaitable[t.Any]]) -> None:
        self._post_commit_hooks.append(hook)

    async def run_hooks(self) -> None:
        if not self._post_commit_hooks:
            return

        for hook_factory in self._post_commit_hooks:
            try:
                hook_coroutine = hook_factory()
                await hook_coroutine
            except Exception as e:
                logger.exception(f"[UoW] Exception while executing post-commit hook. Exception: {e}")

        self._post_commit_hooks.clear()
