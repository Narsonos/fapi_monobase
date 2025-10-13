from app.domain.services import IPasswordHasher, IPasswordHasherAsync
import asyncio

class AsyncHasher(IPasswordHasherAsync):
    def __init__(self, sync_hasher: IPasswordHasher):
        self._sync_hasher = sync_hasher

    async def hash(self, password: str) -> str:
        return await asyncio.to_thread(self._sync_hasher.hash, password)

    async def verify(self, password: str, password_hash: str) -> bool:
        return await asyncio.to_thread(self._sync_hasher.verify, password, password_hash)
