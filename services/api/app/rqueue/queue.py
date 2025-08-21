from functools import wraps
from fastapi import Depends, Request
from typing import Annotated
import inspect
import logging
import asyncio
import uuid
import time
import httpx
import os.path
from redis.asyncio.client import Redis
logger = logging.getLogger('app.queue')


class RedisQueueError(Exception):
    """Base class for Redis Queue exception family"""
    pass 

class RedisQueueTimeoutError(RedisQueueError):
    """Raised when waiting for a free slot exceeds the timeout."""
    pass

class RedisQueueResourceIsAlreadyUsed(RedisQueueError):
    """Raised when User is already using this resource"""
    pass


REDIS_SCRIPTS_DIRECTORY_PATH = os.path.join(os.path.dirname(__file__), 'scripts')
REDIS_SCRIPTS_KEY = 'rqueue:scripts'



async def load_scripts_to_redis(redis:Redis):
    for filename in os.listdir(REDIS_SCRIPTS_DIRECTORY_PATH):
        if not filename.endswith('.lua'):
            continue
        path = os.path.join(REDIS_SCRIPTS_DIRECTORY_PATH, filename)
        with open(path, 'r', encoding='utf-8') as f:
            script = f.read()
            sha = await redis.script_load(script)
            await redis.hset(REDIS_SCRIPTS_KEY, filename, sha)
            logger.info(f"[RedisScripts] Loaded {filename} -> {sha}")


class RedisQueueManager:
    def __init__(self, redis: Redis):
        self.redis = redis
        self.scripts = {}
        self.scripts_path = os.path.join(os.path.dirname(__file__),'scripts')

    async def init_scripts(self):
        self.scripts = await self.redis.hgetall(REDIS_SCRIPTS_KEY)
        if not self.scripts:
            raise RuntimeError("Lua scripts not loaded in Redis. Did you run the loader?")

    async def run_script(self, script_name: str, keys: list[str], args: list[str] = []):
        sha = self.scripts.get(script_name)
        if not sha:
            raise KeyError(f"No SHA found for script: {script_name}")
        return await self.redis.evalsha(sha, len(keys), *keys, *args)

    @staticmethod
    def is_async(func):
        """Helper function to determine if the function is async"""
        if inspect.iscoroutinefunction(func):
            return True
        if inspect.isfunction(func):
            return False
        if isinstance(func, staticmethod):  
            func = func.__func__  
            return inspect.iscoroutinefunction(func)  
        return False

    async def wait_for_slot(self, resource_queue_key: str, used_slots_key:str, lock_key:str, task: str, limit: int, timeout: float, check_interval: float = 1.0):
        """FIFO queue waiting - waits until a free slot for given resource has appeared.
        Arguments:
        - resource_queue_key:str - key to the queue for given resource
        - used_slots_key:str - key to the counter of used slots for given resource
        - lock_key:str - key to a redis lock
        - task:str - a UUID/ID of this task (to track our position in the queue)
        - limit:int number of slots
        - timeout:float - timeout in seconds, for how long we are going to wait at max before throwing an exception
        - check_interval:float - interval between checks (if a free slot appeared) in seconds
        """

        #another approach: using redis lists to maintian FIFO    
        async with self.redis.lock(lock_key, 30):
            await self.redis.rpush(resource_queue_key, task)

        try:
            start_time = asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - start_time <= timeout:
                async with self.redis.lock(lock_key, 30):
                    used_slots = int(await self.redis.get(used_slots_key) or 0)

                if used_slots < limit: #if free slot appeared
                    async with self.redis.lock(lock_key, 30):
                        first = await self.redis.lindex(resource_queue_key, 0) #who's first in the queue?
                    if first == task: #if that's us - exit queue
                        return
                await asyncio.sleep(check_interval) #else - wait

            #if timed out     
            async with self.redis.lock(lock_key, 30):
                await self.redis.lrem(resource_queue_key, 0, task)
            raise RedisQueueTimeoutError(f'Redis Queue timeout waiting for {resource_queue_key} for {(asyncio.get_event_loop().time() - start_time):.2f}s. Limit = {limit}')

        #if cancelled
        except asyncio.CancelledError:
            raise 
        finally:
            async with self.redis.lock(lock_key, 30):
                await self.redis.lrem(resource_queue_key, 0, task) 

    def use_queue_for_resource(self, resource: str, limit: int, exec_timeout: int, timeout:float = 10.0, check_interval: float = 1.0):
        """Decorator factory that creates resource sepcific queue managers
        Arguments:
        - resource: str - arbitrary name of the resource (queue name)
        - limit: int - arbitrary N of slots the resource has
        - exec_timeout: int - time in seconds for which a slot can be occupied
        - timeout: float - time in seconds for which a task is waiting for a free slot
        - check_interval: float - time in seconds between checks for a free slot
        """

        def decorator(func):
            @wraps(func)
            async def wrapper(*args,**kwargs):
                resource_queue_key = f'queue:{resource}:waiting'
                used_slots_key = f'queue:{resource}:active'
                lock_key = f'queue:{resource}:queue_lock'
                task = str(uuid.uuid4()) 

                async with self.redis.lock(lock_key, 30):
                    qlen = await self.redis.llen(resource_queue_key)
                    used = int(await self.redis.get(used_slots_key) or 0)

                logger.debug(f'[QUEUE] Resource {resource} is accessed. Waiting: {qlen}; Active: {used}. Func: {func.__name__}')

                await self.wait_for_slot(resource_queue_key, used_slots_key, lock_key, task, limit, timeout, check_interval) #This will raise Exception, so no need to check for limits.

                async with self.redis.lock(lock_key, 30):
                    await self.redis.incr(used_slots_key) #Active users don't need a list, a counter must be enough

                try: 
                    if self.is_async(func):
                        return await asyncio.wait_for(func(*args, **kwargs), timeout=exec_timeout)
                    else:
                        return func(*args, **kwargs)
                except asyncio.CancelledError:
                    logger.warning(f'[QUEUE] Task cancelled! Cleaning up slot {task[:8]}...{task[:-8]}.')
                    raise  
                finally:
                    async with self.redis.lock(lock_key, 30):
                        await self.redis.decr(used_slots_key) #Active users don't need a list, a counter must be enough
                        qlen = await self.redis.llen(resource_queue_key)
                        used = int(await self.redis.get(used_slots_key) or 0)
                    logger.debug(f'[QUEUE] Resource with key {used_slots_key} is released. Waiting: {qlen}; Active: {used}. Func: {func.__name__}')

            return wrapper
        return decorator                

    def lock_for_same_user(self, resource:str, user_id_kwarg_name:str):
        """Locks a resource with an arbitrary name <resource>. A user is identified by a value contained in a kwarg with a passed name.
        Example: A target function is def vote_in_a_poll(user_id:int, option:int) -> then user_id_kwarg is "user_id", i.e. it's value is going to be used to distinguish users.
        """

        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                user_id = kwargs.get(user_id_kwarg_name)
                user_specific_key = f'queue:{resource}:{user_id}'
                locked = await self.redis.get(user_specific_key)
                if not locked:
                    logger.debug(f'[QUEUE] User {user_id} used {resource}')
                    await self.redis.set(user_specific_key, 1)

                    try:
                        if self.is_async(func):
                            return await func(*args, **kwargs)
                        else:
                            return func(*args,**kwargs)
                    finally:
                        logger.debug(f'[QUEUE] User {user_id} freed {resource}')
                        await self.redis.delete(user_specific_key)
                else:
                    logger.debug(f'[QUEUE] User {user_id} tried to use {resource} twice!')
                    raise RedisQueueResourceIsAlreadyUsed(f'Resource {resource} cannot be accessed twice by {user_id}')
            return wrapper
        return decorator

    def rate_limit(
            self,
            resource:str = 'default', 
            seconds_between_requests:float = 1,
            burst_capacity: int = 3,
            seconds_between_burst_requests:float = 1, 
            ttl: float = 600,
            max_wait_time: int = 300
        ):
        """
        Decorator factory: limits request rate resource-specifically. Now uses token-bucket
        Arguments:
            - resource:str - An arbitrary name of a resource that is being locked, several functions can share this value
            - seconds_between_requests:float - A number of seconds that must elapse between requests, except for burst cases
            - burst_capcity: int - An integer reflecting how many requests can pass in a single burst
            - seconds_between_burst_requests: float - Minimal delay for requests, even those within a burst
        """

        refill_rate = 1/seconds_between_requests

        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                while True:
                    keys = [
                        f"ratelimit:{resource}:tokens",
                        f"ratelimit:{resource}:refill",
                        f"ratelimit:{resource}:request",
                    ]
                    args_ = [burst_capacity, refill_rate, seconds_between_burst_requests, ttl]
                    allowed, wait_time = await self.run_script('token_bucket.lua', keys=keys, args=args_)
                    wait_time = float(wait_time)
                    if allowed:
                        return await func(*args, **kwargs)
                    elapsed = time.time() - start_time
                    if elapsed + wait_time > max_wait_time:
                        raise RedisQueueTimeoutError(f"Rate limit: waited {elapsed:.2f}s, max allowed is {max_wait_time}s")
                    logger.info(f'Call for {resource} is rate limited => waiting {wait_time:.3f}')
                    await asyncio.sleep(wait_time)

            return wrapper
        return decorator

class RateLimitedTransport(httpx.AsyncBaseTransport):
    """Custom HTTPx Async transport that uses rate_limit"""

    def __init__(
            self,
            queue_mgr: RedisQueueManager,
            base: httpx.AsyncBaseTransport = None,
            retries: int = 0,
            resource:str = "default",
            seconds_between_requests:float = 1,
            burst_capacity: int = 3,
            seconds_between_burst_requests:float = 1
        ):

        self.base_transport = base or httpx.AsyncHTTPTransport(retries=retries)
        self.resource = resource
        self.seconds_between_requests = seconds_between_requests
        self.burst_capacity = burst_capacity
        self.seconds_between_burst_requests = seconds_between_burst_requests
        self.queue_mgr = queue_mgr
    
    async def handle_async_request(self, request):
        @self.queue_mgr.rate_limit(self.resource, seconds_between_requests=self.seconds_between_requests,seconds_between_burst_requests=self.seconds_between_burst_requests, burst_capacity=self.burst_capacity)
        async def _handle(self, request):
            return await self.base_transport.handle_async_request(request)
        return await _handle(self, request)



def get_rqueue(request: Request):
    return request.app.state.rqueue

RQueueDependency = Annotated[RedisQueueManager, Depends(get_rqueue)]