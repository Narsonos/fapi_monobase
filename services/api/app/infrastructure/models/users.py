import sqlmodel as sqlm
import sqlalchemy as sa
import typing as t
import app.infrastructure.models.base as base
import app.domain.models as dmod

class User(base.VersionedBaseModel, table=True):
    __tablename__ = '__users__'
    id: int | None = sqlm.Field(default=None, primary_key=True, description='Integer user identifier')
    username: str = sqlm.Field(unique=True, min_length=3, max_length=32, description='A unique username used for logging in')
    password_hash : str = sqlm.Field(description='A hashed password')
    role: dmod.Role = sqlm.Field(default=dmod.Role.USER, sa_type=sa.String(20), description='Role identifier')
    status: dmod.Status = sqlm.Field(default=dmod.Status.ACTIVE, sa_type=sa.String(20), description='Turn on/off a user')



