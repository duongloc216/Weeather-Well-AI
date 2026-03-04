import redis
import json
import asyncio
import sys
from core.sqlserver_client import get_db

async def push_suggestion_jobs(mode='all'):
    """
    Push suggestion jobs với 3 modes:
    
    1. mode='all': Pre-generate cho TẤT CẢ 60 cities
       → Dùng cho scheduler chạy 12AM mỗi ngày
    
    2. mode='user_city': Chỉ tạo cho cities trong user_city
       → Dùng khi cần sync suggestions cho users hiện tại
    
    3. mode='missing': Tìm missing suggestions và tạo
       → Dùng khi user cập nhật vị trí mới, tự động fill gaps
    """
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    db_pool = await get_db()
    
    async with db_pool.acquire() as conn:
        if mode == 'all':
            # Pre-generate cho TẤT CẢ cities (scheduler 12AM)
            rows = await conn.fetch("""
                SELECT city_id, city_name 
                FROM city 
                ORDER BY city_id
            """)
            
            print(f"🌍 Mode: PRE-GENERATE ALL CITIES")
            print(f"📋 Found {len(rows)} cities in database")
            print("=" * 70)
            
            count = 0
            for row in rows:
                city_id = row['city_id']
                city_name = row['city_name']
                
                # Hardcode user_id=1 cho demo (hoặc push cho tất cả users)
                job_data = {
                    "user_id": 1,
                    "city_id": city_id
                }
                
                r.lpush('queue_passive_suggestion', json.dumps(job_data))
                count += 1
                if count % 10 == 0:
                    print(f"   Pushed {count}/{len(rows)} jobs...")
            
            print("=" * 70)
            print(f"✅ Pushed {count} jobs (ALL cities)")
            print(f"💡 Scheduler sẽ chạy mode này lúc 12AM mỗi ngày")
            
        elif mode == 'user_city':
            # Chỉ tạo cho cities mà users đang follow
            rows = await conn.fetch("""
                SELECT DISTINCT uc.user_id, uc.city_id, c.city_name
                FROM user_city uc
                JOIN city c ON uc.city_id = c.city_id
                ORDER BY uc.user_id, uc.city_id
            """)
            
            if not rows:
                print("⚠️  Bảng user_city TRỐNG!")
                return
            
            print(f"👥 Mode: USER-SPECIFIC CITIES")
            print(f"📋 Found {len(rows)} (user_id, city_id) pairs")
            print("=" * 70)
            
            count = 0
            for row in rows:
                job_data = {
                    "user_id": row['user_id'],
                    "city_id": row['city_id']
                }
                
                r.lpush('queue_passive_suggestion', json.dumps(job_data))
                count += 1
                print(f"✅ [{count:2d}] user_id={row['user_id']}, city_id={row['city_id']:7d} ({row['city_name']})")
            
            print("=" * 70)
            print(f"✅ Pushed {count} jobs (user_city only)")
            
        elif mode == 'missing':
            # Tìm các (user_id, city_id) CHƯA có suggestion hôm nay
            from datetime import datetime
            today = datetime.now()
            today_sql = """
                SELECT uc.user_id, uc.city_id, c.city_name
                FROM user_city uc
                JOIN city c ON uc.city_id = c.city_id
                WHERE NOT EXISTS (
                    SELECT 1 FROM suggestion s
                    WHERE s.user_id = uc.user_id 
                      AND s.city_id = uc.city_id
                      AND s.report_year = ? 
                      AND s.report_month = ? 
                      AND s.report_day = ?
                )
                ORDER BY uc.user_id, uc.city_id
            """
            rows = await conn.fetch(today_sql, today.year, today.month, today.day)
            
            if not rows:
                print("✅ Tất cả users đã có suggestion cho cities của họ!")
                return
            
            print(f"🔍 Mode: FILL MISSING SUGGESTIONS")
            print(f"📋 Found {len(rows)} missing (user_id, city_id) pairs")
            print("=" * 70)
            
            count = 0
            for row in rows:
                job_data = {
                    "user_id": row['user_id'],
                    "city_id": row['city_id']
                }
                
                r.lpush('queue_passive_suggestion', json.dumps(job_data))
                count += 1
                print(f"🆕 [{count:2d}] user_id={row['user_id']}, city_id={row['city_id']:7d} ({row['city_name']})")
            
            print("=" * 70)
            print(f"✅ Pushed {count} missing jobs")
            print(f"💡 Use case: User vừa cập nhật vị trí mới trong user_city")
        
        else:
            print(f"❌ Invalid mode: {mode}")
            print(f"💡 Usage: python push_suggestion_job.py [all|user_city|missing]")
            return
    
    # Queue stats
    queue_length = r.llen('queue_passive_suggestion')
    print(f"\n📊 Current queue length: {queue_length}")
    print(f"⏱️  Estimated time: ~{count * 30} seconds ({count} jobs × 30s/job)")

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else 'missing'
    asyncio.run(push_suggestion_jobs(mode))
