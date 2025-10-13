from abc import ABC, abstractmethod

class IPasswordHasher(ABC):
    @abstractmethod
    def hash(self, password: str) -> str: ...
    
    @abstractmethod
    def verify(self, password: str, password_hash: str) -> bool: ...


class IPasswordHasherAsync(ABC):
    @abstractmethod
    async def hash(self, password: str) -> str: ...
    
    @abstractmethod
    async def verify(self, password: str, password_hash: str) -> bool: ...