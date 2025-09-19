import app.domain.repositories as repos
import app.presentation.schemas as schemas
import app.domain.models as domain
import app.domain.services as services
import app.domain.exceptions as domexc

import typing as t
import logging

logger = logging.getLogger('app')

class UserService:

    def __init__(self, user_repo: repos.IUserRepository, password_hasher: services.IPasswordHasher) -> None:
        self.user_repo = user_repo
        self.hasher = password_hasher

    def _clean_fields_update_dict(self, fields: dict[str, t.Any]):
        if password:=fields.get("password"):
            fields["password_hash"] = self.hasher.hash(password)
            del fields["password"]


    async def create(self, user_data: schemas.PublicUserCreationModel) -> schemas.UserDTO:
        'Used by users to signup'
        user = domain.User.create(
            username=user_data.username,
            password=user_data.password,
            role='user',
            status='active',
            hasher=self.hasher
        )
        saved_user = await self.user_repo.save(user)
        return schemas.UserDTO.model_validate(saved_user, from_attributes=True)    

    async def admin_create(self, current_user: schemas.UserDTO, user_data: schemas.PrivateUserCreationModel) -> schemas.UserDTO:
        'Used by ADMINS to create accounts with any role'
        if not current_user.is_admin:
            raise domexc.ActionNotAllowedForRole("This action is allowed for admins only.")
        
        user = domain.User.create(
            username=user_data.username,
            password=self.hasher.hash(user_data.password),
            role=user_data.role,
            status='active',
            hasher=self.hasher
        )
        saved_user = await self.user_repo.save(user)
        return schemas.UserDTO.model_validate(saved_user, from_attributes=True)
        
    async def update(self, current_user: schemas.UserDTO, edited_user: schemas.PublicUserUpdateModel):
        'Used by users to edit their profile'
        current_user: domain.User = await self.user_repo.get_by_id(current_user.id)

        if edited_user.username:
            current_user.username = edited_user.username
        
        if (edited_user.old_password or edited_user.new_password):
            if not (edited_user.old_password and edited_user.new_password):
                raise domexc.UserValueError("Either both password fields must be provided, or no password fields at all.")
            current_user.change_password(old = edited_user.old_password, new = edited_user.new_password, hasher = self.hasher)

        current_user = await self.user_repo.update(current_user)
        return schemas.UserDTO.model_validate(current_user, from_attributes=True)
    
    async def admin_update(self, current_user: schemas.UserDTO, target_user_id: int, edited_user: schemas.PrivateUserUpdateModel):
        if not current_user.is_admin:
            raise domexc.ActionNotAllowedForRole("This action is allowed for admins only")
        
        if current_user.id == target_user_id:
            if edited_user.role and edited_user.role != current_user.role:
                raise domexc.ActionNotAllowedForRole("Admins are not allowed to change their own role.")
            if edited_user.status==domain.Status.DEACTIVATED:
                raise domexc.ActionNotAllowedForRole("Admins cannot deactivate their own account")
        
        target_user = await self.user_repo.get_by_id(target_user_id)
        if not target_user:
            raise domexc.UserDoesNotExist("User with the provided ID does not exist")
        
        if edited_user.username:
            target_user.username = edited_user.username

        if edited_user.new_password:
            target_user.force_change_password(edited_user.new_password, hasher=self.hasher)

        if edited_user.role:
            target_user.set_role(edited_user.role)
        
        if edited_user.status:
            target_user.set_status(edited_user.status)


        edited = await self.user_repo.update(target_user)
        return schemas.UserDTO.model_validate(edited, from_attributes=True)
    

    async def list(self, limit: int = 100, offset: int = 0, filters: schemas.UserFilterSchema = None, filter_mode: t.Literal["and","or"] = "and") -> list[schemas.UserDTO]:        
        users = await self.user_repo.list(limit, offset, filters, filter_mode)
        return [schemas.UserDTO.model_validate(user, from_attributes=True) for user in users]

    async def get_user(self, user_id: int) -> schemas.UserDTO:    
        user = await self.user_repo.get_by_id(user_id)
        return schemas.UserDTO.model_validate(user, from_attributes=True) if user else None
    
    async def delete(self, current_user: schemas.UserDTO) -> None:
        await self.user_repo.delete(current_user.id)
    
    async def admin_delete(self, current_user: schemas.UserDTO, user_id: int):
        if not current_user.is_admin:
            raise domexc.ActionNotAllowedForRole("This action is allowed for admins only")
        if current_user.id == user_id:
            raise domexc.ActionNotAllowedForRole("Admins can't delete their own accounts")
        target_user = await self.user_repo.get_by_id(user_id)
        if not target_user:
            raise domexc.UserDoesNotExist("User with the provided ID does not exist")
        await self.user_repo.delete(target_user)

    
