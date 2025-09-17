from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import typing as t

from app.infrastructure.dependencies import UserRepoDependency, SessionRepoDependency
from app.application.services import StatefulOAuthService, UserService
from app.application.security import StatefulOAuthStrategy, BCryptHasher
import app.presentation.schemas as schemas

def get_auth_service(user_repo: UserRepoDependency, session_repo: SessionRepoDependency):
    strategy = StatefulOAuthStrategy(session_repo, user_repo, PasswordHasher())
    return StatefulOAuthService(strategy)

def get_user_service(user_repo: UserRepoDependency):
    return UserService(user_repo, PasswordHasher())



PasswordHasher = BCryptHasher
OAuthServiceDependency = t.Annotated[StatefulOAuthService, Depends(get_auth_service)]
OAuthFormData = t.Annotated[OAuth2PasswordRequestForm, Depends()]

OAuthToken = t.Annotated[str, Depends(OAuth2PasswordBearer(tokenUrl='/login'))]
OAuthOptionalToken = t.Annotated[str, Depends(OAuth2PasswordBearer(tokenUrl='/login', auto_error=False))]

async def get_current_user(token: OAuthToken, auth_service: OAuthServiceDependency):
    return await auth_service.authenticate({"token":token})

async def get_current_user_optional(token: OAuthOptionalToken, auth_service: OAuthServiceDependency):
    return await get_current_user(token, auth_service) if token else None

        
OptionalCurrentUserDependency = t.Annotated[schemas.UserDTO | None, Depends(get_current_user_optional)]
CurrentUserDependency = t.Annotated[schemas.UserDTO, Depends(get_current_user)]
UserServiceDependency = t.Annotated[UserService, Depends(get_user_service)]