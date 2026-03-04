import asyncio
from core.sqlserver_client import get_db

async def check_weather_data():
    pool = await get_db()
    async with pool.acquire() as conn:
        # Check recent data
        recent = await conn.fetch('''
            SELECT TOP 5 report_day, report_month, report_year, city_id, period, temp 
            FROM weather 
            ORDER BY report_year DESC, report_month DESC, report_day DESC
        ''')
        print("=== RECENT WEATHER DATA ===")
        for row in recent:
            print(f"  Date: {row['report_year']}-{row['report_month']:02d}-{row['report_day']:02d}, City: {row['city_id']}, Period: {row['period']}, Temp: {row['temp']}°C")
        
        # Check today's data
        today_data = await conn.fetch('''
            SELECT COUNT(*) as cnt 
            FROM weather 
            WHERE report_day=3 AND report_month=12 AND report_year=2025
        ''')
        print(f"\n=== DATA FOR 2025-12-03 ===")
        print(f"Total records: {today_data[0]['cnt']}")
        
        if today_data[0]['cnt'] > 0:
            today_sample = await conn.fetch('''
                SELECT TOP 3 city_id, period, temp, weather_main 
                FROM weather 
                WHERE report_day=3 AND report_month=12 AND report_year=2025
            ''')
            print("Sample records:")
            for row in today_sample:
                print(f"  City: {row['city_id']}, Period: {row['period']}, Temp: {row['temp']}°C, Weather: {row['weather_main']}")

asyncio.run(check_weather_data())
