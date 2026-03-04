"""
Crawl Historical Weather Data (2024)
Thu thập dữ liệu thời tiết lịch sử từ OpenWeather OneCall API
- Time range: 2024-01-01 đến 2024-12-31
- Cities: Hà Nội (1581130), TP.HCM (1580578)
- Data: weather (temp, humidity, pressure), air pollution (PM2.5, AQI), UV index
"""
import os
import asyncio
import httpx
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pyodbc
from typing import Dict, List

load_dotenv()

# OpenWeather API configuration
OPENWEATHER_API_KEYS = [
    os.getenv("API_OPENWEATHER_0"),
    os.getenv("API_OPENWEATHER_1"),
    os.getenv("API_OPENWEATHER_2")
]

# SQL Server configuration
SQL_SERVER_HOST = os.getenv("SQL_SERVER_HOST")
SQL_SERVER_DATABASE = os.getenv("SQL_SERVER_DATABASE")
SQL_SERVER_USER = os.getenv("SQL_SERVER_USER")
SQL_SERVER_PASSWORD = os.getenv("SQL_SERVER_PASSWORD")
SQL_SERVER_DRIVER = os.getenv("SQL_SERVER_DRIVER")

# Cities to crawl (city_id from OpenWeather)
CITIES = [
    {"id": 1581130, "name": "Hà Nội", "lat": 21.0285, "lon": 105.8542},
    {"id": 1580578, "name": "TP.HCM", "lat": 10.8231, "lon": 106.6297}
]

# Time range (One Call API 3.0 Free tier: only last 5 days)
# For full year: Need to crawl gradually day-by-day from past
# Or use paid Historical Weather API
TODAY = datetime.now()
START_DATE = TODAY - timedelta(days=5)  # Last 5 days (free tier limit)
END_DATE = TODAY - timedelta(days=1)  # Yesterday

# For full 2024 data: Uncomment below (requires subscription or 365 days crawling)
# START_DATE = datetime(2024, 1, 1)
# END_DATE = datetime(2024, 12, 31)

# API key rotation
api_key_index = 0

def get_next_api_key():
    """Rotate through API keys to avoid rate limits"""
    global api_key_index
    key = OPENWEATHER_API_KEYS[api_key_index]
    api_key_index = (api_key_index + 1) % len(OPENWEATHER_API_KEYS)
    return key

def get_db_connection():
    """Create SQL Server connection"""
    conn_str = (
        f"DRIVER={{{SQL_SERVER_DRIVER}}};"
        f"SERVER={SQL_SERVER_HOST};"
        f"DATABASE={SQL_SERVER_DATABASE};"
        f"UID={SQL_SERVER_USER};"
        f"PWD={SQL_SERVER_PASSWORD}"
    )
    return pyodbc.connect(conn_str)

async def fetch_historical_weather(client: httpx.AsyncClient, city: Dict, date: datetime) -> Dict:
    """
    Fetch REAL historical weather data using OpenWeather One Call API 3.0 Time Machine
    
    API: https://openweathermap.org/api/one-call-3#history
    Free tier: 1000 calls/day
    Historical data: Available for past 5 days (timestamp based)
    """
    api_key = get_next_api_key()
    
    # Convert date to Unix timestamp (noon time)
    dt_timestamp = int((date.replace(hour=12, minute=0, second=0)).timestamp())
    
    # OpenWeather One Call API 3.0 Time Machine
    url = "https://api.openweathermap.org/data/3.0/onecall/timemachine"
    
    params = {
        "lat": city["lat"],
        "lon": city["lon"],
        "dt": dt_timestamp,
        "appid": api_key,
        "units": "metric"
    }
    
    try:
        response = await client.get(url, params=params, timeout=15.0)
        response.raise_for_status()
        data = response.json()
        
        # Extract data from 'data' array (hourly data)
        if "data" in data and len(data["data"]) > 0:
            hourly_data = data["data"]
            
            # Calculate daily averages from hourly data
            temps = [h["temp"] for h in hourly_data]
            humidities = [h["humidity"] for h in hourly_data]
            pressures = [h["pressure"] for h in hourly_data]
            wind_speeds = [h["wind_speed"] for h in hourly_data]
            
            weather_data = {
                "city_id": city["id"],
                "date": date.date(),
                "temp": round(sum(temps) / len(temps), 1),
                "temp_min": round(min(temps), 1),
                "temp_max": round(max(temps), 1),
                "humidity": round(sum(humidities) / len(humidities), 1),
                "pressure": round(sum(pressures) / len(pressures), 0),
                "wind_speed": round(sum(wind_speeds) / len(wind_speeds), 1),
                "weather_main": hourly_data[12]["weather"][0]["main"],  # noon weather
                "weather_description": hourly_data[12]["weather"][0]["description"],
                "uv_index": hourly_data[12].get("uvi", 0)  # UV index at noon
            }
            
            return weather_data
        else:
            print(f"   ⚠️ No data returned for {city['name']} on {date.date()}")
            return None
        
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            print(f"   ❌ API key invalid or One Call API 3.0 not enabled")
        elif e.response.status_code == 404:
            print(f"   ⚠️ No data available for {date.date()} (too old?)")
        else:
            print(f"   ❌ HTTP {e.response.status_code} for {city['name']} on {date.date()}")
        return None
    except Exception as e:
        print(f"   ❌ Error for {city['name']} on {date.date()}: {e}")
        return None

async def fetch_air_pollution(client: httpx.AsyncClient, city: Dict) -> Dict:
    """Fetch air pollution data (PM2.5, AQI)"""
    api_key = get_next_api_key()
    
    url = "http://api.openweathermap.org/data/2.5/air_pollution"
    params = {
        "lat": city["lat"],
        "lon": city["lon"],
        "appid": api_key
    }
    
    try:
        response = await client.get(url, params=params, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        
        aqi_data = data["list"][0]
        components = aqi_data["components"]
        
        return {
            "aqi": aqi_data["main"]["aqi"],
            "pm2_5": components.get("pm2_5", 0),
            "pm10": components.get("pm10", 0),
            "no2": components.get("no2", 0),
            "o3": components.get("o3", 0)
        }
        
    except Exception as e:
        print(f"   ⚠️ Air pollution error: {e}")
        return None

def insert_weather_data(conn, data: Dict):
    """Insert weather data into SQL Server"""
    cursor = conn.cursor()
    
    # Check if data already exists
    check_query = """
        SELECT COUNT(*) FROM weather 
        WHERE city_id = ? AND report_year = ? AND report_month = ? AND report_day = ?
    """
    cursor.execute(check_query, data["city_id"], data["date"].year, data["date"].month, data["date"].day)
    exists = cursor.fetchone()[0] > 0
    
    if exists:
        print(f"      ⚠️ Data already exists for {data['date']}, skipping...")
        cursor.close()
        return
    
    query = """
        INSERT INTO weather (city_id, report_year, report_month, report_day, 
                            temperature, humidity, pressure, wind_speed, 
                            weather_main, weather_description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    cursor.execute(query, 
        data["city_id"],
        data["date"].year,
        data["date"].month,
        data["date"].day,
        data["temp"],
        data["humidity"],
        data["pressure"],
        data["wind_speed"],
        data["weather_main"],
        data["weather_description"]
    )
    
    conn.commit()
    cursor.close()

async def crawl_all_data():
    """Main crawling function"""
    print("=" * 70)
    print("CRAWL HISTORICAL WEATHER DATA (2024)")
    print("=" * 70)
    
    # Calculate total days
    total_days = (END_DATE - START_DATE).days + 1
    total_requests = total_days * len(CITIES)
    
    print(f"\n📊 Crawling plan:")
    print(f"   Cities: {len(CITIES)} ({', '.join([c['name'] for c in CITIES])})")
    print(f"   Date range: {START_DATE.date()} → {END_DATE.date()}")
    print(f"   Total days: {total_days}")
    print(f"   Total API calls: {total_requests}")
    print(f"   Estimated time: {total_requests // 60 + 1} minutes (1 call/sec)")
    
    print("\n⚠️  IMPORTANT:")
    print("   OpenWeather One Call API 3.0 Free tier:")
    print("   - Time Machine: Last 5 days only (free)")
    print("   - Full historical: Requires subscription ($175/month)")
    print("\n📋 Options:")
    print("   1. Crawl REAL data (last 5 days) - FREE ✅")
    print("   2. Crawl REAL data (full 2024) - Requires manual enable")
    print("   3. Generate mock data (365 days) - For demo/testing")
    
    choice = input("\n   Chọn option (1/2/3): ")
    
    if choice == "1":
        print("\n   → Crawling REAL data (last 5 days)")
        await crawl_real_historical_data()
    elif choice == "2":
        print("\n   → Crawling full 2024 (check API subscription first)")
        # Modify date range
        global START_DATE, END_DATE
        START_DATE = datetime(2024, 1, 1)
        END_DATE = datetime(2024, 12, 31)
        await crawl_real_historical_data()
    elif choice == "3":
        print("\n   → Generating mock historical data")
        generate_mock_data()
    else:
        print("   Invalid choice")
        return

async def crawl_real_historical_data():
    """Crawl REAL historical weather data from OpenWeather Time Machine API"""
    conn = get_db_connection()
    
    total_days = (END_DATE - START_DATE).days + 1
    completed = 0
    failed = 0
    
    async with httpx.AsyncClient() as client:
        for city in CITIES:
            print(f"\n[City: {city['name']}]")
            
            current_date = START_DATE
            while current_date <= END_DATE:
                # Fetch historical weather
                weather_data = await fetch_historical_weather(client, city, current_date)
                
                if weather_data:
                    insert_weather_data(conn, weather_data)
                    completed += 1
                    print(f"   ✅ {current_date.date()}: {weather_data['temp']}°C, {weather_data['humidity']}%, UV={weather_data.get('uv_index', 'N/A')}")
                else:
                    failed += 1
                
                current_date += timedelta(days=1)
                
                # Rate limiting: 1 call/second (3600 calls/hour, under free limit)
                await asyncio.sleep(1.2)
            
            print(f"   Summary: {completed} success, {failed} failed")
    
    conn.close()
    print(f"\n✅ Crawling completed! Total: {completed} days")
    print(f"   Success rate: {completed/(completed+failed)*100:.1f}%")

def generate_mock_data():
    """Generate mock historical data based on seasonal patterns"""
    print("\n📝 Generating mock data for 2024...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    import random
    
    for city in CITIES:
        print(f"\n[City: {city['name']}]")
        
        current_date = START_DATE
        count = 0
        
        while current_date <= END_DATE:
            month = current_date.month
            
            # Seasonal temperature patterns for Vietnam
            if city["name"] == "Hà Nội":
                # Hà Nội: Cold winter, hot summer
                if month in [12, 1, 2]:  # Winter
                    temp = random.uniform(15, 22)
                    humidity = random.uniform(70, 85)
                elif month in [6, 7, 8]:  # Summer
                    temp = random.uniform(30, 38)
                    humidity = random.uniform(65, 80)
                else:  # Spring/Fall
                    temp = random.uniform(24, 30)
                    humidity = random.uniform(70, 85)
            else:  # TP.HCM
                # TP.HCM: Hot year-round
                if month in [1, 2, 3]:  # Dry season
                    temp = random.uniform(28, 34)
                    humidity = random.uniform(60, 75)
                else:  # Rainy season
                    temp = random.uniform(26, 32)
                    humidity = random.uniform(75, 90)
            
            # Insert mock data
            query = """
                INSERT INTO weather (city_id, report_year, report_month, report_day,
                                    temperature, humidity, pressure, wind_speed,
                                    weather_main, weather_description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            cursor.execute(query,
                city["id"],
                current_date.year,
                current_date.month,
                current_date.day,
                round(temp, 1),
                round(humidity, 1),
                random.randint(1010, 1020),  # Pressure
                random.uniform(2, 8),  # Wind speed
                "Clear" if random.random() > 0.3 else "Clouds",
                "Trời quang đãng" if random.random() > 0.3 else "Có mây"
            )
            
            current_date += timedelta(days=1)
            count += 1
            
            if count % 30 == 0:
                print(f"   Progress: {count}/365 days")
        
        conn.commit()
        print(f"   ✅ Generated {count} days of data")
    
    cursor.close()
    conn.close()
    print("\n✅ Mock data generation completed!")

async def crawl_forecast_data():
    """Crawl 5-day forecast data"""
    print("\n🔮 Crawling forecast data (next 5 days)...")
    
    conn = get_db_connection()
    
    async with httpx.AsyncClient() as client:
        for city in CITIES:
            api_key = get_next_api_key()
            
            url = "https://api.openweathermap.org/data/2.5/forecast"
            params = {
                "lat": city["lat"],
                "lon": city["lon"],
                "appid": api_key,
                "units": "metric",
                "lang": "vi"
            }
            
            try:
                response = await client.get(url, params=params, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                
                print(f"\n[City: {city['name']}]")
                
                for item in data["list"][:40]:  # 5 days × 8 times/day
                    dt = datetime.fromtimestamp(item["dt"])
                    
                    weather_data = {
                        "city_id": city["id"],
                        "date": dt.date(),
                        "temp": item["main"]["temp"],
                        "temp_min": item["main"]["temp_min"],
                        "temp_max": item["main"]["temp_max"],
                        "humidity": item["main"]["humidity"],
                        "pressure": item["main"]["pressure"],
                        "wind_speed": item["wind"]["speed"],
                        "weather_main": item["weather"][0]["main"],
                        "weather_description": item["weather"][0]["description"]
                    }
                    
                    insert_weather_data(conn, weather_data)
                
                print(f"   ✅ Inserted 5-day forecast")
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
            
            await asyncio.sleep(1)
    
    conn.close()
    print("\n✅ Forecast crawling completed!")

if __name__ == "__main__":
    asyncio.run(crawl_all_data())
