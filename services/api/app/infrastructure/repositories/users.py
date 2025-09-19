import app.presentation.schemas as schemas
import app.domain.repositories as repo
import app.domain.models as domain
import app.domain.exceptions as e
import app.domain.services as domsvc
import app.infrastructure.models as db


from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel.sql.expression import SelectOfScalar
import sqlalchemy.exc as sqlexc
import sqlmodel as sqlm
import typing as t
import pydantic as p

from redis.asyncio import Redis
import json, hashlib
import logging
from app.common.config import Config

# Cache TTL (seconds)
USER_CACHE_TTL_SECONDS = Config.USER_CACHE_TTL_SECONDS
DEFAULT_ADMIN_USERNAME = Config.DEFAULT_ADMIN_USERNAME
DEFAULT_ADMIN_PASSWORD = Config.DEFAULT_ADMIN_PASSWORD

logger = logging.getLogger('app')


class SQLAUserRepository(repo.IUserRepository):
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
            if error_code == 1062 and 'id' in msg:
                raise e.UserAlreadyExists(f"Another user with this id already exists") from error
        raise e.UserIntegrityError("Action causes integrity constraint violation for User model. Cancelled", orig=error.orig)

    def _apply_filters(self, select_query: SelectOfScalar[db.User], filters: schemas.UserFilterSchema, filter_mode: t.Literal["and","or"] = "and"):
        d = filters.model_dump(exclude_none=True)
        f = sqlm.and_ if filter_mode == "and" else sqlm.or_
        where_filters = [getattr(db.User, key)==value for key,value in d.items()]
        return select_query.where(f(*where_filters)) if where_filters else select_query
            
    async def _get_by_id(self, user_id: int) -> db.User | None:
        """Gets user by ID. For internal use, does not convert to domain level model."""
        return (await self.session.scalars(
            sqlm.select(db.User).where(db.User.id == user_id)
        )).one_or_none()


    async def get_by_id(self, user_id: int) -> domain.User | None:
        """Retrieve a user by their unique ID.

        Args:
            user_id (int): The ID of the user to retrieve.

        Returns:
            User | None: The user object if found, else None.
        """
        user = await self._get_by_id(user_id=user_id)
        return domain.User.model_validate(user, from_attributes=True) if user is not None else None
        

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
        return domain.User.model_validate(user, from_attributes=True) if user is not None else None

    async def list(self, limit: int = 100, offset: int = 0, filters: schemas.UserFilterSchema = None, filter_mode: t.Literal["and","or"] = "and") -> list[domain.User]:
        """Retrieve all users in the system.

        Returns:
            list[User]: List of all users.
        """
        q = sqlm.select(db.User)
        if filters:
            q = self._apply_filters(q, filters, filter_mode)
        q = q.limit(limit).offset(offset)
        users_db = (await self.session.scalars(q)).all()
        return [domain.User.model_validate(u, from_attributes=True) for u in users_db]


    async def create(self, user: domain.User) -> domain.User:
        """Creates a given user in the database
        Args:
            user: User to save

        Returns:
            User: a created user.
        """
        try:
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
            return domain.User.model_validate(user, from_attributes=True)
        except sqlexc.IntegrityError as e:
            self._handle_integrity_error(e)

    async def update(self, user: domain.User) -> domain.User:
        result = await self.session.execute(
            sqlm.update(db.User)
            .where(db.User.id == user.id, db.User.version == user.version)
            .values(**user.model_dump(exclude={"version"}), version=user.version+1)
        )
        if result.rowcount == 0:
            raise e.VersionError("User was updated concurrently. Your operation cancelled -> Retry.")
        await self.session.commit()
        user.version += 1
        return user

    async def delete(self, user: domain.User):
        """Delete a user from database.

        Args:
            user: User to delete

        Returns:
            None.
        """
        user = db.User.model_validate(user)
        await self.session.delete(user)
        await self.session.commit()

    async def ensure_admin_exists(self, hasher: domsvc.IPasswordHasher):
        admins = await self.list(limit=1, filters=schemas.UserFilterSchema(role="admin"))
        if not admins:
            default_admin = domain.User(
                username=DEFAULT_ADMIN_USERNAME,
                password_hash=hasher.hash(DEFAULT_ADMIN_PASSWORD),
                role="admin",
                status="active"
            )
            await self.create(default_admin)
    

class RedisCacheUserRepository(repo.IUserRepository):
    def __init__(self, user_db_repo: repo.IUserRepository, connection: Redis):
        self.user_db = user_db_repo
        self.redis = connection

    async def __clear_userlist_cache(self):
        logger.debug('[CACHE: USERS] Dropping users:list cache')
        cursor = "0"
        while cursor:
            cursor, keys = await self.redis.scan(cursor, "users:list:*")
            if keys:
                await self.redis.delete(*keys)
            if cursor == 0:
                break

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

    async def list(self, limit: int = 100, offset: int = 0, filters: schemas.UserFilterSchema = None, filter_mode: t.Literal["and","or"] = "and") -> list[domain.User]:
        pagination = f':offset={offset}:limit={limit}'
        filters_dict = filters.model_dump(exclude_none=True) if filters else None
        filters_json = json.dumps(filters_dict, sort_keys=True) if filters_dict else ""
        full_hash = hashlib.sha256((pagination + filters_json).encode()).hexdigest()
        key = f'users:list:{full_hash}'

        raw = await self.redis.get(key)
        if raw:
            logger.debug(f'[CACHE: USERS] hit {key}')
            try:
                data = json.loads(raw)
                return [domain.User.model_validate(item) for item in data]
            except Exception:
                pass
        users = await self.user_db.list(limit=limit, offset=offset, filters=filters, filter_mode=filter_mode)
        logger.debug(f'[CACHE: USERS] miss {key} - priming')
        await self.redis.set(key, json.dumps([u.model_dump() for u in users]), ex=USER_CACHE_TTL_SECONDS)
        return users
    
    async def create(self, user: domain.User) -> domain.User:
        user = await self.user_db.create(user)
        if user:
            logger.debug(f'[CACHE: USERS] User id={user.id}, username={user.username} created. Priming.')
            await self.redis.set(f'user:{user.id}', user.model_dump_json(), ex=USER_CACHE_TTL_SECONDS)
            await self.redis.set(f'user:username:{user.username}', user.model_dump_json(), ex=USER_CACHE_TTL_SECONDS)
            await self.__clear_userlist_cache()
        return user

    async def update(self, user: domain.User) -> domain.User:
        old = await self.redis.get(f'user:{user.id}')
        old_user = domain.User.model_validate_json(old) if old else None
        user = await self.user_db.update(user)
        if user:
            logger.debug(f'[CACHE: USERS] User id={user.id}, username={user.username} updated. Priming.')
            async with self.redis.pipeline() as pipe:
                pipe.set(f'user:{user.id}', user.model_dump_json(), ex=USER_CACHE_TTL_SECONDS)
                if old_user:
                    pipe.delete(f'user:username:{old_user.username}')
                pipe.set(f'user:username:{user.username}', user.model_dump_json(), ex=USER_CACHE_TTL_SECONDS)
                await pipe.execute()
            await self.__clear_userlist_cache()
        return user


    async def delete(self, user: domain.User) -> None:
        # fetch user to know username and remove both keys
        await self.user_db.delete(user)
        logger.debug(f'[CACHE: USERS] delete id={user.id}')
        await self.redis.delete(f'user:{user.id}')
        await self.redis.delete(f'user:username:{user.username}')
        await self.__clear_userlist_cache()

    async def ensure_admin_exists(self, hasher: domsvc.IPasswordHasher):
        await self.user_db.ensure_admin_exists(hasher)
    



    
