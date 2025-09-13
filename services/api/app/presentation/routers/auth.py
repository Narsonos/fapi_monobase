#Fastapi
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

#Project files
from app.models.models import UserLoginModel, TokenResponse
from app.config import Config
from app.db import RedisDependency, DBDependency
import app.security.base as security
import app.utils.exceptions as exc

#Pydantic/Typing
from typing import Annotated
import logging

logger = logging.getLogger('app')
OAuthDependency = Annotated[str, Depends(security.oauth2)]

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
async def login(dbsession: DBDependency, redis: RedisDependency, form_data: Annotated[OAuth2PasswordRequestForm,Depends()]) -> TokenResponse:
    given_user = UserLoginModel(username=form_data.username,password=form_data.password)
    user = await security.authenticate_user(dbsession, given_user)
    if not user:
        raise exc.CredentialsException()

    
    access_token, refresh_token, session_id = security.create_access_and_refresh(user_id=user.id, return_session_id=True)
    #Here we're gonna load user and load session - the sessions and cached_users are separate One to Many
    user_session_key = f"user_session:{user.id}:{session_id}" #One record per SESSION
    await redis.hset(user_session_key, mapping={"access_token":access_token,"refresh_token":refresh_token})
    await redis.hexpire(user_session_key, Config.ACCESS_TOKEN_EXPIRE_MINUTES*60, 'access_token')
    await redis.expire(user_session_key, Config.REFRESH_TOKEN_EXPIRE_HOURS*3600)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token,token_type="bearer")



@router.get("/logout", description='Invalidates your token')
async def logout(token_data: OAuthDependency, redis: RedisDependency) -> JSONResponse:
    user_id, session_id = await security.exctract_token_data(token_data) 
    await redis.delete(f"user_session:{user_id}:{session_id}") #delete session from "session" storage
    return JSONResponse(status_code=200, content={"msg":"Token successfully deactivated!"})


@router.post("/refresh", responses={401: {"description":"Logged out or expired/wrong token"}},description='Send refresh token in Authorization header as "Bearer [token]"')
async def refresh(refresh_token: OAuthDependency, redis: RedisDependency) -> TokenResponse:
    logger.info(f'[REFRESH] Token = {refresh_token}')
    user_id,session_id = await security.exctract_token_data(refresh_token, refresh=True) 
    user_data = await redis.hgetall(f"user_session:{user_id}:{session_id}")
    logger.info(f'[HGETALL DATA of key user:{user_id}:{session_id}] = {user_data}')
    #If user in redis - refresh tokens
    if user_data.get("refresh_token") == refresh_token:
        access_token, refresh_token = security.create_access_and_refresh(user_id=user_id, session_id=session_id)
        user_session_key = f"user_session:{user_id}:{session_id}"
        await redis.hset(user_session_key, mapping={
            'access_token':access_token,
            'refresh_token':refresh_token
            })
        await redis.hexpire(user_session_key, Config.ACCESS_TOKEN_EXPIRE_MINUTES*60, 'access_token')
        await redis.expire(user_session_key, Config.REFRESH_TOKEN_EXPIRE_HOURS)
        #Return renewed tokens
        return TokenResponse(access_token=access_token, refresh_token=refresh_token,token_type="bearer")

    #Else user is considered logged out (bc they're not in redis)
    raise exc.LoggedOutException()