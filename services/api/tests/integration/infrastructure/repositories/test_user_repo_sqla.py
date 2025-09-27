#NOTE: Only lines not covered by broader tests are tested here. (probably due to pytest-cov bugs, idk)
import app.infrastructure.dependencies as ideps
import pytest
import app.domain.models as dmod
import app.domain.exceptions as domexc
from app.infrastructure.repositories.users import DEFAULT_ADMIN_USERNAME

@pytest.mark.asyncio
async def test_user_repo_get_by_id(uow):
    id = 15
    db = ideps.UserDB(uow.session)
    user = dmod.User(
        id=id,
        username='someusername',
        password_hash='abcasdasdasdasd',
        role=dmod.Role.USER,
        status=dmod.Status.ACTIVE
    )
    await db.create(user)
    await uow.commit()
    user = await db.get_by_id(id)
    nonexistent = await db.get_by_id(id+1)
    assert nonexistent is None
    assert user.id == id


@pytest.mark.asyncio
async def test_user_repo_list(uow):
    db = ideps.UserDB(uow.session)

    for i in range(3):
        user = dmod.User(
            id=i+1,
            username=f'getbyid{i+1}',
            password_hash='abcasdasdasdasd',
            role=dmod.Role.USER,
            status=dmod.Status.ACTIVE
        )
        await db.create(user)
    await uow.commit()

    users = await db.list()
    assert len(users) == 3

@pytest.mark.asyncio
async def test_user_repo_duplicate_handling_username(uow):
    db = ideps.UserDB(uow.session)
    id = 10
    user = dmod.User(
        id=id,
        username='name',
        password_hash='abcasdasdasdasd',
        role=dmod.Role.USER,
        status=dmod.Status.ACTIVE
    )
    await db.create(user)
    with pytest.raises(domexc.UserAlreadyExists):
        await db.create(user)
        await uow.commit()


@pytest.mark.asyncio
async def test_user_repo_duplicate_handling_id(uow):
    db = ideps.UserDB(uow.session)
    id = 10
    user = dmod.User(
        id=id,
        username='name',
        password_hash='abcasdasdasdasd',
        role=dmod.Role.USER,
        status=dmod.Status.ACTIVE
    )
    await db.create(user)
    user_with_no_id_but_same_name = dmod.User.model_copy(user)
    with pytest.raises(domexc.UserAlreadyExists):
        await db.create(user_with_no_id_but_same_name)
        await uow.commit()
    
    

@pytest.mark.asyncio
async def test_user_repo_update(uow):
    db = ideps.UserDB(uow.session)
    id = 10
    user = dmod.User(
        id=id,
        username='name',
        password_hash='abcasdasdasdasd',
        role=dmod.Role.USER,
        status=dmod.Status.ACTIVE
    )
    bad_id_user = dmod.User.model_copy(user)
    bad_id_user.id = 11 #currently not in DB -> can't update
    bad_id_user.username = 'name2' #change for future use
    await db.create(user)
    await uow.commit()

    #cant edit nonexistent
    with pytest.raises(domexc.UserDoesNotExist):
        await db.update(bad_id_user)

    #cant use used username
    await db.create(bad_id_user) 
    with pytest.raises(domexc.UserAlreadyExists):
        bad_id_user.username = 'name' #we use a name that's already taken
        await db.update(bad_id_user)

    #valid update
    bad_id_user.username = 'validname'
    updated = await db.update(bad_id_user)  
    assert updated.username == 'validname'

@pytest.mark.asyncio
async def test_user_repo_delete(uow):
    db = ideps.UserDB(uow.session)
    id = 10
    user = dmod.User(
        id=id,
        username='name',
        password_hash='abcasdasdasdasd',
        role=dmod.Role.USER,
        status=dmod.Status.ACTIVE
    )
    await db.create(user)
    await uow.commit()
    await db.delete(user)
    await uow.commit()
    

    with pytest.raises(ValueError):
        user.id = None
        await db.delete(user)

    assert await db.get_by_id(10) == None

@pytest.mark.asyncio
async def test_ensure_admin_exists(uow):
    db = ideps.UserDB(uow.session)
    await db.ensure_admin_exists(hasher=ideps.PasswordHasherType())

    admin = await db.get_by_username(DEFAULT_ADMIN_USERNAME)
    assert admin.role == dmod.Role.ADMIN.value

