import abc, typing as t

class ITaskProcessor(abc.ABC):
    @abc.abstractmethod
    async def add_task(self, task_name: str, *args, **kwargs) -> str:
        """Queue task, return task_id"""

    @abc.abstractmethod
    async def get_task_result(self, task_id, timeout=None) -> t.Any:
        """Fetches task results"""

    @abc.abstractmethod
    async def get_task_status(self, task_id) -> str:
        """Fetches task status"""

    @abc.abstractmethod
    async def revoke_task(self, task_id: str) -> None:
        """Cancel task by task_id"""

    @abc.abstractmethod
    async def schedule_task(self, task_name: str, eta: float, *args, **kwargs) -> str:
        """Schedule a task for execution in the future (timestamp ETA)"""

    @abc.abstractmethod
    def task(self, *args, **kwargs) -> t.Callable[[t.Callable[..., t.Any]], t.Callable[..., t.Any]]:
        """Must return a decorator"""




class IPeriodicTaskProcessor(ITaskProcessor):
    @abc.abstractmethod
    async def add_periodic_task(self, task_name ,schedule, *args, **kwargs):
        """Add a task that will be executed periodically according to the schedule"""