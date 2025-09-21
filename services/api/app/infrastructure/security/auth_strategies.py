from app.application.repositories import SessionRepository
import app.application.interfaces as iapp
import app.application.exceptions as appexc
import app.application.models as mapp

import app.domain.repositories as repos
import app.domain.exceptions as domexc
import app.domain.models as mdom
import app.domain.services as domsvc

from app.common.config import Config
from app.presentation.schemas import TokenResponse

import typing as t
import jwt, uuid, datetime as dt

REFRESH_SECRET = Config.REFRESH_SECRET
JWT_SECRET = Config.JWT_SECRET
ACCESS_EXPIRES_MINS = Config.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_EXPIRES_HOURS = Config.REFRESH_TOKEN_EXPIRE_HOURS
ALGORITHM = Config.ALGORITHM

class StatefulOAuthStrategy(iapp.IAuthStrategy, iapp.ITokenMixin, iapp.IPasswordMixin, iapp.ILoginLogoutMixin):

    def __init__(self, session_repo: SessionRepository, user_repo: repos.IUserRepository, password_hasher: domsvc.IPasswordHasher):
        self.session_repo = session_repo
        self.user_repo = user_repo
        self._hasher = password_hasher

    def __exctract_token_data(self, token: str, refresh:bool=False):
        secret = REFRESH_SECRET if refresh else JWT_SECRET
        try:
            data = jwt.decode(token, secret, algorithms=[ALGORITHM])
            return data
        except jwt.InvalidTokenError as e:
            raise appexc.CredentialsException() from e
        except jwt.ExpiredSignatureError as e:
            raise appexc.TokenExpiredException() from e


    @staticmethod
    def __create_token(payload: dict, expires_delta: dt.timedelta, refresh: bool = False) -> str:
        secret = REFRESH_SECRET if refresh else JWT_SECRET
        expiration_time = (dt.datetime.now(dt.timezone.utc) + expires_delta).timestamp()
        encoded_jwt = jwt.encode(payload | {"exp": expiration_time}, secret, algorithm=Config.ALGORITHM)
        return encoded_jwt, expiration_time

    @staticmethod
    def __create_a_pair_of_tokens(payload: dict) -> TokenResponse:
        access_token_expires = dt.timedelta(minutes=ACCESS_EXPIRES_MINS)
        refresh_token_expires = dt.timedelta(days=REFRESH_EXPIRES_HOURS)

        access_token, access_expires = StatefulOAuthStrategy.__create_token(payload=payload, expires_delta=access_token_expires)
        refresh_token, refresh_expires = StatefulOAuthStrategy.__create_token(payload=payload, expires_delta=refresh_token_expires, refresh=True)
        return TokenResponse(access_token=access_token, refresh_token=refresh_token, access_expires=access_expires, refresh_expires=refresh_expires)

    @property
    def hasher(self) -> domsvc.IPasswordHasher:
        return self._hasher

    async def login(self, credentials: dict) -> TokenResponse:
        username = credentials['username']
        password = credentials['password']
        
        user = await self.user_repo.get_by_username(username)
        if not user:
            raise domexc.UserDoesNotExist("User does not exist!")
        
        if not self._hasher.verify(password, user.password_hash):
            raise appexc.CredentialsException("Bad password given for this username!")
        
        session_id = str(uuid.uuid4())
        tokens = self.__create_a_pair_of_tokens(dict(session_id = session_id))
        session = mapp.RotatingTokenSession(
            id = session_id,
            user_id = user.id,
            roles = [user.role],
            refresh_token=tokens.refresh_token
        )
        
        
        await self.session_repo.create(session, ttl=ACCESS_EXPIRES_MINS*60)
        return tokens

    async def logout(self, credentials: dict) -> None:
        token = credentials['token']
        data = self.__exctract_token_data(token=token)
        await self.session_repo.delete(data["session_id"])
    
    async def authenticate(self, credentials: dict) -> mdom.User:
        token = credentials["token"]
        if not token:
            raise appexc.CredentialsException("Token is missing")
        data = self.__exctract_token_data(token=token, refresh=False)
        session = await self.session_repo.get_session(data["session_id"])
        if not session:
            raise appexc.LoggedOutException("Token is valid, yet session does not exist!")
        
        user = await self.user_repo.get_by_id(session.user_id)
        if not user:
            raise appexc.LoggedOutException("Token is valid, yet session does not exist!")
        return user
        
        
    async def refresh(self, refresh_token: str) -> TokenResponse:
        data = self.__exctract_token_data(token=refresh_token, refresh=True)
        session: mapp.RotatingTokenSession = await self.session_repo.get_session(data["session_id"])
        if not session:
            raise appexc.LoggedOutException("Token is valid, yet session does not exist!")
        
        if session.refresh_token!=refresh_token:
            raise appexc.TokenExpiredException("This has been rotated already!")
        
        tokens = self.__create_a_pair_of_tokens(dict(session_id = session.id))
        session.refresh_token = tokens.refresh_token
        await self.session_repo.create(session, REFRESH_EXPIRES_HOURS * 3600)
        return tokens
        



        