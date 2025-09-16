import app.domain.repositories as repo
import app.domain.models as domain
import app.domain.exceptions as e
import app.infrastructure.models as db

from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy.exc as sqlexc
import sqlmodel as sqlm
import typing as t
import pydantic as p

from redis.asyncio import Redis
import json
import logging
from app.common.config import Config

# Cache TTL (seconds)
USER_CACHE_TTL_SECONDS = Config.USER_CACHE_TTL_SECONDS

logger = logging.getLogger('app')

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

    async def get_by_id(self, user_id: int) -> domain.User | None:
        """Retrieve a user by their unique ID.

        Args:
            user_id (int): The ID of the user to retrieve.

        Returns:
            User | None: The user object if found, else None.
        """
        user = (await self.session.scalars(
            sqlm.select(db.User).where(db.User.id == user_id)
        )).one_or_none()
        return domain.User.model_validate(user) if user is not None else None
        

    async def get_by_username(self, username: str) -> domain.User | None:
        """Retrieve a user by their unique username.

        Args:
            username (str): The username to search for.

        Returns:
            User | None: The user object if found, else None.
        """
        user = (await self.session.scalars(
            sqlm.select(db.User).where(db.User.username == username)
        )).one_or_none()
        return domain.User.model_validate(user) if user is not None else None

    async def list(self, limit: int = 100, offset: int = 0) -> list[domain.User]:
        """Retrieve all users in the system.

        Returns:
            list[User]: List of all users.
        """
        q = sqlm.select(db.User).limit(limit).offset(offset)
        users_db = (await self.session.scalars(q)).all()
        return [domain.User.model_validate(u) for u in users_db]


    async def create(self, user: domain.User, return_result: bool = True) -> domain.User | None:
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
            user = db.User.model_validate(user)
            self.session.add(user)
            await self.session.commit()
            if return_result: 
                await self.session.refresh(user)
                return domain.User.model_validate(user)
        except sqlexc.IntegrityError as error:
            self._handle_integrity_error(error)

    async def update(self, user: domain.User, return_result: bool = True) -> domain.User | None:
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
            user = db.User.model_validate(user)
            await self.session.merge(user)
            await self.session.commit()
            if return_result: 
                await self.session.refresh(user)
                return domain.User.model_validate(user)        
        except sqlexc.IntegrityError as error:
            self._handle_integrity_error(error)

    async def update_fields(self, user_id:int, fields: dict[str, t.Any], return_result:bool = True) -> domain.User | None:
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
        
        q = (sqlm.update(db.User)
            .where(db.User.id == user_id)
            .values(**fields)
            .execution_options(synchronize_session='fetch')
        )
        try:
            await self.session.execute(q)
            await self.session.commit()
            if return_result:
                user = await self.get_by_id(user_id)
                return domain.User.model_validate(user) if user else None
        except sqlexc.IntegrityError as error:
            self._handle_integrity_error(error)



class RedisCacheUserRepository(repo.UserRepository):
    def __init__(self, user_db_repo: repo.UserRepository, connection: Redis):
        self.user_db = user_db_repo
        self.redis = connection

    async def __clear_userlist_cache(self):
        cursor = b'0'
        while cursor:
            cursor, keys = await self.redis.scan(0, "users:list:*")
            if keys:
                await self.redis.delete(*keys)

    async def get_by_id(self, user_id: int) -> domain.User | None:
        key = f'user:{user_id}'
        raw = await self.redis.get(key)
        if raw:
            logger.debug(f'[CACHE: USERS] hit id={user_id}')
            try:
                return domain.User.model_validate_json(raw)
            except p.ValidationError:
                logger.debug(f'[CACHE: USERS] cache record for user id={user_id} contains corrupt data. Fallback')

        user = await self.user_db.get_by_id(user_id)
        if user:
            logger.debug(f'[CACHE: USERS] miss id={user_id} - priming')
            await self.redis.set(key, user.model_dump_json(), ex=USER_CACHE_TTL_SECONDS)
            await self.redis.set(f'user:username:{user.username}', user.model_dump_json(), ex=USER_CACHE_TTL_SECONDS)
        return user

    async def get_by_username(self, username: str) -> domain.User | None:
        key = f'user:username:{username}'
        raw = await self.redis.get(key)
        if raw:
            logger.debug(f'[CACHE: USERS] hit username={username}')
            try:
                return domain.User.model_validate_json(raw)
            except Exception:
                logger.debug(f'[CACHE: USERS] cache record for username={username} contains corrupt data. Fallback')

        user = await self.user_db.get_by_username(username)
        if user:
            logger.debug(f'[CACHE: USERS] miss username={username} - priming')
            await self.redis.set(key, user.model_dump_json(), ex=USER_CACHE_TTL_SECONDS)
            await self.redis.set(f'user:{user.id}', user.model_dump_json(), ex=USER_CACHE_TTL_SECONDS)
        return user

    async def list(self, limit: int = 100, offset: int = 0) -> list[domain.User]:
        key = f'users:list:offset={offset}:limit={limit}'
        raw = await self.redis.get(key)
        if raw:
            logger.debug('[CACHE: USERS] hit users:all')
            try:
                data = json.loads(raw)
                return [domain.User.model_validate(item) for item in data]
            except Exception:
                pass
        users = await self.user_db.list(limit=limit, offset=offset)
        logger.debug(f'[CACHE: USERS] miss {key} - priming')
        await self.redis.set(key, json.dumps([u.model_dump() for u in users]), ex=USER_CACHE_TTL_SECONDS)
        return users
    
    async def create(self, user: domain.User, return_result:bool = True) -> domain.User | None:
        created = await self.user_db.create(user, return_result=return_result)
        if created:
            logger.debug(f'[CACHE: USERS] create priming id={created.id} username={created.username}')
            await self.redis.set(f'user:{created.id}', created.model_dump_json(), ex=USER_CACHE_TTL_SECONDS)
            await self.redis.set(f'user:username:{created.username}', created.model_dump_json(), ex=USER_CACHE_TTL_SECONDS)
            await self.__clear_userlist_cache()
        return created

    async def update(self, user: domain.User, return_result:bool = True) -> domain.User | None:
        updated = await self.user_db.update(user, return_result=return_result)
        if updated:
            id_key = f'user:{updated.id}'
            cached_raw = await self.redis.get(id_key)
            if cached_raw:
                try:
                    cached_user = domain.User.model_validate_json(cached_raw)
                    await self.redis.delete(f'user:username:{cached_user.username}')
                except Exception:
                    pass

            logger.debug(f'[CACHE: USERS] update priming id={updated.id} username={updated.username}')

            updated_raw = updated.model_dump_json()
            await self.redis.set(id_key, updated_raw, ex=USER_CACHE_TTL_SECONDS)
            await self.redis.set(f'user:username:{updated.username}', updated_raw, ex=USER_CACHE_TTL_SECONDS)
            await self.__clear_userlist_cache()
        return updated

    async def update_fields(self, user_id:int, fields: dict[str, t.Any], return_result:bool = True) -> domain.User | None:
        updated = await self.user_db.update_fields(user_id, fields, return_result=return_result)
        if updated:
            # refresh caches similar to update
            logger.debug(f'[CACHE: USERS] update_fields priming id={updated.id} username={updated.username}')
            updated_raw = updated.model_dump_json()
            await self.redis.set(f'user:{updated.id}', updated_raw, ex=USER_CACHE_TTL_SECONDS)
            await self.redis.set(f'user:username:{updated.username}', updated_raw, ex=USER_CACHE_TTL_SECONDS)
            await self.__clear_userlist_cache()
        return updated

    async def delete(self, user_id: int) -> None:
        # fetch user to know username and remove both keys
        user = await self.user_db.get_by_id(user_id)
        await self.user_db.delete(user_id)
        logger.debug(f'[CACHE: USERS] delete id={user_id}')
        await self.redis.delete(f'user:{user_id}')
        if user:
            await self.redis.delete(f'user:username:{user.username}')
        await self.__clear_userlist_cache()




    
