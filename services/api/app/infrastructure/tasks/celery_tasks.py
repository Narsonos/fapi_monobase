import datetime as dt, logging
import app.application.interfaces as iapp
from celery.app import Celery
from celery.result import AsyncResult
from celery.app.task import Task

logger = logging.getLogger('app')

class CeleryTaskProcessor(iapp.ITaskProcessor):
    """
    A task processor implementation that delegates task execution to a Celery application.
    
    This class provides an abstraction over Celery to allow scheduling, revoking,
    and managing both one-time and periodic tasks.
    """

    def __init__(self, celery: Celery):
        """
        Initialize the task processor with a Celery application instance.

        Args:
            celery (Celery): The Celery application used to send and manage tasks.
        """
        self.celery = celery

    async def add_task(self, task_name, *args, **kwargs):
        """
        Submit a new asynchronous task to Celery.

        Args:
            task_name (str): The fully qualified name of the task (e.g., "app.tasks.do_something").
            *args: Positional arguments passed to the task.
            **kwargs: Keyword arguments passed to the task.

        Returns:
            str: The unique ID of the submitted task.
        """
        task: Task = self.celery.send_task(name=task_name, args=args, kwargs=kwargs)
        return task.id

    async def get_task_result(self, task_id, timeout: int|None = None):
        result = AsyncResult(task_id, app=self.celery)
        return result.get(timeout=timeout)

    async def get_task_status(self, task_id):
        result = AsyncResult(task_id, app=self.celery)
        return result.status


    async def revoke_task(self, task_id):
        """
        Revoke (cancel) a previously submitted task.

        Args:
            task_id (str): The ID of the task to revoke.
        """
        self.celery.control.revoke(task_id)

    async def schedule_task(self, task_name, eta_utc: float | dt.datetime, *args, **kwargs):
        """
        Schedule a task for future execution at a specific time.

        Args:
            task_name (str): The name of the task to schedule.
            eta (float | datetime.datetime): Execution time. Can be provided as a UNIX timestamp (float)
                                             or a datetime object.
            *args: Positional arguments for the task.
            **kwargs: Keyword arguments for the task.

        Returns:
            str: The unique ID of the scheduled task.
        """
        if isinstance(eta_utc, float):
            eta_utc = dt.datetime.fromtimestamp(eta_utc, tz=dt.timezone.utc)
        task: Task = self.celery.send_task(name=task_name,args=args,kwargs=kwargs,eta=eta_utc)
        return task.id


    def task(self, *args, **kwargs):
        """
        Just a proxy to celery's decorator
        """
        return self.celery.task(*args, **kwargs)
    