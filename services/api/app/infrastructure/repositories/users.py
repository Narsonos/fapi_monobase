import app.domain.repositories as repo
import app.domain.models as m
import app.domain.exceptions as e

from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy.exc as sqlexc
import sqlmodel as sqlm
import typing as t

class MySQLUserRepository(repo.UserRepository):
    """Repository implementation for User model using MySQL via SQLAlchemy AsyncSession.

    This class handles CRUD operations for users and converts database-specific
    integrity errors into domain-level exceptions.
    """

    def __init__(self, session: AsyncSession):
        """Initialize the repository with an asynchronous SQLAlchemy session.

        Args:
            session (AsyncSession): An active SQLAlchemy async session.
        """
        self.session = session

    def _handle_integrity_error(self, error: sqlexc.IntegrityError):
        """Handle SQLAlchemy IntegrityError and convert it into a domain exception.

        Currently checks for duplicate username errors and raises `UserAlreadyExists`.

        Args:
            error (IntegrityError): The caught SQLAlchemy integrity error.

        Raises:
            UserAlreadyExists: If the error is caused by a duplicate username.
            IntegrityError: Re-raises other integrity errors not handled explicitly.
        """
        if error.orig.args and len(error.orig.args) > 1:
            error_code, msg = error.orig.args
            if error_code == 1062 and 'username' in msg:
                raise e.UserAlreadyExists(f"Another user with this username already exists") from error
        raise error

    async def get_by_id(self, user_id: int) -> m.User | None:
        """Retrieve a user by their unique ID.

        Args:
            user_id (int): The ID of the user to retrieve.

        Returns:
            User | None: The user object if found, else None.
        """
        return (await self.session.scalars(
            sqlm.select(m.User).where(m.User.id == user_id)
        )).one_or_none()

    async def get_by_username(self, username: str) -> m.User | None:
        """Retrieve a user by their unique username.

        Args:
            username (str): The username to search for.

        Returns:
            User | None: The user object if found, else None.
        """
        return (await self.session.scalars(
            sqlm.select(m.User).where(m.User.username == username)
        )).one_or_none()

    async def list(self) -> list[m.User]:
        """Retrieve all users in the system.

        Returns:
            list[User]: List of all users.
        """
        return (await self.session.scalars(sqlm.select(m.User))).all()

    async def create(self, user: m.User, return_result: bool = True) -> m.User | None:
        """Create a new user in the database.

        Args:
            user (User): The user object to create.
            return_result (bool, optional): Whether to refresh and return the created user. Defaults to True.

        Returns:
            User | None: The created user if `return_result` is True, else None.

        Raises:
            UserAlreadyExists: If a user with the same username already exists.
        """
        try:
            self.session.add(user)
            await self.session.commit()
            if return_result: 
                await self.session.refresh(user)
                return user
        except sqlexc.IntegrityError as error:
            self._handle_integrity_error(error)

    async def update(self, user: m.User, return_result: bool = True) -> m.User | None:
        """Update an existing user by merging changes.

        Args:
            user (User): The user object with updated fields. Must have a valid ID.
            return_result (bool, optional): Whether to refresh and return the updated user. Defaults to True.

        Returns:
            User | None: The updated user if `return_result` is True, else None.

        Raises:
            UserDoesNotExist: If no user with the given ID exists.
            UserAlreadyExists: If updating the username causes a duplicate.
        """
        existing_user = await self.get_by_id(user.id)
        if not existing_user:
            raise e.UserDoesNotExist('User with given ID does not exist!')
        
        try:
            await self.session.merge(user)
            await self.session.commit()
            if return_result: 
                await self.session.refresh(user)
                return user        
        except sqlexc.IntegrityError as error:
            self._handle_integrity_error(error)

    async def update_fields(self, user_id:int, fields: dict[str, t.Any], return_result:bool = True) -> m.User | None:
        """Update specific fields of a user by their ID.

        Args:
            user_id (int): The ID of the user to update.
            fields (dict[str, Any]): A dictionary of field names and values to update.
            return_result (bool, optional): Whether to return the updated user. Defaults to True.

        Returns:
            User | None: The updated user if `return_result` is True, else None.

        Raises:
            UserDoesNotExist: If no user with the given ID exists.
            UserAlreadyExists: If updating the username causes a duplicate.
        """
        existing_user = await self.get_by_id(user_id)
        if not existing_user:
            raise e.UserDoesNotExist('User with given ID does not exist!')
        
        q = (sqlm.update(m.User)
            .where(m.User.id == user_id)
            .values(**fields)
            .execution_options(synchronize_session='fetch')
        )
        try:
            await self.session.execute(q)
            await self.session.commit()
            if return_result:
                return await self.get_by_id(user_id)
        except sqlexc.IntegrityError as error:
            self._handle_integrity_error(error)
