from app.domain.services import IPasswordHasher
import bcrypt, asyncio


class BCryptHasher(IPasswordHasher):
    def hash(self, password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4)).decode()

    def verify(self, password: str, password_hash: str) -> bool:
        return bcrypt.checkpw(password.encode(), password_hash.encode())


