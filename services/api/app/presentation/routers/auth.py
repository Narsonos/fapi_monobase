#Fastapi
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

#Project files
import app.presentation.schemas as schemas
import app.application.dependencies as appdeps
import app.domain.exceptions as domexc, app.application.exceptions as appexc, app.common.exceptions as exc

#Pydantic/Typing
import typing as t
import logging

logger = logging.getLogger('app')
router = APIRouter(
    prefix="/auth",
    tags = ["auth"],
    responses={404: {"description": "Requested resource is not found"}}
    )




@router.post("/login", responses={
    401: {"description":"Bad credentials"},
    422: {"description":"Form data has bad format (PydanticValidation)"},
    },
    description='If credentials are valid - returns a pair of tokens, each can be used in Authorization header as "Bearer [token]"')
async def login(auth_service: appdeps.OAuthServiceDependency, form_data: appdeps.OAuthFormData) -> schemas.TokenResponse:
    credentials = {"username": form_data.username, "password": form_data.password}
    try:
        tokens = await auth_service.login(credentials)
    except appexc.CredentialsException as e:
        raise e    
    return tokens
        


@router.get("/logout", description='Invalidates your token')
async def logout(auth_service: appdeps.OAuthServiceDependency, token: appdeps.OAuthToken) -> JSONResponse:
    credentials = {"token": token}
    await auth_service.logout(credentials)
    return JSONResponse({"msg":"Logged out successfully!"})


@router.get("/refresh", responses={401: {"description":"Logged out or expired/wrong token"}},description='Send refresh token in Authorization header as "Bearer [token]"')
async def refresh(auth_service: appdeps.OAuthServiceDependency, token: appdeps.OAuthToken) -> schemas.TokenResponse:
    tokens = await auth_service.refresh(refresh_token=token)
    return tokens


