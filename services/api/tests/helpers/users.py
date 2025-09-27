import app.infrastructure.dependencies as ideps
import app.domain.models as dmod

async def build_user_repo(uow: ideps.UnitOfWork, cache_client: ideps.CacheConnectionType) -> ideps.UserRepository:
    db = ideps.UserDB(uow.session)
    return ideps.UserRepoDependency(user_db_repo=db, connection=cache_client, uow=uow)


async def build_sess_repo(cache_client: ideps.CacheConnectionType) -> ideps.SessionRepository:
    return ideps.SessionRepository(cache_client)


async def create_user(user_repo, uow, username='admin', password='password', id=555):
    user = dmod.User.create(
        username=username,
        password=password,
        role=dmod.Role.ADMIN.value,
        hasher=ideps.PasswordHasherType(),
    )
    user.id = id
    await user_repo.create(user)
    await uow.commit()

async def create_several_users(user_repo, uow):
    hasher = ideps.PasswordHasherType()
    users = [
        dmod.User.create('test1','12341234', dmod.Role.USER.value, hasher),
        dmod.User.create('test2','12341234', dmod.Role.ADMIN.value, hasher),
        dmod.User.create('test3','12341234', dmod.Role.USER.value, hasher),
    ]
    users[2].set_status('deactivated')
    for user in users:
        await user_repo.create(user)
    await uow.commit()
