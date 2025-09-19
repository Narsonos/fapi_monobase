import app.application.repositories as apprepo
import app.application.models as m
from redis.asyncio import Redis





class RedisSessionRepository(apprepo.SessionRepository):
    def __init__(self, redis: Redis):
        self.redis = redis

    async def create(self, session: m.RotatingTokenSession, ttl:int) -> None:    
        await self.redis.set(f'session:{session.id}', session.model_dump_json(), ex=ttl)
        return session

    async def delete(self, session_id: str) -> None:
        await self.redis.delete(f'session:{session_id}')

    async def get_session(self, session_id: str) -> m.RotatingTokenSession | None:
        sess = await self.redis.get(f'session:{session_id}')
        return m.RotatingTokenSession.model_validate_json(sess) if sess else None

    async def refresh(self, session_id:str, ttl:int) -> None:
        await self.redis.expire(f'session:{session_id}', ttl)