import app.domain.models as dmod
import app.application.dependencies as adeps
from app.infrastructure.dependencies import UserRepository, UserDB, UnitOfWork

async def test_login(async_client, uow, cache):
    username = 'test'
    password = '123123123'

    user_db = UserDB(uow.session)
    user_repo = UserRepository(user_db, cache, uow)
    user = dmod.User.create(username='test', password='123123123', role='user', hasher=adeps.PasswordHasher())
    await user_repo.create(user)
    await uow.commit()

    response = await async_client.post('/auth/login', data={'username':username, 'password':password})
    assert response.status_code == 200