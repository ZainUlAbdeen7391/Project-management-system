import os
import aiomysql
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

class Database:
    _pool = None

    @classmethod
    async def init(cls):
        cls._pool = await aiomysql.create_pool(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            port=int(os.getenv("DB_PORT", "3306")),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            db=os.getenv("DB_NAME", "project_management_systemdb"),
            autocommit=False,
            minsize=1,
            maxsize=10
        )

    @classmethod
    @asynccontextmanager
    async def get_cursor(cls):
        async with cls._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                try:
                    yield cur
                    await conn.commit()
                except Exception:
                    await conn.rollback()
                    raise

async def get_db():
    async with Database.get_cursor() as cur:
        yield cur
        
        
