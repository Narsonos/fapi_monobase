class FakeHasher:
    def hash(self, password: str) -> str:
        return f"hashed:{password}"

    def verify(self, password: str, hashed: str) -> bool:
        return hashed == f"hashed:{password}"


class AsyncHasherAdapter:
    def __init__(self, sync_hasher: FakeHasher):
        self._sync = sync_hasher

    async def hash(self, password: str) -> str:
        return self._sync.hash(password)

    async def verify(self, password: str, hashed: str) -> bool:
        return self._sync.verify(password, hashed)