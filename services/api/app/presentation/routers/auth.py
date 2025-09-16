#Fastapi
from fastapi import APIRouter
from fastapi.responses import JSONResponse

#Project files
from app.presentation.schemas import UserLoginModel, TokenResponse
from app.common.config import Config
from app.application.dependencies import OAuthService, OAuthFormData, OAuthToken

import app.common.exceptions as exc

#Pydantic/Typing
import typing as t
import logging

logger = logging.getLogger('app')
router = APIRouter(
    prefix="",
    tags = ["auth"],
    responses={404: {"description": "Requested resource is not found"}}
    )




@router.post("/login", responses={
    401: {"description":"Bad credentials"},
    422: {"description":"Form data has bad format (PydanticValidation)"},
    },
    description='If credentials are valid - returns a pair of tokens, each can be used in Authorization header as "Bearer [token]"')
async def login(auth_service: OAuthService, form_data: OAuthFormData) -> TokenResponse:
    credentials = {"username": form_data.username, "password": form_data.password}
    result = await auth_service.login(credentials)
    return result


@router.get("/logout", description='Invalidates your token')
async def logout(auth_service: OAuthService, token: OAuthToken) -> JSONResponse:
    credentials = {"token": token}
    await auth_service.logout(credentials)
    return JSONResponse({"msg":"Logged out successfully!"})


@router.post("/refresh", responses={401: {"description":"Logged out or expired/wrong token"}},description='Send refresh token in Authorization header as "Bearer [token]"')
async def refresh(auth_service: OAuthService, token: OAuthToken) -> TokenResponse:
    tokens = await auth_service.refresh(refresh_token=token)
    return tokens


