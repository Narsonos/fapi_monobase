import typing as t
import pydantic as p
from app.domain.models import Role, Status

class UserDTO(p.BaseModel):
    id: int
    username: str
    role: Role
    status: Status
    @property
    def is_admin(self):
        return self.role == 'admin'    

class UserFilterSchema(p.BaseModel):
    id: int|None = p.Field(default=None)
    username: str|None = p.Field(default=None)
    role: Role|None = p.Field(default=None)
    status: Status|None = p.Field(default=None)

class PublicUserCreationModel(p.BaseModel):
    username: str = p.Field(min_length=3, max_length=32, description='A unique username used for logging in')
    password: str = p.Field(min_length=8, max_length=32, description='User password')

    class Config:
        extra = "forbid"

class PrivateUserCreationModel(PublicUserCreationModel):
    """This model is used for CREATING users BY ADMINS ONLY. It, in addition, allows to set a role"""
    role: Role = p.Field(description='Role identifier')


class UserLoginModel(p.BaseModel):
    username: str = p.Field(min_length=3, max_length=32)
    password: str = p.Field(min_length=8, max_length=32)

class PublicUserUpdateModel(p.BaseModel):
    username: str|None = p.Field(min_length=3, max_length=32, description="New username")
    password: str|None = p.Field(min_length=8, max_length=32, description="New password")    

    class Config:
        extra = "forbid"

    @p.field_validator('username', 'password', mode='before')
    @classmethod
    def empty_to_none(cls, v):
        if isinstance(v, str) and not v.strip():
            return None
        return v

class PrivateUserUpdateModel(PublicUserUpdateModel):
    """This model is used for UPDATING users BY ADMINS ONLY. It, in addition, allows to set a role"""
    role: Role|None = p.Field(default=None, description='Role identifier')



