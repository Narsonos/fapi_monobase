#NOTE: Only lines not covered by broader tests are tested here. (probably due to pytest-cov bugs, idk)
import pytest
import app.infrastructure.models as imod
import app.infrastructure.dependencies as ideps
import app.domain.models as dmod

@pytest.mark.asyncio
async def test_uow_rollback(uow):
    user = imod.User(id=1, username='12345', password_hash='123131', role=dmod.Role.ADMIN, status=dmod.Status.ACTIVE)
    uow.session.add(user)
    await uow.rollback()

    db = ideps.UserDB(uow.session)
    assert await db.get_by_id(1) == None
    
    
@pytest.mark.asyncio
async def test_uow_hook_not_throws(uow):
    async def raiser():
        raise Exception()

    uow.add_post_commit_hook(lambda: raiser())
    await uow.run_hooks()
    assert uow._post_commit_hooks == []