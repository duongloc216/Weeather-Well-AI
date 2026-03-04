import uuid
from core.sqlserver_client import get_db
from core.redis_client import get_redis_data
from dotenv import load_dotenv
import os
import asyncio
import json
load_dotenv('/Users/macbook/Desktop/BangA_DSC2025/.env')

QUEUE_DATA = os.getenv("QUEUE_DATA", "queue_data")


async def fetch_city_data():
    """
    Query city_id, longitude, latitude (unique city_id) từ DB
    """
    pool = await get_db()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT DISTINCT uc.city_id, c.longitude, c.latitude
            FROM user_city uc
            LEFT JOIN city c ON uc.city_id = c.city_id
        """)
        return rows

async def clear_old_data(): # hàm xoá dữ liệu trước khi thực hiện push_job lặp lịch
    """
    Xoá toàn bộ dữ liệu trong các bảng weather, climate, uv
    """
    pool = await get_db()
    async with pool.acquire() as conn:
        # SQL Server không có TRUNCATE ... RESTART IDENTITY CASCADE
        # Dùng DELETE thay vì TRUNCATE
        await conn.execute("DELETE FROM weather;")
        await conn.execute("DELETE FROM climate;")
        await conn.execute("DELETE FROM uv;")
        print("[SQL Server] Cleared data from weather, climate, uv")


async def push_jobs_collect_data():
    """
    Clear old data, sau đó build job JSON và push vào QUEUE_DATA
    """
    await clear_old_data()

    redis_data = await get_redis_data()
    rows = await fetch_city_data()

    for row in rows:
        job_data = {
            "job_id": str(uuid.uuid4()),
            "city_id": row["city_id"],
            "longitude": row["longitude"],
            "latitude": row["latitude"]
        }
        await redis_data.lpush(QUEUE_DATA, json.dumps(job_data))
        print(f"[PUSHED to {QUEUE_DATA}] {job_data}")

# này chỉ để test cho scheduler
if __name__ == "__main__":
    asyncio.run(push_jobs_collect_data())

