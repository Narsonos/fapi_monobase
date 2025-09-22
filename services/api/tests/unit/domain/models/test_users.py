import pytest, random
import app.domain.models as dmod
import app.domain.exceptions as domexc
from tests.mocks import FakeHasher


@pytest.fixture
def valid_user() -> dmod.User:
    return dmod.User.create(
        username='test',
        password='12341234',
        role='user',
        hasher=FakeHasher()
    )

@pytest.fixture
def hasher() -> FakeHasher:
    return FakeHasher()

@pytest.mark.models
@pytest.mark.parametrize(
   "username, hasher, expected_error",
   [
       ("abc123",'hasher', None),
       ("23123a-+",'hasher', 'only numbers and letters')
   ],
   indirect=['hasher']
)
def test_invalid_username_raises_error(username, hasher, expected_error):
    if expected_error:
        with pytest.raises(domexc.UserValueError, match=expected_error):
            user = dmod.User.create(
                username = username,
                password = '123123123',
                role = dmod.Role.ADMIN,
                hasher=hasher
            )
    else:
        user = dmod.User.create(
                username = username,
                password = '123123123',
                role = dmod.Role.ADMIN,
                hasher=hasher
            )
        assert user.username == username


@pytest.mark.models
@pytest.mark.parametrize(
   "valid_user, hasher, password, expected_error",
   [
       ("valid_user",'hasher','3123', 'Minimal password length '),
       ("valid_user",'hasher','123123123', None)
   ],
   indirect=['valid_user','hasher']
)
def test_password_length(valid_user: dmod.User, hasher: FakeHasher, password, expected_error):
    if expected_error: 
        with pytest.raises(domexc.UserValueError, match=expected_error):
            valid_user.force_change_password(new=password, hasher=hasher)
    else:
        valid_user.force_change_password(new=password, hasher=hasher)
        assert hasher.verify(password, valid_user.password_hash)

@pytest.mark.models
def test_is_admin_property(valid_user: dmod.User):
    assert valid_user.is_admin == False
    valid_user.role = dmod.Role.ADMIN
    assert valid_user.is_admin == True

@pytest.mark.models
def test_role_setter(valid_user: dmod.User):
    with pytest.raises(domexc.UserValueError):
        valid_user.set_role('12312pasodksapodadasdasdasd')
    role = random.choice(list(dmod.Role))
    valid_user.set_role(role)   
    assert valid_user.role == role

@pytest.mark.models
def test_status_setter(valid_user: dmod.User):
    with pytest.raises(domexc.UserValueError):
        valid_user.set_status('12312pasodksapodadasdasdasd')
    status = random.choice(list(dmod.Status))
    valid_user.set_status(status)   
    assert valid_user.status == status

@pytest.mark.models
def test_hash_password(hasher: FakeHasher):
    with pytest.raises(domexc.UserValueError):
        dmod.User._hash_password('1234567',hasher)

    password = '12345678'
    hash = dmod.User._hash_password(password, hasher)
    assert hasher.verify(hashed=hash, password=password)

@pytest.mark.models
def test_user_creation(hasher: FakeHasher):
    data = dict(
        username = 'test',
        role=dmod.Role.USER,
    )
    password = '11112222'
    user = dmod.User(**data, password_hash=hasher.hash(password), status=dmod.Status.ACTIVE)
    created_user = dmod.User.create(**data, password=password, hasher=hasher)
    assert user == created_user


@pytest.mark.models
@pytest.mark.parametrize(
   "valid_user, hasher, old, new, expected_error",
   [    #valid user correct old password: 12341234
       ("valid_user",'hasher','111112222','asdasdasda', 'Old password invalid'),
       ("valid_user",'hasher','12341234','12341234', 'password must not match the old one'),
       ("valid_user",'hasher','12341234','1111123123123123123', None)
   ],
   indirect=['valid_user','hasher']
)
def test_password_change(valid_user: dmod.User, hasher: FakeHasher, old, new, expected_error):
    if expected_error == 'Old password invalid':
        with pytest.raises(domexc.UserValueError, match=expected_error):
            valid_user.change_password('not_matching_old', new, hasher)
    elif expected_error == 'password must not match the old one':
        with pytest.raises(domexc.UserValueError,match=expected_error):
            valid_user.change_password(old, old, hasher)
    elif expected_error is None:
        valid_user.change_password(old, new, hasher)
        assert hasher.verify(password=new, hashed=valid_user.password_hash)

    