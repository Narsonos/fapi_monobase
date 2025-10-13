import app.application.repositories as iapp
from redis.asyncio.client import Redis
import datetime as dt

class RedisMetricActiveUserStorage(iapp.IMetricActiveUsersStorage):
    def __init__(self, redis: Redis, zset_key='metrics:dau'):
        self.redis = redis
        self.zset_key = zset_key
        
    async def register_activity(self, user_id):
        '''Inserts a user into a ZSET with a timestamp as score'''
        await self.redis.zadd(self.zset_key, {user_id:dt.datetime.now().timestamp()})

    async def get_active_count(self, timespan_sec: int) -> int:
        '''Returns users that were updated within less than *self.timespan*'''
        now = dt.datetime.now().timestamp()
        return await self.redis.zcount(self.zset_key, min=now-timespan_sec, max=now)
    
    async def remove_old(self, timespan_sec: int):
        '''Removes stale records'''
        now = dt.datetime.now().timestamp()
        await self.redis.zremrangebyscore(self.zset_key,min=0, max=now-timespan_sec)