import typing as t
import pydantic as p
from enum import Enum
from app.domain.services import IPasswordHasher
import app.domain.exceptions as domexc

class Role(str, Enum):
    ADMIN = "admin"
    USER = "user"

class Status(str, Enum):
    ACTIVE = "active"
    DEACTIVATED = "deactivated"

class User(p.BaseModel):
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

    def _set_new_password(self, password: str, hasher: IPasswordHasher):
        if len(password) < 8:
            raise domexc.UserValueError(f"Minimal password length is 8 symbols. Your length: {len(password)}")
        self.password_hash = hasher.hash(password)


    @property
    def is_admin(self):
        return self.role == 'admin'

    def set_status(self, status: Role):
        self.status = status

    def set_role(self, new: Role):
        self.role = new        
    
    @staticmethod
    def create(username: str, password: str, role: Role, hasher: IPasswordHasher):
        if len(password) < 8:
            raise domexc.UserValueError(f"Minimal password length is 8 symbols. Your length: {len(password)}")

        password_hash = hasher.hash(password)
        return User(
            username=username.lower(),
            password_hash=password_hash,
            role=role,
            status=Status.ACTIVE
        )
    
    def change_password(self,old:str, new:str, hasher: IPasswordHasher):
        if not hasher.verify(old, self.password_hash):
            raise domexc.UserValueError("Old password invalid")
        if hasher.verify(new, self.password_hash):
            raise domexc.UserValueError(f'New password must not match the old one. Use different password.')
        self._set_new_password(new, hasher)

    def force_change_password(self, new: str, hasher: IPasswordHasher):
        self._set_new_password(new, hasher)

    class Config:
        validate_assignment = True

