import pytest, datetime as dt, asyncio
import app.infrastructure.dependencies as ideps




@pytest.mark.asyncio
async def test_task_processor_celery_basic_execution():
    task_id = await ideps.TaskProcessor.add_task('twice',3)
    assert await ideps.TaskProcessor.get_task_status(task_id) == "PENDING"
    assert await ideps.TaskProcessor.get_task_result(task_id,3) == 6


@pytest.mark.asyncio
async def test_task_processor_celery_scheduling():
    t0 = dt.datetime.now(dt.timezone.utc).timestamp()
    t1_eta = t0 + 3 #task will be delayed for 3s
    task_id = await ideps.TaskProcessor.schedule_task('eta',t1_eta)
    t1_factual = await ideps.TaskProcessor.get_task_result(task_id, timeout=10)

    #we're expecting the difference of delays to be small
    assert abs(t1_factual - t1_eta) <= 0.5