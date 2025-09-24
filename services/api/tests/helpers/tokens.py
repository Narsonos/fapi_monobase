
import jwt
import datetime as dt
import typing as t
import app.application.exceptions as appexc
import app.presentation.schemas as schemas


class OAuthTokenizer:
    def __init__(
        self,
        refresh_secret: str,
        jwt_secret: str,
        algorithm: str,
        access_expires_mins: int,
        refresh_expires_hours: int,
    ) -> None:
        self.refresh_secret = refresh_secret
        self.jwt_secret = jwt_secret
        self.algorithm = algorithm
        self.access_expires_mins = access_expires_mins
        self.refresh_expires_hours = refresh_expires_hours

    def exctract_token_data(self, token: str, refresh: bool = False) -> dict:
        secret = self.refresh_secret if refresh else self.jwt_secret
        try:
            data = jwt.decode(token, secret, algorithms=[self.algorithm])
            return data
        except jwt.ExpiredSignatureError as e:
            raise appexc.TokenExpiredException() from e
        except jwt.InvalidTokenError as e:
            raise appexc.CredentialsException() from e

    def create_token(self, payload: dict, expires_delta: dt.timedelta, refresh: bool = False) -> tuple[str, float]:
        secret = self.refresh_secret if refresh else self.jwt_secret
        expiration_time = (dt.datetime.now(dt.timezone.utc) + expires_delta).timestamp()
        encoded_jwt = jwt.encode(payload | {"exp": expiration_time}, secret, algorithm=self.algorithm)
        return encoded_jwt, expiration_time

    def create_a_pair_of_tokens(self, payload: dict) -> schemas.TokenResponse:
        access_token_expires = dt.timedelta(minutes=self.access_expires_mins)
        refresh_token_expires = dt.timedelta(hours=self.refresh_expires_hours)

        access_token, access_expires = self.create_token(payload=payload, expires_delta=access_token_expires)
        refresh_token, refresh_expires = self.create_token(
            payload=payload, expires_delta=refresh_token_expires, refresh=True
        )

        return schemas.TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            access_expires=access_expires,
            refresh_expires=refresh_expires,
        )
