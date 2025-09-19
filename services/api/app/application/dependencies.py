from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import typing as t

from app.infrastructure.dependencies import UserRepoDependency, SessionRepoDependency
import app.application.services as services
import app.infrastructure.security as security
import app.presentation.schemas as schemas

def get_auth_service(user_repo: UserRepoDependency, session_repo: SessionRepoDependency):
    strategy = security.StatefulOAuthStrategy(session_repo, user_repo, PasswordHasher())
    return services.StatefulOAuthService(strategy)

def get_user_service(user_repo: UserRepoDependency):
    return services.UserService(user_repo, PasswordHasher())



PasswordHasher = security.BCryptHasher
OAuthServiceDependency = t.Annotated[services.StatefulOAuthService, Depends(get_auth_service)]
OAuthFormData = t.Annotated[OAuth2PasswordRequestForm, Depends()]

OAuthToken = t.Annotated[str, Depends(OAuth2PasswordBearer(tokenUrl='/api/auth/login'))]
OAuthOptionalToken = t.Annotated[str, Depends(OAuth2PasswordBearer(tokenUrl='/api/auth/login', auto_error=False))]

async def get_current_user(token: OAuthToken, auth_service: OAuthServiceDependency):
    return await auth_service.authenticate({"token":token})

async def get_current_user_optional(token: OAuthOptionalToken, auth_service: OAuthServiceDependency):
    return await get_current_user(token, auth_service) if token else None

        
OptionalCurrentUserDependency = t.Annotated[schemas.UserDTO | None, Depends(get_current_user_optional)]
CurrentUserDependency = t.Annotated[schemas.UserDTO, Depends(get_current_user)]
UserServiceDependency = t.Annotated[services.UserService, Depends(get_user_service)]