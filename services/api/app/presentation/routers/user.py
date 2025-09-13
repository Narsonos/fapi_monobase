#Fastapi
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

#Project files
import app.models.models as models
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


########################################
#             USER CRUD                #
#######################################

@router.get('/{user_id}', tags=['admin'])
async def get_users(
        current_user: security.CurrentUserDependency,
        dbsession: DBDependency,
        user_id=Annotated[int|None, Path(description='if None -> returns all')]
    ) -> list[models.User]:
    '''Returns a user specified by user_id'''

    if not current_user.role == 'admin':
        raise exc.NotAllowed()    
    return (await dbsession.scalars(select(models.User).where(models.User.id == user_id))).one_or_none()



@router.post("/", responses= {
    200: {"description":"Created successfully"},
    409: {"description":"User already exists"},
    403: {"description":"Returned when NON-Admin tries to create an admin account."}
    })
async def create_user(
        dbsession: DBDependency,
        new_user: models.PublicUserCreationModel | models.PrivateUserCreationModel,
        current_user: security.OptionalCurentUserDependency #NOTE: This implies that being logged in works, yet differenetly
    )  -> JSONResponse:

    #if not admin tries to create admin
    if new_user.role == 'admin' and (not current_user or not current_user.is_admin):
        raise exc.NotAllowed()

    #Find duplicates
    user = (await fetch_users(dbsession, use_and=False, username=new_user.username)).one_or_none()
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
        return JSONResponse({"msg":"User successfully created!", "user": user.model_dump()})
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

    





