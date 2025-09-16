import pydantic as p, uuid

class UserSession(p.BaseModel):
    id: str = p.Field(default_factory=lambda: uuid.uuid4())
    user_id: int
    roles: list[str]

class RotatingTokenSession(UserSession):
    refresh_token: str