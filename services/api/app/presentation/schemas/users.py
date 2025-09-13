import sqlmodel as sqlm
import typing as t
import pydantic as p

class PublicUserCreationModel(sqlm.SQLModel):
    username: str = sqlm.Field(min_length=3, max_length=32, description='A unique username used for logging in')
    password: str = sqlm.Field(min_length=8, max_length=32, description='User password')
    role: t.Literal["user"] = sqlm.Field(default="user", description="Role identifier")

    class Config:
        extra = "forbid"

class PrivateUserCreationModel(PublicUserCreationModel):
    """This model is used for CREATING users BY ADMINS ONLY. It, in addition, allows to set a role"""
    role: t.Literal["user", "admin"] = sqlm.Field(description='Role identifier')


class UserLoginModel(sqlm.SQLModel):
    username: str = sqlm.Field(min_length=3, max_length=32)
    password: str = sqlm.Field(min_length=8, max_length=32)

class PublicUserUpdateModel(sqlm.SQLModel):
    username: str|None = sqlm.Field(min_length=3, max_length=32, description="New username")
    password: str|None = sqlm.Field(min_length=8, max_length=32, description="New password")    

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
    role: t.Literal["user", "admin"]|None = sqlm.Field(default=None, description='Role identifier')