import typing as t
import pydantic as p
from enum import Enum
from app.domain.services import IPasswordHasherAsync
import app.domain.exceptions as domexc

class Role(str, Enum):
    ADMIN = "admin"
    USER = "user"

class Status(str, Enum):
    ACTIVE = "active"
    DEACTIVATED = "deactivated"

class User(p.BaseModel):
    model_config = p.ConfigDict(validate_assignment=True)

    id: int|None = None
    username: str
    password_hash: str
    role: Role
    status: Status
    version: int|None = None

    @p.field_validator('username')
    def username_must_be_alphanumeric(cls,v:str):
        if not v.isalnum():
            raise domexc.UserValueError("Username must contain only numbers and letters")
        return v

    @staticmethod
    async def _hash_password(password: str, hasher: IPasswordHasherAsync):
        if len(password) < 8:
            raise domexc.UserValueError(f"Minimal password length is 8 symbols. Your length: {len(password)}")
        return await hasher.hash(password)


    @property
    def is_admin(self):
        return self.role == Role.ADMIN

    def set_status(self, status: Status):
        if not status in Status:
            raise domexc.UserValueError(f"Given status '{status}' is not a valid status!")
        self.status = status

    def set_role(self, role: Role):
        if not role in Role:
            raise domexc.UserValueError(f"Given role '{role}' is not a valid role!")
        self.role = role        
    
    @staticmethod
    async def create(username: str, password: str, role: Role, hasher: IPasswordHasherAsync):
        password_hash = await User._hash_password(password, hasher)
        return User(
            username=username.lower(),
            password_hash=password_hash,
            role=role,
            status=Status.ACTIVE
        )
    
    async def change_password(self,old:str, new:str, hasher: IPasswordHasherAsync):
        if not await hasher.verify(old, self.password_hash):
            raise domexc.UserValueError("Old password invalid")
        if await hasher.verify(new, self.password_hash):
            raise domexc.UserValueError(f'New password must not match the old one. Use different password.')
        self.password_hash = await self._hash_password(new, hasher)

    async def force_change_password(self, new: str, hasher: IPasswordHasherAsync):
        self.password_hash = await self._hash_password(new, hasher)

    

