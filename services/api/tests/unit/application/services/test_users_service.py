import pytest, typing as t
from pytest_mock import MockerFixture
import app.application.services as svc
import app.domain.models as dmod
import app.domain.exceptions as domexc
import app.presentation.schemas as schemas
from tests.mocks import FakeHasher



@pytest.fixture
def hasher() -> FakeHasher:
    return FakeHasher()

@pytest.fixture
def user_data():
    return dict(
        id=1,
        username='1234',
        role=dmod.Role.USER,
        status=dmod.Status.ACTIVE,
    )


@pytest.mark.asyncio
async def test_user_service_get_user(mocker: MockerFixture, hasher, user_data):
    mock_user_repo = mocker.AsyncMock()
    mock_user_repo.get_by_id.return_value = dmod.User(**user_data,password_hash='somehash',version=0)
    service = svc.UserService(mock_user_repo, hasher)
    target_id = 1
    user = await service.get_user(target_id)
    assert user == schemas.UserDTO.model_validate(user_data)
    mock_user_repo.get_by_id.assert_called_once_with(target_id)
        
@pytest.mark.asyncio
async def test_user_service_list(mocker: MockerFixture, hasher, user_data):
    mock_user_repo = mocker.AsyncMock()
    mock_user_repo.list.return_value = [dmod.User(**user_data,password_hash='somehash',version=0)]

    service = svc.UserService(mock_user_repo, hasher)
    user_list = await service.list(1,1,filters=None)
    assert user_list == [schemas.UserDTO.model_validate(user_data)]
    mock_user_repo.list.assert_called_once_with(1,1,None,'and')


@pytest.mark.asyncio
async def test_user_service_delete(mocker: MockerFixture, hasher):
    mock_user_repo = mocker.AsyncMock()
    mock_user_repo.delete.return_value = None
    service = svc.UserService(mock_user_repo, hasher)

    current_user = mocker.MagicMock(spec=schemas.UserDTO )
    current_user.id = 1

    rs = await service.delete(current_user)
    mock_user_repo.delete.assert_called_once_with(current_user.id)


@pytest.mark.asyncio
@pytest.mark.parametrize(
   "mocker, hasher, current_user_role, current_user_id, target_user_id, target_user_exists, exc, exc_text",
   [    
       ("mocker",'hasher','user', 1,1, True,domexc.ActionNotAllowedForRole,'for admins only'),
       ("mocker",'hasher','admin', 1,1, True,domexc.ActionNotAllowedForRole, 'delete their own accounts'),
       ("mocker",'hasher','admin', 1,2, False,domexc.UserDoesNotExist, 'provided ID does not exist'),
       ("mocker",'hasher','admin', 1,2, True,None,None),
   ],
   indirect=['mocker','hasher']
)
async def test_user_service_admin_delete(mocker, hasher, current_user_role, current_user_id, target_user_id, target_user_exists, exc, exc_text):
    mock_user_repo = mocker.AsyncMock()
    mock_user_repo.delete.return_value = None
    mock_user_repo.get_by_id.return_value = target_user_exists
    service = svc.UserService(mock_user_repo, hasher)

    current_user = schemas.UserDTO(
        id=current_user_id,
        username='test',
        role=current_user_role,
        status=dmod.Status.ACTIVE
    )

    if exc_text:
        with pytest.raises(exc, match=exc_text):
            await service.admin_delete(current_user, target_user_id)
    else:
        await service.admin_delete(current_user, target_user_id)
        mock_user_repo.delete.assert_called_once_with(target_user_exists)

    
@pytest.mark.asyncio
async def test_user_service_create(mocker, hasher, user_data):
    mock_user_repo = mocker.AsyncMock()
    password = '12341234'

    input_user = schemas.PublicUserCreationModel(
        username=user_data.get('username'),
        password=password
    )
    created_user = dmod.User(
        **user_data,
        password_hash=hasher.hash(password),
        version=0
    )
    repo_input_user = dmod.User.model_copy(created_user)
    repo_input_user.id = None
    repo_input_user.version = None

    mock_user_repo.create.return_value = created_user
    service = svc.UserService(mock_user_repo, hasher)
    result = await service.create(input_user)
    assert result == schemas.UserDTO.model_validate(created_user,from_attributes=True)
    mock_user_repo.create.assert_called_once_with(repo_input_user)

@pytest.mark.asyncio
@pytest.mark.parametrize(
   "mocker, hasher, user_data, current_user_role, target_user_role, exc, exc_text",
   [    
       ("mocker",'hasher','user_data','user','user',domexc.ActionNotAllowedForRole,'for admins only'),
       ("mocker",'hasher','user_data','user','admin',domexc.ActionNotAllowedForRole, 'for admins only'),
       ("mocker",'hasher','user_data','admin','user',None,None),
       ("mocker",'hasher','user_data','admin','admin',None,None),
   ],
   indirect=['mocker','hasher','user_data']
)
async def test_user_service_admin_create(mocker, hasher, user_data, current_user_role, target_user_role, exc, exc_text):
    mock_user_repo = mocker.AsyncMock()
    password = '12341234'

    current_user = schemas.UserDTO(
        id=2,
        username='cur',
        role=current_user_role,
        status=dmod.Status.ACTIVE,
    )
    user_data['role'] = target_user_role
    input_user = schemas.PrivateUserCreationModel(
        username=user_data.get('username'),
        password=password,
        role=user_data.get('role')
    )
    created_user = dmod.User(
        **user_data,
        password_hash=hasher.hash(password),
        version=0
    )
    repo_input_user = dmod.User.model_copy(created_user)
    repo_input_user.id = None
    repo_input_user.version = None

    mock_user_repo.create.return_value = created_user
    service = svc.UserService(mock_user_repo, hasher)

    if exc:
        with pytest.raises(exc, match=exc_text):
            await service.admin_create(current_user, input_user)
    else:
        result = await service.admin_create(current_user, input_user)
        assert result == schemas.UserDTO.model_validate(created_user,from_attributes=True)
        mock_user_repo.create.assert_called_once_with(repo_input_user)


@pytest.mark.asyncio
@pytest.mark.parametrize(
   "mocker, hasher, user_data, old_pass,new_pass, exc, exc_text",
   [    
       ("mocker",'hasher','user_data','11112222',None,domexc.UserValueError,'both password fields must be provided'),
       ("mocker",'hasher','user_data','11112222','123123123',None, None),
       ("mocker",'hasher','user_data',None,None,None,None),
       ("mocker",'hasher','user_data',None,None,None,None),
   ],
   indirect=['mocker','hasher','user_data']
)
async def test_user_service_update(mocker, hasher, user_data, old_pass,new_pass, exc, exc_text):
    mock_user_repo = mocker.AsyncMock()
    new_username = 'newname'
    current_user = schemas.UserDTO(**user_data)
    update_model = schemas.PublicUserUpdateModel(
        username=new_username,
        old_password=old_pass,
        new_password=new_pass
    )

    domain_model_before_changes = dmod.User(**user_data, password_hash=hasher.hash(old_pass), version=1)
    domain_model_after_changes = dmod.User.model_copy(domain_model_before_changes)
    domain_model_after_changes.username = new_username
    
    if old_pass and new_pass:
        domain_model_after_changes.change_password(old_pass, new_pass, hasher)
    
    domain_updated_model = dmod.User.model_copy(domain_model_after_changes)
    domain_updated_model.version += 1

    mock_user_repo.get_by_id.return_value = domain_model_before_changes
    mock_user_repo.update.return_value = domain_updated_model
    service = svc.UserService(mock_user_repo, hasher)
    
    if exc:
        with pytest.raises(exc, match=exc_text):
            await service.update(current_user, update_model)
    else:
        result = await service.update(current_user, update_model)
        assert result == schemas.UserDTO.model_validate(domain_updated_model,from_attributes=True)
        mock_user_repo.update.assert_called_once_with(domain_model_after_changes)
        mock_user_repo.get_by_id.assert_called_once_with(current_user.id)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mocker, hasher, user_data, current_user_role, current_user_id, target_user_id, target_user_exists, edited_role, edited_status, new_pass, exc, exc_text",
    [
        ("mocker", 'hasher', 'user_data', 'user', 1, 2, True, None, None, None, domexc.ActionNotAllowedForRole, 'for admins only'),
        ("mocker", 'hasher', 'user_data', 'admin', 1, 1, True, 'user', None, None, domexc.ActionNotAllowedForRole, 'Admins are not allowed to change their own role.'),
        ("mocker", 'hasher', 'user_data', 'admin', 1, 2, False, None, None, None, domexc.UserDoesNotExist, 'User with the provided ID does not exist'),
        ("mocker", 'hasher', 'user_data', 'admin', 1, 2, True, 'user', dmod.Status.ACTIVE, 'newpassword', None, None),
        ("mocker", 'hasher', 'user_data', 'admin', 1, 2, True, 'user', None, None, None, None),
        ("mocker", 'hasher', 'user_data', 'admin', 1, 1, True, None, dmod.Status.DEACTIVATED, None, domexc.ActionNotAllowedForRole, 'Admins cannot deactivate their own account'),
    ],
    indirect=['mocker', 'hasher', 'user_data'],
)
async def test_user_service_admin_update(
    mocker,
    hasher,
    user_data,
    current_user_role,
    current_user_id,
    target_user_id,
    target_user_exists,
    edited_role,
    edited_status,
    new_pass,
    exc,
    exc_text,
):
    mock_user_repo = mocker.AsyncMock()

    current_user = schemas.UserDTO(
        id=current_user_id,
        username='cur',
        role=current_user_role,
        status=dmod.Status.ACTIVE,
    )

    target_user = None
    if target_user_exists:
        target_user = dmod.User(**user_data, password_hash=hasher.hash('initpass'), version=1)

    edited_user = schemas.PrivateUserUpdateModel(
        username='newname',
        new_password=new_pass,
        role=edited_role,
        status=edited_status,
    )

    if target_user and new_pass:
        target_user.force_change_password(new_pass, hasher=hasher)

    expected = None
    if target_user:
        expected = dmod.User.model_copy(target_user)
        if edited_user.username:
            expected.username = edited_user.username
        if edited_user.role:
            expected.set_role(edited_user.role)
        if edited_user.status:
            expected.set_status(edited_user.status)
        if new_pass:
            expected.version += 1

    mock_user_repo.get_by_id.return_value = target_user
    if target_user:
        mock_user_repo.update.return_value = expected

    service = svc.UserService(mock_user_repo, hasher)

    if exc:
        with pytest.raises(exc, match=exc_text):
            await service.admin_update(current_user, target_user_id, edited_user)
    else:
        result = await service.admin_update(current_user, target_user_id, edited_user)
        assert result == schemas.UserDTO.model_validate(expected, from_attributes=True)
        mock_user_repo.update.assert_called_once()



 