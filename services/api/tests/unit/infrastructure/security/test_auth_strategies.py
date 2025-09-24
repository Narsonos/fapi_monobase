import pytest, jwt, datetime as dt, uuid, pydantic as p, typing as t
from pytest_mock import MockerFixture
import app.infrastructure.security as isec
from app.common.config import Config
from tests.helpers.tokens import OAuthTokenizer
import app.application.exceptions as appexc
import app.domain.exceptions as domexc
import app.presentation.schemas as schemas
import app.domain.models as dmod
import app.application.models as amod

JWT_SECRET = 'abc123' 
REFRESH_SECCRET = 'abc321'

class FakeHasher:
    def hash(self, password: str) -> str:
        return f"hashed:{password}"

    def verify(self, password: str, hashed: str) -> bool:
        return hashed == f"hashed:{password}"


class SOAuthTestSuite(p.BaseModel):
    user: dmod.User | None
    mock_user_repo: t.Any
    mock_sess_repo: t.Any
    mocker: t.Any
    strat: isec.StatefulOAuthStrategy

    model_config = p.ConfigDict(arbitrary_types_allowed=True)


@pytest.fixture
def user_data():
    return dict(
        id=1,
        username='test',
        password_hash=FakeHasher().hash('12341234'),
        role=dmod.Role.USER,
        status=dmod.Status.ACTIVE
    )

@pytest.fixture
def get_full_oauth_setup(mocker,user_data):
    def _inner(user_exists: bool):
        mock_user_repo = mocker.AsyncMock()
        user = dmod.User(**user_data) if user_exists else None
        mock_user_repo.get_by_username.return_value = user
        mock_user_repo.get_by_id.return_value = user

        mock_sess_repo = mocker.AsyncMock()
        mock_sess_repo.create.return_value = None
        mock_sess_repo.delete.return_value = None

        strat = isec.StatefulOAuthStrategy(
            session_repo=mock_sess_repo,
            user_repo=mock_user_repo,
            password_hasher=FakeHasher(),
            jwt_secret=JWT_SECRET,
            refresh_secret=REFRESH_SECCRET
        )
        suite = SOAuthTestSuite(user=user, mock_user_repo=mock_user_repo, mock_sess_repo=mock_sess_repo, mocker=mocker, strat=strat)
        return suite
    return _inner

@pytest.fixture
def get_valid_token_pair():
    def _inner(payload):
        strat = isec.StatefulOAuthStrategy(
            user_repo=None,
            session_repo=None,
            password_hasher=FakeHasher(),
            jwt_secret=JWT_SECRET,
            refresh_secret=REFRESH_SECCRET
        )
        tokenizer = OAuthTokenizer(
            refresh_secret=strat.refresh_secret,
            jwt_secret=strat.jwt_secret,
            algorithm=strat.algorithm,
            access_expires_mins=strat.access_expires_mins,
            refresh_expires_hours=strat.refresh_expires_hours,
        )
        tokens = tokenizer.create_a_pair_of_tokens(payload)
        return tokens
    return _inner



def test_SOAuth_create_tokens_and_extract_data(get_valid_token_pair):
    strat = isec.StatefulOAuthStrategy(
        session_repo=None,
        user_repo=None,
        password_hasher=FakeHasher(),
        jwt_secret=JWT_SECRET,
        refresh_secret=REFRESH_SECCRET
    )
    payload = {'session_id': '1'}
    
    tokens: schemas.TokenResponse = get_valid_token_pair(payload)

    # Create an immediately-expired token using tokenizer
    tokenizer = OAuthTokenizer(
        refresh_secret=strat.refresh_secret,
        jwt_secret=strat.jwt_secret,
        algorithm=strat.algorithm,
        access_expires_mins=strat.access_expires_mins,
        refresh_expires_hours=strat.refresh_expires_hours,
    )
    outdated_token, expiration_time = tokenizer.create_token(payload, expires_delta=dt.timedelta(microseconds=0))

    with pytest.raises(appexc.CredentialsException):
        tokenizer.exctract_token_data('asdasdasda', refresh=False)

    with pytest.raises(appexc.TokenExpiredException):
        tokenizer.exctract_token_data(outdated_token, refresh=False)

    decoded_payload = tokenizer.exctract_token_data(tokens.access_token, refresh=False)
    assert decoded_payload == payload | {'exp': tokens.access_expires}



@pytest.mark.parametrize(
    'get_full_oauth_setup, credentials, user_exists, exc',
    [
        #fixture creds: test, 12341234
        ('get_full_oauth_setup', dict(username='test', password='12341234'), True, None),
        ('get_full_oauth_setup', dict(username='test', password='12341234'), False, domexc.UserDoesNotExist),
        ('get_full_oauth_setup', dict(username='test', password='11112222'), True, appexc.CredentialsException),
        ('get_full_oauth_setup', dict(username='test'), True, appexc.CredentialsException)
    ],
    indirect=['get_full_oauth_setup']
)
async def test_SOAuth_login_logout(get_full_oauth_setup, credentials, user_exists: bool, exc):
    suite = get_full_oauth_setup(user_exists)
    #test hasher property along the way
    assert isinstance(suite.strat.hasher, FakeHasher)
    if exc:
        with pytest.raises(exc):
            await suite.strat.login(credentials)
        
    else:
        tokens = await suite.strat.login(credentials)
        assert isinstance(tokens,schemas.TokenResponse)
        suite.mock_user_repo.get_by_username.assert_awaited_once()
        suite.mock_sess_repo.create.assert_awaited_once()

        await suite.strat.logout(credentials={'token': tokens.access_token})
        tokenizer = OAuthTokenizer(
            refresh_secret=suite.strat.refresh_secret,
            jwt_secret=suite.strat.jwt_secret,
            algorithm=suite.strat.algorithm,
            access_expires_mins=suite.strat.access_expires_mins,
            refresh_expires_hours=suite.strat.refresh_expires_hours,
        )
        data = tokenizer.exctract_token_data(tokens.access_token, refresh=False)
        suite.mock_sess_repo.delete.assert_called_once_with(data['session_id'])
        
        with pytest.raises(appexc.CredentialsException):
            await suite.strat.logout(credentials={'wrong_field':'adasda'})




@pytest.mark.parametrize(
    'get_full_oauth_setup, get_valid_token_pair, credentials, user_exists, session_exists, exc',
    [
        #NOTE: 'valid' in credentials creates a real pair of tokens with session_id="1"
        ('get_full_oauth_setup', 'get_valid_token_pair', 'valid', True, False, appexc.LoggedOutException),
        ('get_full_oauth_setup', 'get_valid_token_pair', 'valid', False, True, appexc.LoggedOutException),
        ('get_full_oauth_setup', 'get_valid_token_pair', dict(some_bad_field='abcasdadasd'), True, True, appexc.CredentialsException),
        ('get_full_oauth_setup', 'get_valid_token_pair', 'valid', True, True, None)
    ],
    indirect=['get_full_oauth_setup','get_valid_token_pair']
)
async def test_SOAuth_authenticate(get_full_oauth_setup, get_valid_token_pair, credentials, user_exists: bool, session_exists:bool, exc):
    suite: SOAuthTestSuite = get_full_oauth_setup(user_exists)
    if credentials == 'valid':
        payload = {'session_id':'some_uuid'}
        tokens:schemas.TokenResponse = get_valid_token_pair(payload)
        credentials = dict(token=tokens.access_token)
    
    session_mock = suite.mocker.MagicMock()
    session_mock.user_id = 1

    suite.mock_sess_repo.get_session.return_value = session_mock if session_exists else None
    if exc:
        with pytest.raises(exc):
            await suite.strat.authenticate(credentials)
    else:
        user = await suite.strat.authenticate(credentials)
        assert user == suite.user






@pytest.mark.parametrize(
    'get_full_oauth_setup, get_valid_token_pair, tokens_match, session_exists, exc',
    [
        #NOTE: 'valid' in credentials creates a real pair of tokens with session_id="1"
        ('get_full_oauth_setup', 'get_valid_token_pair', True, False, appexc.LoggedOutException),
        ('get_full_oauth_setup', 'get_valid_token_pair', False, True, appexc.TokenExpiredException),
        ('get_full_oauth_setup', 'get_valid_token_pair', True, True, None)
    ],
    indirect=['get_full_oauth_setup','get_valid_token_pair']
)
async def test_SOAuth_refresh(get_full_oauth_setup, get_valid_token_pair, tokens_match: bool, session_exists:bool, exc):
    suite: SOAuthTestSuite = get_full_oauth_setup(True)
    payload = {'session_id':'some_uuid'}
    tokens:schemas.TokenResponse = get_valid_token_pair(payload)

    session = amod.RotatingTokenSession(
        id='1',
        user_id=1,
        roles=['abc'],
        refresh_token=tokens.refresh_token if tokens_match else 'some other non matching token'
    )
    suite.mock_sess_repo.get_session.return_value = session if session_exists else None
    if exc:
        with pytest.raises(exc):
            await suite.strat.refresh(tokens.refresh_token)
    else:
        tokens = await suite.strat.refresh(tokens.refresh_token)
        assert isinstance(tokens, schemas.TokenResponse)
