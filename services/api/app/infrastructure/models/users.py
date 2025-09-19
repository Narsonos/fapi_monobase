import sqlmodel as sqlm
import sqlalchemy as sa
import typing as t
import app.infrastructure.models.base as base

class User(base.VersionedBaseModel, table=True):
    __tablename__ = '__users__'
    id: int | None = sqlm.Field(default=None, primary_key=True, description='Integer user identifier')
    username: str = sqlm.Field(unique=True, min_length=3, max_length=32, description='A unique username used for logging in')
    password_hash : str = sqlm.Field(description='A hashed password')
    role: t.Literal["user","admin"] = sqlm.Field(default="user", sa_type=sa.String(10), description='Role identifier')
    status: t.Literal["active","inactive"] = sqlm.Field(default='active', sa_type=sa.String(10), description='Turn on/off a user')



