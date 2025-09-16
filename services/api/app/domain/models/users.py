import typing as t
import pydantic as p


class User(p.BaseModel):
    id: int|None = None
    username: str
    password_hash: str
    role: t.Literal["user","admin"]
    status: t.Literal["active","inactive"]

    @property
    def is_admin(self):
        return self.role == 'admin'
