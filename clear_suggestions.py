import asyncio
from core.sqlserver_client import get_db

async def delete_all_suggestions():
    """Xóa tất cả suggestions của user_id=1"""
    pool = await get_db()
    async with pool.acquire() as conn:
        result = await conn.execute('DELETE FROM suggestion WHERE user_id = 1')
        print(f'✅ Đã xóa tất cả suggestions của user_id=1')
        print(f'   Kết quả: {result}')

asyncio.run(delete_all_suggestions())
