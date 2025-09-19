#Fastapi
from fastapi import APIRouter, HTTPException, Query, Path, Body, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
#Project files
import app.application.dependencies as deps
import app.presentation.schemas as schemas
import app.domain.exceptions as domexc
import app.domain.models as dmod
#Pydantic/Typing
import typing as t
import pydantic as p


router = APIRouter(
    prefix="/users",
    tags = ["users"],
    responses={404: {"description": "Requested resource is not found"}}
    )

import logging
logger = logging.getLogger('app')


########################################
#             USER CRUD                #
########################################

@router.get('/{user_id}')
async def get_user(
        user_service: deps.UserServiceDependency,
        user_id = t.Annotated[int, Path(description='Specifies user to return')]
    ) -> schemas.UserDTO:
    '''Returns a user specified by user_id'''    
    return await user_service.get_user(user_id)
    
@router.get('')
async def get_users(
        user_service: deps.UserServiceDependency,
        limit: t.Annotated[int, Query(le=100)] = 100,
        offset: t.Annotated[int, Query()] = 0,
        filter_mode: t.Annotated[t.Literal["and","or"], Query()] = "and",
        username: str | None = Query(None),
        role: dmod.Role | None = Query(None),
        status: dmod.Status | None = Query(None)
    ) -> list[schemas.UserDTO]:
    filters = schemas.UserFilterSchema.model_validate(dict(username=username, role=role, status=status))
    return await user_service.list(limit,offset,filters,filter_mode)

@router.post("", responses= {
    200: {"description":"Created successfully"},
    409: {"description":"User already exists"},
    403: {"description":"Returned when NON-Admin accesses this endpoint"}
    })
async def create_user_for_admins(
        user_service: deps.UserServiceDependency,
        current_user: deps.CurrentUserDependency,
        new_user_data: schemas.PrivateUserCreationModel,
    ) -> schemas.UserDTO:

    try:
        return await user_service.admin_create(current_user, new_user_data)
    except domexc.UserIntegrityError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, {"error": str(e)})
    except domexc.ActionNotAllowedForRole as e:
        raise HTTPException(status.HTTP_403_FORBIDDEN, {"error": str(e)})


@router.patch("/{user_id}", description="Update a user. Provide only those fields in 'edited user' that need to be changed.",responses= {
    200: {"description":"User updated"},
    403: {"description":"Invalid token"},
    403: {"description":"Returned when a regular user tries to access admin-only editable fields."},
    409: {"description":"Account with this username exists"},
    })
async def update_user(
    user_service: deps.UserServiceDependency,
    current_user: deps.CurrentUserDependency,
    new_user_data: t.Annotated[schemas.PrivateUserUpdateModel | schemas.PublicUserUpdateModel, Body(description="Private schema is used only when ADMINS edit OTHER users. Else, use Public schema.")],
    user_id: t.Annotated[int, Path(description='id of a user to edit')],
    ) -> schemas.UserDTO:
    
    data = new_user_data.model_dump(exclude_unset=True)
    try:
        if not current_user.is_admin:
            model = schemas.PublicUserUpdateModel.model_validate(data)
            return await user_service.update(current_user, model)
        else:
            model = schemas.PrivateUserUpdateModel.model_validate(data)
            return await user_service.admin_update(current_user, user_id, model) 
    except domexc.UserDoesNotExist as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, {"error": str(e)})
    except domexc.UserIntegrityError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, {"error": str(e)})
    except domexc.ActionNotAllowedForRole as e:
        raise HTTPException(status.HTTP_403_FORBIDDEN, {"error": str(e)})
    except p.ValidationError as e:
        raise RequestValidationError(e.errors())


@router.delete('/{user_id}', responses= {
    200: {"description":"User successfully deleted"},
    502: {"description":"Failed to delete user"},
    })
async def delete_user(
    user_service: deps.UserServiceDependency,
    current_user: deps.CurrentUserDependency,
    user_id: t.Annotated[int | None, Path(description='If you are ADMIN, pass id of a user to delete. For regular users - ignored.')],
    ) -> JSONResponse:
    try:
        if current_user.is_admin:
            await user_service.admin_delete(current_user, user_id)
            return JSONResponse({"msg": "User deleted successfully"})
        else:
            await user_service.delete(current_user)
    except domexc.ActionNotAllowedForRole as e:
        raise HTTPException(status.HTTP_403_FORBIDDEN, {"error": str(e)})
    except domexc.UserDoesNotExist as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, {'error': str(e)})






