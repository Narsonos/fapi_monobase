from app.application.repositories import SessionRepository
import app.application.interfaces as iapp
import app.application.exceptions as appexc
import app.application.models as mapp
import app.infrastructure.interfaces as iabc
import app.domain.repositories as repos
import app.domain.exceptions as domexc
import app.domain.models as mdom
import app.domain.services as domsvc


from app.infrastructure.telemetry.traces import TracerType
from app.common.config import Config
from app.presentation.schemas import TokenResponse

import typing as t
import jwt, uuid, datetime as dt



class StatefulOAuthStrategy(iapp.IAuthStrategy, iapp.ITokenMixin, iapp.IPasswordMixin, iapp.ILoginLogoutMixin):

    def __init__(
        self,
        session_repo: SessionRepository,
        user_repo: repos.IUserRepository,
        password_hasher: domsvc.IPasswordHasherAsync,
        *,
        refresh_secret: t.Optional[str] = None,
        jwt_secret: t.Optional[str] = None,
        access_expires_mins: t.Optional[int] = None,
        refresh_expires_hours: t.Optional[int] = None,
        algorithm: t.Optional[str] = None,
    ):
        
        self.session_repo = session_repo
        self.user_repo = user_repo
        self._hasher = password_hasher

        self.refresh_secret = refresh_secret or Config.REFRESH_SECRET
        self.jwt_secret = jwt_secret or Config.JWT_SECRET
        self.access_expires_mins = (
            access_expires_mins or Config.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        self.refresh_expires_hours = (
            refresh_expires_hours or Config.REFRESH_TOKEN_EXPIRE_HOURS
        )
        self.algorithm = algorithm or Config.ALGORITHM

    def __exctract_token_data(self, token: str, refresh: bool = False):
        secret = self.refresh_secret if refresh else self.jwt_secret
        try:
            data = jwt.decode(token, secret, algorithms=[self.algorithm])
            return data
        except jwt.ExpiredSignatureError as e:
            raise appexc.TokenExpiredException() from e
        except jwt.InvalidTokenError as e:
            raise appexc.CredentialsException() from e

    @TracerType.traced
    def __create_token(self, payload: dict, expires_delta: dt.timedelta, refresh: bool = False) -> tuple[str, float]:
        secret = self.refresh_secret if refresh else self.jwt_secret
        expiration_time = (dt.datetime.now(dt.timezone.utc) + expires_delta).timestamp()
        encoded_jwt = jwt.encode(
            payload | {"exp": expiration_time}, secret, algorithm=self.algorithm
        )
        return encoded_jwt, expiration_time

    def __create_a_pair_of_tokens(self, payload: dict) -> TokenResponse:
        access_token_expires = dt.timedelta(minutes=self.access_expires_mins)
        refresh_token_expires = dt.timedelta(hours=self.refresh_expires_hours)

        access_token, access_expires = self.__create_token(
            payload=payload, expires_delta=access_token_expires
        )
        refresh_token, refresh_expires = self.__create_token(
            payload=payload, expires_delta=refresh_token_expires, refresh=True
        )
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            access_expires=access_expires,
            refresh_expires=refresh_expires,
        )

    @property
    def hasher(self) -> domsvc.IPasswordHasherAsync:
        return self._hasher

    async def login(self, credentials: dict) -> TokenResponse:
        username = credentials.get('username')
        password = credentials.get('password')

        if not (username and password):
            raise appexc.CredentialsException("Field missing! Both username and password must be provided.")
        
        user = await self.user_repo.get_by_username(username)
        if not user:
            raise domexc.UserDoesNotExist("User does not exist!")
        
        with TracerType.start_span('login_password_verifying'):
            if not await self._hasher.verify(password, user.password_hash):
                raise appexc.CredentialsException("Bad password given for this username!")
        
        session_id = str(uuid.uuid4())
        tokens = self.__create_a_pair_of_tokens(dict(session_id=session_id))
        session = mapp.RotatingTokenSession(
            id = session_id,
            user_id = user.id,
            roles = [user.role],
            refresh_token=tokens.refresh_token
        )
        await self.session_repo.create(session, ttl=self.access_expires_mins * 60)
        return tokens

    async def logout(self, credentials: dict) -> None:
        token = credentials.get('token')
        if not token:
            raise appexc.CredentialsException("Token is missing. Please provide a valid access token for this operation.")
        data = self.__exctract_token_data(token=token)
        await self.session_repo.delete(data["session_id"])
    
    async def authenticate(self, credentials: dict) -> mdom.User:
        token = credentials.get('token')
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
        
        if session.refresh_token != refresh_token:
            raise appexc.TokenExpiredException("This token has been rotated already - it not valid anymore!")

        tokens = self.__create_a_pair_of_tokens(dict(session_id=session.id))
        session.refresh_token = tokens.refresh_token
        await self.session_repo.create(session, self.refresh_expires_hours * 3600)
        return tokens
        



        