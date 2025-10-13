import app.infrastructure.dependencies as ideps
import logging, datetime as dt

logger = logging.getLogger('app')

@ideps.TaskProcessor.task(name='periodic_task')
def periodic_task():
    logger.info('Periodic task example')

@ideps.TaskProcessor.task(name="twice")
def test_twice(a:int):
    return 2*a

@ideps.TaskProcessor.task(name="eta")
def test_eta():
    return dt.datetime.now(dt.timezone.utc).timestamp()