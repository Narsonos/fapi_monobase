import pydantic as p

class TokenResponse(p.BaseModel):
    access_token: str
    refresh_token: str
    access_expires: int
    refresh_expires: int