from app.domain.repositories import UserRepository
import app.presentation.schemas as schemas
from app.domain.models import User
from app.domain.services import PasswordHasher

from app.domain.repositories import UserRepository
import app.presentation.schemas as schemas
from app.domain.models import User
from app.domain.services import PasswordHasher
import app.domain.exceptions as domexc

import typing as t

class UserService:

    def __init__(self, user_repo: UserRepository, password_hasher: PasswordHasher) -> None:
        self.user_repo = user_repo
        self.hasher = password_hasher

    async def create(self, user_data: schemas.PublicUserCreationModel) -> schemas.UserDTO:
        'Used by users to signup'
        user = User(
            username=user_data.username,
            password_hash=self.hasher.hash(user_data.password),
            role='user',
            status='active'
        )
        saved_user = await self.user_repo.create(user, return_result=True)
        return schemas.UserDTO.model_validate(saved_user)    

    async def admin_create(self, current_user: schemas.UserDTO, user_data: schemas.PrivateUserCreationModel) -> schemas.UserDTO:
        'Used by ADMINS to create accounts with any role'

        if not current_user.is_admin:
            raise domexc.ActionNotAllowedForRole("This action is allowed for admins only.")
        user = User(
            username=user_data.username,
            password_hash=self.hasher.hash(user_data.password),
            role=user_data.role,
            status='active'
        )
        saved_user = await self.user_repo.create(user, return_result=True)
        return schemas.UserDTO.model_validate(saved_user)
        
    async def update(self, current_user: schemas.UserDTO, edited_user: schemas.PublicUserUpdateModel):
        'Used by users to edit their profile'
        fields = edited_user.model_dump(exclude_none=True)
        if password:=fields.get("password"):
            fields["password_hash"] = self.hasher.hash(password)

        edited = await self.user_repo.update_fields(
            user_id = current_user.id,
            fields = edited_user.model_dump(exclude_unset=True)
        )
        return schemas.UserDTO.model_validate(edited)
    
    async def admin_update(self, current_user: schemas.UserDTO, target_user_id: int, edited_user: schemas.PrivateUserUpdateModel):
        if not current_user.is_admin:
            raise domexc.ActionNotAllowedForRole("This action is allowed for admins only")
        
        if current_user.id == target_user_id:
            if edited_user.role != current_user.role:
                raise domexc.ActionNotAllowedForRole("Admins are not allowed to change their own role.")

        fields = edited_user.model_dump(exclude_none=True)
        if password:=fields.get("password"):
            fields["password_hash"] = self.hasher.hash(password)

        edited = await self.user_repo.update_fields(
            user_id = target_user_id,
            fields = edited_user.model_dump(exclude_unset=True)
        )
        return schemas.UserDTO.model_validate(edited)
    

    async def list(self, limit: int = 100, offset: int = 0, filters: schemas.UserFilterSchema = None, filter_mode: t.Literal["and","or"] = "and") -> list[schemas.UserDTO]:        
        users = await self.user_repo.list(limit, offset, filters, filter_mode)
        return [schemas.UserDTO.model_validate(user) for user in users]

    async def get_user(self, user_id: int) -> schemas.UserDTO:    
        user = await self.user_repo.get_by_id(user_id)
        return schemas.UserDTO.model_validate(user) if user else None
    
    async def delete(self, current_user: schemas.UserDTO) -> None:
        await self.user_repo.delete(current_user.id)
    
    async def admin_delete(self, current_user: schemas.UserDTO, user_id: int):
        if not current_user.is_admin:
            raise domexc.ActionNotAllowedForRole("This action is allowed for admins only")
        if current_user.id == user_id:
            raise domexc.ActionNotAllowedForRole("Admins can't delete their own accounts")
        await self.user_repo.delete(user_id)

    
