"""PostgreSQL 연결 관리"""

import os
import asyncpg
from contextlib import asynccontextmanager

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://stopper:stopper2026@localhost:5432/stopper"
)

pool: asyncpg.Pool = None


async def init_db():
    """DB 연결 풀 초기화"""
    global pool
    pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=2,
        max_size=10,
    )
    print(f"✓ Connected to PostgreSQL")


async def close_db():
    """DB 연결 종료"""
    global pool
    if pool:
        await pool.close()
        print("✓ Disconnected from PostgreSQL")


@asynccontextmanager
async def get_connection():
    """커넥션 컨텍스트 매니저"""
    async with pool.acquire() as conn:
        yield conn


async def execute(query: str, *args):
    """단일 쿼리 실행"""
    async with pool.acquire() as conn:
        return await conn.execute(query, *args)


async def fetch_one(query: str, *args):
    """단일 행 조회"""
    async with pool.acquire() as conn:
        return await conn.fetchrow(query, *args)


async def fetch_all(query: str, *args):
    """다중 행 조회"""
    async with pool.acquire() as conn:
        return await conn.fetch(query, *args)


async def fetch_val(query: str, *args):
    """단일 값 조회"""
    async with pool.acquire() as conn:
        return await conn.fetchval(query, *args)
