from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import typing as t

from app.infrastructure.dependencies import DatabaseDependency, CacheDependency, UserRepository, SessionRepository, UserDB
from app.application.services import StatefulOAuthService
from app.application.security import StatefulOAuthStrategy, BCryptHasher


def get_auth_service(dbsession: DatabaseDependency, cache: CacheDependency) -> StatefulOAuthService:
    user_db = UserDB(session=dbsession)
    user_repo = UserRepository(user_db, cache)
    session_repo = SessionRepository(cache)
    password_hasher = PasswordHasher()
    strategy = StatefulOAuthStrategy(session_repo, user_repo, password_hasher)
    return StatefulOAuthService(strategy)

PasswordHasher = BCryptHasher
OAuthService = t.Annotated[StatefulOAuthService, Depends(get_auth_service)]
OAuthFormData = t.Annotated[OAuth2PasswordRequestForm, Depends()]
OAuthToken = t.Annotated[OAuth2PasswordBearer, Depends(OAuth2PasswordBearer(tokenUrl='/login'))]