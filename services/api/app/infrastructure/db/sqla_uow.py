import typing as t
import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession
import app.infrastructure.interfaces as iabc


class SQLAlchemyUnitOfWork(iabc.IUnitOfWork[AsyncSession]):
    def __init__(self, session: AsyncSession):
        self._session = session
        self._post_commit_hooks: list[tuple[t.Callable, asyncio.AbstractEventLoop]] = []

    @property
    def session(self):
        return self._session

    async def commit(self):
        await self._session.commit()
        await self.run_hooks()

    async def rollback(self):
        await self._session.rollback()

    def add_post_commit_hook(self, hook: t.Callable) -> None:
        '''Memorize a hook and its event loop for thread-safe execution after commit'''
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()
        self._post_commit_hooks.append((hook, loop))

    async def run_hooks(self):
        '''Runs hooks ensuring that each hook is executed in its loop'''
        current_loop = None
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            return

        logger = logging.getLogger("app.uow")
        for hook, hook_loop in self._post_commit_hooks:
            try:
                result = hook()
            except Exception as e:
                logger.exception("Post-commit hook raised when called: %s", e)
                continue

            # If hook() returned a coroutine, await or schedule it. Otherwise, treat it as sync result.
            if asyncio.iscoroutine(result):
                if hook_loop is current_loop:
                    try:
                        await result
                    except Exception:
                        logger.exception("Exception while executing post-commit coroutine hook")
                else:
                    try:
                        fut = asyncio.run_coroutine_threadsafe(result, hook_loop)
                        await asyncio.wrap_future(fut)
                    except Exception:
                        logger.exception("Exception while scheduling post-commit coroutine on original loop")
            else:
                continue
        self._post_commit_hooks.clear()

