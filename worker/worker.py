import os
import pandas as pd
from core.redis_client import get_redis_data
from dotenv import load_dotenv
from .weather import aggregate_weather_by_period # dấu chấm thể hiện module cùng cấp
from .climate import process_air_pollution_by_period
from .uv import aggregate_uv_by_period
from core.sqlserver_client import get_db
import asyncio
import json, traceback
import httpx
import redis.asyncio as redis
from redis.exceptions import ResponseError, ConnectionError, TimeoutError
import time

# FIX: Load .env từ thư mục gốc project (không hardcode path)
load_dotenv()
QUEUE_DATA = os.getenv("QUEUE_DATA", "queue_data")
API_KEYS = [k.strip() for k in os.getenv("OPEN_WEATHER_API", "").split(",") if k.strip()]  # POOL API KEY OPEN_WEATHER
BASE_BACKOFF = float(os.getenv("BASE_BACKOFF", 1.0))  # seconds
MAX_RETRY = int(os.getenv("MAX_RETRY", 5))

# track API key status
api_key_pool = [{"key": k.strip(), "blocked_until": 0} for k in API_KEYS] # thêm pool apikey vào
current_index = 0

async def get_next_key():
    """
    Lấy key tiếp theo chưa bị block. Nếu tất cả blocked, sleep thời gian nhỏ nhất.
    """
    global current_index
    n = len(api_key_pool)
    start_index = current_index
    while True:
        key_info = api_key_pool[current_index]
        current_index = (current_index + 1) % n
        if key_info["blocked_until"] <= asyncio.get_event_loop().time():
            return key_info, None

        if current_index == start_index:
            # tất cả key đang block
            sleep_time = min(k["blocked_until"] - asyncio.get_event_loop().time() for k in api_key_pool)
            sleep_time = max(sleep_time, 0.1)
            print(f"[Worker] All keys blocked. Sleeping {sleep_time:.2f}s")
            return None, sleep_time

# hàm này chỉ dùng cho uv_index
async def fetch_api_uv(url, params): 
    """Gọi API Air Pollution Forecast và trả về JSON"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)

        if response.status_code == 200:
            return response.json()
        else:
            print("Lỗi API:", response.status_code, response.NVARCHAR(MAX))
            return None
    except httpx.RequestError as e:
        print(f"Lỗi kết nối API: {e}")
        return None

# ta sẽ xử lý xoay api ở đây
async def fetch_api(url, params):
    """
    Gọi API với xoay API key từ pool. 
    Nếu gặp 429 thì block key đó một thời gian rồi thử key khác.
    """
    global api_key_pool
    retry = 0
    while retry < MAX_RETRY:
        key_info, sleep_time = await get_next_key()
        if key_info is None:
            await asyncio.sleep(sleep_time)  # tất cả key block → chờ rồi thử lại
            continue

        params["appid"] = key_info["key"]
        api_key_suffix = key_info["key"][-8:]  # Hiển thị 8 ký tự cuối để debug
        
        try:
            # FIX: Tăng timeout và thêm retry cho connection
            timeout_config = httpx.Timeout(60.0, connect=30.0)  # 60s total, 30s connect
            async with httpx.AsyncClient(timeout=timeout_config) as client:
                response = await client.get(url, params=params)

            if response.status_code == 200:
                # print(f"[Worker] API success với key ...{api_key_suffix}")  # Uncomment để debug
                return response.json()

            elif response.status_code == 429:
                # rate-limit → block key trong 60s
                block_time = 60
                key_info["blocked_until"] = asyncio.get_event_loop().time() + block_time
                print(f"[Worker] Key ...{api_key_suffix} bị rate-limit → block {block_time}s, chuyển sang key khác")
                retry += 1
                await asyncio.sleep(BASE_BACKOFF)  # Chờ ngắn trước khi thử key khác
                continue

            else:
                print(f"[Worker] API lỗi {response.status_code}: {response.text}")
                retry += 1
                await asyncio.sleep(BASE_BACKOFF * retry)

        except (httpx.RequestError, httpx.ConnectTimeout, httpx.ReadTimeout) as e:
            print(f"[Worker] Exception khi gọi API (retry {retry+1}/{MAX_RETRY}): {e}")
            retry += 1
            
            # Nếu lỗi kết nối → thử key khác ngay (không block key này)
            if retry < MAX_RETRY:
                print(f"[Worker] Chuyển sang API key khác...")
                await asyncio.sleep(BASE_BACKOFF)  # Chờ ngắn trước khi thử key khác
                continue
            else:
                # Hết retry → backoff lâu hơn
                await asyncio.sleep(BASE_BACKOFF * retry)

    print("[Worker] Gọi API thất bại sau nhiều lần thử.")
    print(f"[Worker] Đã thử {len(api_key_pool)} API keys với tổng {MAX_RETRY} lần retry")
    return None


async def insert_weather(data_weather: pd.DataFrame):
    # rename cho khớp schema table in database
    data_weather = data_weather.rename(columns={
        "year": "report_year",
        "month": "report_month",
        "day": "report_day"
    })

    # reorder đúng thứ tự cột trong DB
    data_weather = data_weather[
        [
            "city_id",
            "report_year",
            "report_month",
            "report_day",
            "period",
            "temp",
            "feels_like",
            "humidity",
            "pop",
            "rain_3h",
            "wind_speed",
            "wind_gust",
            "visibility",
            "clouds_all",
            "weather_main",
            "weather_description",
            "weather_icon",
        ]
    ]
    
    # FIX: Replace NULL/NaN/empty values cho các cột số
    numeric_columns = ["temp", "feels_like", "humidity", "pop", "rain_3h", 
                       "wind_speed", "wind_gust", "visibility", "clouds_all"]
    for col in numeric_columns:
        if col in data_weather.columns:
            data_weather[col] = data_weather[col].fillna(0.0)  # Replace NaN with 0
            data_weather[col] = data_weather[col].replace('', 0.0)  # Replace empty string
            data_weather[col] = pd.to_numeric(data_weather[col], errors='coerce').fillna(0.0)  # Coerce invalid to 0
    
    # FIX: Replace NULL cho string columns
    string_columns = ["period", "weather_main", "weather_description", "weather_icon"]
    for col in string_columns:
        if col in data_weather.columns:
            data_weather[col] = data_weather[col].fillna('')  # Replace NaN with empty string
            data_weather[col] = data_weather[col].astype(str).replace('nan', '')  # Replace 'nan' string

    pool = await get_db()
    async with pool.acquire() as conn:
        records = list(data_weather.itertuples(index=False, name=None))
        placeholders = ','.join(['?' for _ in data_weather.columns])
        columns_str = ','.join(data_weather.columns)
        query = f"INSERT INTO weather ({columns_str}) VALUES ({placeholders})"
        await conn.executemany(query, records)

    print(f"[Worker] Đã insert {len(records)} rows weather cho city_id {data_weather['city_id'].iloc[0]}")

# hàm thêm dữ liệu vào bảng climate
async def insert_climate(data_climate: pd.DataFrame):
    # rename cho khớp schema table in database
    data_climate = data_climate.rename(columns={
        "year": "report_year",
        "month": "report_month",
        "day": "report_day"
    })

    # reorder đúng thứ tự cột trong DB
    data_climate = data_climate[
        [
            "city_id",
            "report_year",
            "report_month",
            "report_day",
            "period",
            "aqi",
            "co",
            "no",
            "no2",
            "o3",
            "so2",
            "pm2_5",
            "pm10",
            "nh3"
        ]
    ]

    pool = await get_db()
    async with pool.acquire() as conn:
        records = list(data_climate.itertuples(index=False, name=None))
        placeholders = ','.join(['?' for _ in data_climate.columns])
        columns_str = ','.join(data_climate.columns)
        query = f"INSERT INTO climate ({columns_str}) VALUES ({placeholders})"
        await conn.executemany(query, records)

    print(f"[Worker] Đã insert {len(records)} rows climate cho city_id {data_climate['city_id'].iloc[0]}")

# hàm insert vào bảng UV
async def insert_uv(data_uv: pd.DataFrame):
    # rename cho khớp schema table in database
    data_uv = data_uv.rename(columns={
        "year": "report_year",
        "month": "report_month",
        "day": "report_day"
    })

    # reorder đúng thứ tự cột trong DB
    data_uv = data_uv[
        [
            "city_id",
            "report_year",
            "report_month",
            "report_day",
            "period",
            "uvi"
        ]
    ]

    pool = await get_db()
    async with pool.acquire() as conn:
        records = list(data_uv.itertuples(index=False, name=None))
        placeholders = ','.join(['?' for _ in data_uv.columns])
        columns_str = ','.join(data_uv.columns)
        query = f"INSERT INTO uv ({columns_str}) VALUES ({placeholders})"
        await conn.executemany(query, records)

    print(f"[Worker] Đã insert {len(records)} rows uv index cho city_id {data_uv['city_id'].iloc[0]}")


async def process_job(job_data):
    # lấy ra các tham số từ job_data 
    city_id = job_data["city_id"]
    longitude = job_data["longitude"]
    latitude = job_data["latitude"]
    job_id = job_data["job_id"]
    print(f"[Worker] Processing job {job_id} for city_id '{city_id}'")


    pool = await get_db()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT TOP 1 1 FROM weather WHERE city_id = ?", city_id
        )
    if row:
        print(f"[Worker] city_id {city_id} đã tồn tại trong bảng weather → skip")
        return  # không crawl nữa
    # crawl weather
    print(f"crawling weather data.....")    
    url_weather = "https://api.openweathermap.org/data/2.5/forecast"
    params_weather = { # không cần khai báo thêm key vì hàm fetch_api sẽ chịu trách nhiệm thêm và xoay api
        "id": city_id,
        "units": "metric",  # nhiệt độ Celsius
        "lang": "vi"        # ngôn ngữ tiếng Việt
    }
    response_weather = await fetch_api(url_weather, params_weather)
    if response_weather is None:
        print(f"[Worker] Không lấy được dữ liệu weather cho city_id {city_id}")
        return
    data_weather = aggregate_weather_by_period(response_weather)
    if data_weather.empty:
        print(f"[Worker] Weather data cho city_id {city_id} bị rỗng → skip insert")
    else:
        await insert_weather(data_weather)  # chỉ insert khi có dữ liệu

    # crawl climate
    print(f"crawling climate data.....")
    url_climate = "http://api.openweathermap.org/data/2.5/air_pollution/forecast"
    params_climate = { # không cần khai báo thêm key vì hàm fetch_api sẽ chịu trách nhiệm thêm và xoay api
        "lat": latitude,
        "lon": longitude,
    }
    response_climate = await fetch_api(url_climate,params_climate)
    if response_climate is None:
        print(f"[Worker] Không lấy được dữ liệu climate cho city_id {city_id}")
        return
    data_climate = process_air_pollution_by_period(response_climate)
    if data_climate.empty:
        print(f"[Worker] Climate data cho city_id {city_id} bị rỗng → skip insert")
    else:
        data_climate["city_id"] = city_id
        await insert_climate(data_climate)

    # crawl uv index
    print(f"crawling uv index data.....")
    url_uv = "https://currentuvindex.com/api/v1/uvi"
    params_uv = {
        "latitude": latitude,
        "longitude": longitude
    }
    response_uv = await fetch_api_uv(url_uv,params_uv)
    if response_uv is None:
        print(f"[Worker] Không lấy được dữ liệu uv_index cho city_id {city_id}")
        return
    data_uv = aggregate_uv_by_period(response_uv)

    if data_uv.empty:
        print(f"[Worker] UV data cho city_id {city_id} bị rỗng → skip insert")
    else:
        data_uv["city_id"] = city_id
        await insert_uv(data_uv)


PING_INTERVAL = 1800  # 30 phút ping Redis 1 lần
async def worker_loop():
    global redis_data
    redis_data = await get_redis_data()
    print("[Worker] Started worker loop...")
    last_ping = time.time()
    while True:
        if time.time() - last_ping > PING_INTERVAL:
            try:
                pong = await redis_data.ping()
                if pong is True:
                    print("[Worker] Redis ping OK")
                else:
                    print("[Worker] Redis ping failed → reconnecting")
                    redis_data = await get_redis_data()
            except Exception as e:
                print(f"[Worker] Redis ping error: {e} → reconnecting")
                redis_data = await get_redis_data()
            last_ping = time.time()

        try:

            if redis_data is None:
                redis_data = await get_redis_data()

            job_json = await redis_data.brpop(QUEUE_DATA, timeout=5)
        except ResponseError as e:
            print(f"[Worker] BRPOP was force-unblocked, retrying... {e}")
            await asyncio.sleep(0.5)
            continue

        except (ConnectionError, TimeoutError) as e:
            print(f"[Worker] Redis connection lost: {e}. Reconnecting...")
            redis_data = None  # force reconnect
            traceback.print_exc()
            await asyncio.sleep(1)
            continue

        except Exception as e:
            print(f"[Worker] Unexpected error during BRPOP: {e}")
            traceback.print_exc()
            await asyncio.sleep(1)
            continue

        if job_json is None:
            continue

        _, job_str = job_json
        job_data = json.loads(job_str)

        try:
            await process_job(job_data) # city_id, longitude, latitude
        except Exception as e:
            print(f"[Worker] Error in worker loop for job {job_data.get('job_id')}: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(worker_loop())
    except KeyboardInterrupt:
        print("\n[Worker] Stopped by user (Ctrl+C)")


# python -m worker.worker