from abc import ABC, abstractmethod
import typing as t

ConnectionType = t.TypeVar("ConnectionType") 
SessionType = t.TypeVar("SessionType")



class ConnectionManagerInterface(t.Generic[ConnectionType], ABC):
    @abstractmethod
    async def connect(self) -> ConnectionType: ...

    @abstractmethod
    async def close(self) -> None: ...

    @abstractmethod
    async def wait_for_startup(self, attempts:int = 5, interval_sec: int = 5):
        '''Pings the external service until it has started up'''

    @abstractmethod
    async def initialize_data_structures(self):
        '''Creates all data structures, if there are any to create'''

    @abstractmethod
    async def flush_data(self):
        '''Drops all data'''


class SessionManagerInterface(ConnectionManagerInterface[ConnectionType], t.Generic[ConnectionType, SessionType], ABC):
    @abstractmethod
    async def session(self, **kwargs) -> SessionType: 
        '''Must return a context manager -> async with self.session() as session'''
    
