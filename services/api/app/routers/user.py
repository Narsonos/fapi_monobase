#Fastapi
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

#Project files
from app.models.common import User,PrivateUserCreationModel, PublicUserCreationModel, UserLoginModel, TokenResponse, PublicUserUpdateModel, PrivateUserUpdateModel
from app.config import Config
from app.db import RedisDependency, DBDependency, get_users as fetch_users
import app.security.base as security
import app.utils.exceptions as exc

#SQLAlchemy/SQLModel
from sqlmodel import select, insert, delete
import sqlalchemy.exc as sqlexc

#Pydantic/Typing
from typing import Annotated


OAuthDependency = Annotated[str, Depends(security.oauth2)]



router = APIRouter(
    prefix="/users",
    tags = ["users"],
    responses={404: {"description": "Requested resource is not found"}}
    )

import logging
logger = logging.getLogger('app')





@router.post("/token", responses={
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



########################################
#        GETTING USER PROFILE          #
########################################


@router.get("/me")
async def whoami(current_user:security.CurrentUserDependency) -> User:
    return current_user



########################################
#             USER CRUD                #
#######################################

@router.get('/get', tags=['admin'])
async def get_users(current_user: security.CurrentUserDependency,dbsession: DBDependency, user_id=Annotated[int|None, Query(description='if None -> returns all')]) -> list[User]:
    if not current_user.role == 'admin':
        raise exc.NotAllowed()    

    q = select(User)
    if user_id is None:
        q = q.where(User.id == user_id)
    return (await dbsession.scalars(q)).all()



@router.post("/new", responses= {
    200: {"description":"Created successfully"},
    409: {"description":"User already exists"},
    403: {"description":"Returned when NON-Admin tries to create an admin account."}
    })
async def create_user(
    dbsession: DBDependency,
    signup_user: PublicUserCreationModel | PrivateUserCreationModel,
    current_user: security.OptionalCurentUserDependency #NOTE: This implies that being logged works, yet differenetly
    )  -> JSONResponse:

    #if not admin tries to create admin
    if signup_user.role == 'admin' and (not current_user or not current_user.role == 'admin'):
        raise exc.NotAllowed()

    #Find duplicates
    user = (await fetch_users(dbsession, use_and=False, username=signup_user.username)).one_or_none()
    if user:
        e = exc.UserAlreadyExistsError()
    
        #NOTE: Generate error messages here
        if user.username == signup_user.username:
            e.detail['msg'] = 'Username value violates unique constraint!'
            raise e
        
        #...Extend here...
    
    user = User(
        username=signup_user.username,
        password_hash=security.hash_password(signup_user.password),
        role=signup_user.role
    )
    try:
        dbsession.add(user)
        await dbsession.commit()
        await dbsession.refresh(user)
        return JSONResponse(status_code=200, content={"msg":"User successfully created!", "user": user.model_dump()})
    except sqlexc.IntegrityError:
        e = exc.UserAlreadyExistsError()
        e.detail['msg'] = 'The request failed due to a race condition, such user already exists. Please retry your request!'
        raise e


@router.post("/update", description="Update a user. Provide only those fields in 'edited user' that need to be changed.",responses= {
    200: {"description":"User updated"},
    403: {"description":"Invalid token"},
    403: {"description":"Returned when a regular user tries to access admin-only editable fields."},
    409: {"description":"Account with this username exists"},
    })
async def update_user(
    dbsession: DBDependency,
    edited_user: PublicUserUpdateModel | PrivateUserUpdateModel, 
    current_user: security.CurrentUserDependency,
    target_user_id: Annotated[int | None, Query(description='If admin, pass id of a user to edit. Using None edits your own profile')] = None,
    )  -> JSONResponse:


    #If not admin, you can change only your own profile
    if not current_user.role == 'admin':
        target_user = current_user
        #If not admin, can't use this model
        e = exc.NotAllowed()
        if isinstance(edited_user, PrivateUserUpdateModel):
            e.detail['msg'] = 'Passing role="admin" is not allowed for non-admin users.'
            raise e
        if target_user_id is not None:
            e.detail['msg'] = 'A non-admin user cannot pass "target_user_id" value. Please, remove the field.'
            raise e

        
    else:
        if target_user_id is None:
            target_user = current_user
        else:
            target_user = (await fetch_users(dbsession, id=target_user_id)).one_or_none()
            if not target_user:
                raise exc.UserDoesNotExist()

    #Fields that need to be pre-checked for uniqueness must be added here
    unique_to_check = {}

    #NOTE: Add common editable fields that may be edited here
    if edited_user.username:
        target_user.username = edited_user.username
        unique_to_check['username'] = edited_user.username
    
    if edited_user.password:
        target_user.password_hash = security.hash_password(edited_user.password)
    
    #NOTE: Add ADMIN-ONLY editable fields that may be edited here (edit the model too!)
    if isinstance(edited_user, PrivateUserUpdateModel):
        if edited_user.role:
            target_user.role = edited_user.role
    
    #PRE-CHECK that "edited" user does not violate unique constraints
    if unique_to_check:
        with dbsession.no_autoflush:
            confilicting_user = (await fetch_users(dbsession, use_and=False, exclude_id=target_user.id, **unique_to_check)).one_or_none()
        logger.debug(f'Conflicting user: {confilicting_user}; unique_to_check: {unique_to_check}')
        if confilicting_user:
            for field_name in unique_to_check:
                if getattr(confilicting_user,field_name) == unique_to_check[field_name]:
                    e = exc.UserAlreadyExistsError()
                    e.detail['msg'] = f'Field "{field_name}" with value "{unique_to_check[field_name]}" causes conflict in User table.'
                    raise e

    try:
        target_user = await dbsession.merge(target_user)
        await dbsession.commit()
        await dbsession.refresh(target_user)
        return JSONResponse(status_code=200, content={'msg': "User successfully updated!", "user": target_user.model_dump()})
    except sqlexc.IntegrityError: #If username violates unique constraint
        e = exc.UserAlreadyExistsError()
        e.detail['msg'] = 'One of the fields violates unique constraint.'
        raise e


@router.post('/delete', responses= {
    200: {"description":"User successfully deleted"},
    502: {"description":"Failed to delete user"},
    })
async def delete_user(
    dbsession:DBDependency,
    redis:RedisDependency,
    current_user:security.CurrentUserDependency,
    target_user_id: Annotated[int | None, Query(description='Using None deletes your own profile')] = None,
    ) -> JSONResponse:

    if current_user.role != 'admin' and target_user_id is not None and target_user_id != current_user.id:
        raise exc.NotAllowed()

    if target_user_id is None or target_user_id == current_user.id:
        target_user = current_user
    else:
        target_user = (await fetch_users(dbsession, id=target_user_id)).one_or_none()
        if not target_user:
            raise exc.UserDoesNotExist()

    if target_user.role == 'admin':
        admins = (await fetch_users(dbsession, use_and=True, role='admin')).all()
        if len(admins) <= 1:
            raise HTTPException(status_code=400, detail={"msg":"Cannot delete the last admin account"})

    cursor = 0
    keys: list[str] = []
    while True:
        cursor, batch = await redis.scan(cursor=cursor, match=f"user_session:{target_user.id}:*", count=100)
        keys.extend(batch)
        if cursor == 0:
            break

    if keys:
        async with redis.pipeline() as pipe:
            for key in keys:
                logger.debug(f'[APP] Session ...{key[:10]} of user {target_user.id} logged out')
                pipe.delete(key)  # queue delete, do not await here
            await pipe.execute()

    try:
        logger.debug(f'[APP] User({target_user.id}) is about to be deleted')
        await dbsession.execute(delete(User).where(User.id==target_user.id)) 
        await dbsession.commit()
        return JSONResponse(status_code=200, content={"msg":f"User was successfully deleted!", "deleted_user_id": target_user_id})
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=502, detail={"msg":"Failed to delete user. They might have been deleted already!"})

    





