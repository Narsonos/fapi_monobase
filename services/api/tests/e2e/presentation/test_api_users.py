import app.application.dependencies as adeps
import app.infrastructure.dependencies as ideps
import app.domain.models as dmod
import app.domain.exceptions as domexc
import app.presentation.schemas as schemas
import pytest
import pytest_asyncio as pytestaio
from tests.helpers.users import build_sess_repo, build_user_repo, create_user, create_several_users

username, password = 'admin', 'password'


async def valid_tokens(username, password,user_repo, sess_repo):
    auth_start = ideps.AuthStrategyType(user_repo=user_repo, session_repo=sess_repo, password_hasher=ideps.PasswordHasherType())
    tokens = await auth_start.login(dict(username=username, password=password))
    return tokens


@pytest.mark.asyncio
async def test_get_user(async_client, uow, cache_client):
    user_repo = await build_user_repo(uow, cache_client)
    await create_user(user_repo, uow, id=555)

    actual_user =  await user_repo.get_by_id(555)
    response = await async_client.get(f'/users/{555}')
    assert response.status_code == 200
    user = schemas.UserDTO.model_validate(response.json())
    assert user.id == 555
    
    response = await async_client.get(f'/users/1111')
    assert response.json().get('detail') is not None #returns a json with user does not exist message
    none = await user_repo.get_by_id(1111) #nonexistent id
    assert none is None
    


@pytest.mark.asyncio
async def test_get_users(async_client, uow, cache_client):
    user_repo = await build_user_repo(uow, cache_client)
    await create_several_users(user_repo, uow)
    url = '/users'
    
    case = await async_client.get(url)
    case_json = case.json()
    assert len(case_json) == 3
    case = await async_client.get(url) #Triggers cache for coverage

    #limit works
    case = await async_client.get(url, params=dict(limit=1))
    case_json = case.json()
    assert isinstance(case_json, list)
    assert len(case_json) == 1
    model = schemas.UserDTO.model_validate(case_json[0])

    #offset works
    case = await async_client.get(url, params=dict(limit=1, offset=5))
    case_json = case.json()
    assert isinstance(case_json, list)
    assert len(case_json) == 0

    #username works
    case = await async_client.get(url, params=dict(username='test1'))
    case_json = case.json()
    assert isinstance(case_json, list)
    assert len(case_json) == 1
    model = schemas.UserDTO.model_validate(case_json[0])
    assert model.username == 'test1'

    #role works
    case = await async_client.get(url, params=dict(role=dmod.Role.ADMIN.value, username='test1', filter_mode='or'))
    case_json = case.json()
    assert isinstance(case_json, list)
    assert len(case_json) == 2

    contains_test1 = False
    contains_admin = False

    for user in case_json:
        model = schemas.UserDTO.model_validate(user)
        if model.is_admin:
            contains_admin = True
        if model.username == 'test1':
            contains_test1 = True

    assert contains_test1 is True
    assert contains_admin is True
    

@pytest.mark.asyncio
async def test_admin_create_users(async_client, uow, cache_client):
    user_repo = await build_user_repo(uow, cache_client)
    sess_repo = await build_sess_repo(cache_client)
    await create_user(user_repo, uow)
    adm_tokens = await valid_tokens(username, password, user_repo, sess_repo)

    url = '/users'
    aname, cpass = 'admin2', '12341234'
    uname = 'user333'
    response_adm = await async_client.post(url, json={'username':aname,'password':cpass,'role':dmod.Role.ADMIN.value}, headers={"Authorization": f"Bearer {adm_tokens.access_token}"})
    response_usr = await async_client.post(url, json={'username':uname,'password':cpass,'role':dmod.Role.USER.value}, headers={"Authorization": f"Bearer {adm_tokens.access_token}"})
    
    assert response_adm.status_code == 201
    assert response_usr.status_code == 201
    await uow.commit()
    
    user = await user_repo.get_by_username(aname)
    assert user is not None
    assert user.role == dmod.Role.ADMIN

    user = await user_repo.get_by_username(uname)
    assert user is not None
    assert user.role == dmod.Role.USER

    user_tokens = await valid_tokens(uname, cpass, user_repo, sess_repo)

    response = await async_client.post(url, json={'username':'icantlogin','password':cpass,'role':dmod.Role.ADMIN.value}, headers={"Authorization": f"Bearer {user_tokens.access_token}"})
    assert response.status_code == 403
    response = await async_client.post(url, json={'username':uname,'password':cpass,'role':dmod.Role.ADMIN.value}, headers={"Authorization": f"Bearer {adm_tokens.access_token}"})    
    assert response.status_code == 409



@pytest.mark.asyncio
async def test_user_update(async_client, uow, cache_client):
    user_repo = await build_user_repo(uow, cache_client)
    sess_repo = await build_sess_repo(cache_client)
    await create_several_users(user_repo, uow)

    #user update self
    user = await user_repo.get_by_username('test1') #gives us id
    assert user.version == 0
    edited_username = 'etest1'
    old_password = '12341234'
    new_password = '44442222'
    tokens = await valid_tokens('test1', old_password, user_repo, sess_repo)

    ### user tries to make themselves admin
    response = await async_client.patch(
        url  =f'/users/{user.id}',
        json = {'username':edited_username, 'old_password': old_password, 'new_password':new_password, 'role':dmod.Role.ADMIN.value},
        headers = {'Authorization':f'Bearer {tokens.access_token}'}
    )
    assert response.status_code == 422
    
    ### user tries to make themselves admin
    response = await async_client.patch(
        url  =f'/users/{user.id}',
        json = {'username':edited_username, 'old_password': old_password, 'new_password':new_password},
        headers = {'Authorization':f'Bearer {tokens.access_token}'}
    )
    await uow.commit()
    assert response.status_code == 200
    user = await user_repo.get_by_username(edited_username)
    assert user.version == 1
    assert user.username == edited_username


    #admin update etest1 -> e2test and make into admin
    adm_pass = '12341234'
    edited_username = 'e2test1'
    tokens = await valid_tokens('test2', adm_pass, user_repo, sess_repo)
    
    response = await async_client.patch(
        url  =f'/users/{user.id}',
        json = {'username':edited_username, 'role':dmod.Role.ADMIN.value},
        headers = {'Authorization':f'Bearer {tokens.access_token}'}
    )
    assert response.status_code == 200
    user = await user_repo.get_by_username(edited_username)
    assert user.version == 2
    assert user.username == edited_username



@pytest.mark.asyncio
async def test_user_delete(async_client, uow, cache_client):
    user_repo = await build_user_repo(uow, cache_client)
    sess_repo = await build_sess_repo(cache_client)
    await create_several_users(user_repo, uow)

    #user delete self
    username, password = 'test1','12341234'

    user = await user_repo.get_by_username(username)
    tokens = await valid_tokens(username, password, user_repo, sess_repo)
    response = await async_client.delete(
        url  =f'/users/{user.id}',
        headers = {'Authorization':f'Bearer {tokens.access_token}'}
    )
    assert response.status_code == 204

    #admin delete others
    username, password = 'test2','12341234'
    user = await user_repo.get_by_username('test3')
    tokens = await valid_tokens(username, password, user_repo, sess_repo)

    response = await async_client.delete(
        url  =f'/users/{user.id}',
        headers = {'Authorization':f'Bearer {tokens.access_token}'}
    )
    assert response.status_code == 204