from abc import ABC, abstractmethod

class PasswordHasher(ABC):
    @abstractmethod
    def hash(self, password: str) -> str: ...
    
    @abstractmethod
    def verify(self, password: str, password_hash: str) -> bool: ...