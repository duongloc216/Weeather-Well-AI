import asyncio
import aioodbc

async def check_suggestion_data():
    conn_str = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=localhost\\MSSQLSERVER02;"
        "DATABASE=WeatherWell_AI;"
        "Trusted_Connection=yes;"
    )
    
    try:
        async with aioodbc.connect(dsn=conn_str) as conn:
            async with conn.cursor() as cursor:
                # Đếm tổng số suggestion
                await cursor.execute("SELECT COUNT(*) FROM suggestion")
                count = await cursor.fetchone()
                print(f"📊 Total suggestions: {count[0]}")
                
                # Lấy 5 suggestion mới nhất
                await cursor.execute("""
                    SELECT TOP 5 
                        user_id, 
                        city_id, 
                        LEFT(text_suggestion, 100) as preview
                    FROM suggestion
                    ORDER BY user_id DESC, city_id DESC
                """)
                
                rows = await cursor.fetchall()
                if rows:
                    print("\n📋 Latest suggestions:")
                    for row in rows:
                        print(f"   User {row[0]}, City {row[1]}: {row[2]}...")
                else:
                    print("\n⚠️  Bảng suggestion TRỐNG!")
                
                # Kiểm tra city_id cụ thể
                await cursor.execute("""
                    SELECT COUNT(*) 
                    FROM suggestion 
                    WHERE city_id = 1581129 AND user_id = 1
                """)
                city_count = await cursor.fetchone()
                print(f"\n🔍 Suggestions for city_id=1581129, user_id=1: {city_count[0]}")
                
    except Exception as e:
        print(f"❌ Error: {e}")

asyncio.run(check_suggestion_data())
