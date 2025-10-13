import abc


class IMetricActiveUsersStorage(abc.ABC):
    @abc.abstractmethod
    async def register_activity(self, user_id: int) -> None: ... 

    @abc.abstractmethod
    async def get_active_count(self, timespan_sec: int) -> int: ...

    @abc.abstractmethod
    async def remove_old(self, timespan_sec: int) -> None: ...


