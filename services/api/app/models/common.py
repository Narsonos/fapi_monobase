from sqlmodel import Field, SQLModel, Relationship, String, UniqueConstraint, select
from typing import Optional, Literal, List
from sqlmodel import Column, Text, JSON
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils import exceptions as exc
from pydantic import field_validator




class User(SQLModel, table=True):
    __tablename__ = '__users__'
    id: int | None = Field(default=None, primary_key=True, description='Integer user identifier')
    username: str = Field(unique=True, min_length=3, max_length=32, description='A unique username used for logging in')
    password_hash : str = Field(description='A hashed password')
    role: Literal["user","admin"] = Field(default="user", sa_type=String(10), description='Role identifier')
    status: Literal["active","inactive"] = Field(default='active', sa_type=String(10), description='Turn on/off a user')


class Token(SQLModel):
    token: str
    token_type: str

class TokenResponse(SQLModel):
    access_token: str
    refresh_token: str
    token_type: str

class PublicUserCreationModel(SQLModel):
    username: str = Field(min_length=3, max_length=32, description='A unique username used for logging in')
    password: str = Field(min_length=8, max_length=32, description='User password')
    role: Literal["user"] = Field(default="user", description="Role identifier")

    class Config:
        extra = "forbid"

class PrivateUserCreationModel(PublicUserCreationModel):
    """This model is used for CREATING users BY ADMINS ONLY. It, in addition, allows to set a role"""
    role: Literal["user", "admin"] = Field(description='Role identifier')


class UserLoginModel(SQLModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=32)

class PublicUserUpdateModel(SQLModel):
    username: str|None = Field(min_length=3, max_length=32, description="New username")
    password: str|None = Field(min_length=8, max_length=32, description="New password")    

    class Config:
        extra = "forbid"

    @field_validator('username', 'password', mode='before')
    @classmethod
    def empty_to_none(cls, v):
        if isinstance(v, str) and not v.strip():
            return None
        return v

class PrivateUserUpdateModel(PublicUserUpdateModel):
    """This model is used for UPDATING users BY ADMINS ONLY. It, in addition, allows to set a role"""
    role: Literal["user", "admin"]|None = Field(default=None, description='Role identifier')