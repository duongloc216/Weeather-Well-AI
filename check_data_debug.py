import asyncio
from core.sqlserver_client import get_db

async def check():
    pool = await get_db()
    async with pool.acquire() as conn:
        # Check weather data
        weather_count = await conn.fetchval('SELECT COUNT(*) FROM weather WHERE city_id = ?', 1587871)
        print(f'Weather rows for city 1587871: {weather_count}')
        
        # Check climate data
        climate_count = await conn.fetchval('SELECT COUNT(*) FROM climate WHERE city_id = ?', 1587871)
        print(f'Climate rows for city 1587871: {climate_count}')
        
        # Check uv data
        uv_count = await conn.fetchval('SELECT COUNT(*) FROM uv WHERE city_id = ?', 1587871)
        print(f'UV rows for city 1587871: {uv_count}')
        
        # Check user disease
        user = await conn.fetchrow('SELECT user_id, disease_id, describe_disease FROM users WHERE user_id = ?', 1)
        print(f'User info: {user}')
        
        # Check if user_city exists
        user_city = await conn.fetchrow('SELECT * FROM user_city WHERE user_id = ? AND city_id = ?', 1, 1587871)
        print(f'User_city: {user_city}')

asyncio.run(check())
