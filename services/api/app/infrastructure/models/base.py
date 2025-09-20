import sqlmodel as sqlm
import sqlalchemy as sa

class VersionedBaseModel(sqlm.SQLModel):
    version: int = sqlm.Field(sa_column=sqlm.Column(sa.Integer, default=0, nullable=False))
