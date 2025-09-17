import typing as t
import pydantic as p
from enum import Enum

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

    @property
    def is_admin(self):
        return self.role == 'admin'


