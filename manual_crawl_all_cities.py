"""
Script để crawl dữ liệu thời tiết cho TẤT CẢ các thành phố trong database.
Chạy script này TRƯỚC KHI DEMO để đảm bảo có đầy đủ dữ liệu.

Usage:
    python manual_crawl_all_cities.py
"""

import asyncio
import json
import uuid
from core.sqlserver_client import get_db
from core.redis_client import get_redis_data
from dotenv import load_dotenv
import os

load_dotenv()

QUEUE_DATA = os.getenv("QUEUE_DATA", "queue_data")


async def get_all_cities():
    """
    Lấy TẤT CẢ các thành phố từ bảng city (không chỉ user_city).
    Trả về danh sách (city_id, city_name, longitude, latitude).
    """
    pool = await get_db()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT city_id, city_name, longitude, latitude
            FROM city
            WHERE longitude IS NOT NULL AND latitude IS NOT NULL
            ORDER BY city_id
        """)
        return rows


async def push_crawl_jobs_for_all_cities():
    """
    Push job crawl cho TẤT CẢ các thành phố vào Redis queue.
    Worker sẽ tự động xử lý các job này.
    """
    redis_data = await get_redis_data()
    cities = await get_all_cities()
    
    if not cities:
        print("[ERROR] Không tìm thấy thành phố nào trong database!")
        return
    
    print(f"\n🌍 Tìm thấy {len(cities)} thành phố trong database")
    print("=" * 60)
    
    pushed_count = 0
    for city in cities:
        job_data = {
            "job_id": str(uuid.uuid4()),
            "city_id": city["city_id"],
            "longitude": city["longitude"],
            "latitude": city["latitude"]
        }
        
        await redis_data.lpush(QUEUE_DATA, json.dumps(job_data))
        pushed_count += 1
        
        print(f"✅ [{pushed_count}/{len(cities)}] Pushed: {city['city_name']} (ID: {city['city_id']})")
    
    print("=" * 60)
    print(f"\n🎉 Đã push {pushed_count} jobs vào queue '{QUEUE_DATA}'")
    print(f"📋 Worker sẽ tự động crawl dữ liệu cho tất cả các thành phố")
    print(f"⏱️  Thời gian ước tính: ~{pushed_count * 2} giây (2s/thành phố)")
    print(f"\n💡 Kiểm tra tiến độ bằng lệnh:")
    print(f"   redis-cli LLEN {QUEUE_DATA}")


async def clear_old_weather_data():
    """
    Xóa dữ liệu cũ trong bảng weather, climate, uv trước khi crawl mới.
    """
    pool = await get_db()
    async with pool.acquire() as conn:
        # SQL Server không dùng conn.transaction(), chỉ execute trực tiếp
        await conn.execute("DELETE FROM weather;")
        await conn.execute("DELETE FROM climate;")
        await conn.execute("DELETE FROM uv;")
        print("🗑️  Đã xóa dữ liệu cũ từ weather, climate, uv")


async def main():
    print("\n" + "=" * 60)
    print("  MANUAL CRAWL - Crawl dữ liệu cho TẤT CẢ thành phố")
    print("=" * 60)
    
    # Bước 1: Hỏi xác nhận xóa data cũ
    print("\n⚠️  Bạn có muốn XÓA dữ liệu cũ trước khi crawl không?")
    print("   [Y] Xóa dữ liệu cũ (khuyến nghị nếu muốn data mới hoàn toàn)")
    print("   [N] Giữ dữ liệu cũ (chỉ cập nhật thành phố chưa có data)")
    
    choice = input("\nLựa chọn (Y/N): ").strip().upper()
    
    if choice == "Y":
        print("\n🔄 Đang xóa dữ liệu cũ...")
        await clear_old_weather_data()
    else:
        print("\n✅ Giữ dữ liệu cũ, chỉ crawl các thành phố thiếu data")
    
    # Bước 2: Push jobs vào Redis queue
    print("\n🔄 Đang push jobs vào Redis queue...")
    await push_crawl_jobs_for_all_cities()
    
    print("\n✅ HOÀN TẤT! Worker đang xử lý các job crawl.")
    print("📊 Theo dõi tiến độ:")
    print("   1. Kiểm tra queue: redis-cli LLEN queue_data")
    print("   2. Kiểm tra DB: SELECT COUNT(*) FROM weather;")
    print("   3. Xem log worker ở terminal đang chạy worker")


if __name__ == "__main__":
    asyncio.run(main())
