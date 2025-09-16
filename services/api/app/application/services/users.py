from app.domain.repositories import UserRepository
import app.presentation.schemas as schemas
from app.domain.models import User
from app.domain.services import PasswordHasher

class UserService:

    def __init__(self, user_repo: UserRepository, password_hasher: PasswordHasher) -> None:
        self.user_repo = user_repo
        self.hasher = password_hasher

    async def signup(self, user_data: schemas.PublicUserCreationModel) -> schemas.UserDTO:
        'Used by users to signup'

        user = User(
            username=user_data.username,
            password_hash=self.hasher.hash(user_data.password),
            role=user_data.role,
            status='active'
        )
        saved_user = await self.user_repo.create(user)
        return schemas.UserDTO.model_validate(saved_user)

    async def create(self, ) -> schemas.UserDTO:
        ### THIS IS WHERE I STOPPED 
        ...