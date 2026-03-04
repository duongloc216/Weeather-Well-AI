from core.sqlserver_client import get_db
from rag.rule_based import interpret_daily_data_for_single_user_city
from rag.ml_based import predict_health_risk  # 🌟 ML integration
from langchain_core.prompts import ChatPromptTemplate
from core.langchain_local_adapter import LocalEmbeddings, LocalChatModel  # 🌟 Local models (NO Gemini API)
from langchain_chroma import Chroma
from typing import Dict, List
import chromadb
from dotenv import load_dotenv, find_dotenv
import os
import asyncio

load_dotenv('/Users/macbook/Desktop/BangA_DSC2025/.env')
CHROMA_SERVER_HOST = os.environ.get("CHROMA_SERVER_HOST", "103.133.224.14")
CHROMA_SERVER_PORT = int(os.environ.get("CHROMA_SERVER_PORT", 8000))

# Query to get city name by city_id
GET_CITY_NAME_QUERY = "SELECT city_name FROM city WHERE city_id = ?;"

GET_DATA_QUERY_WEATHER_CLIMATE_UV = """
    SELECT
        w.period, w.report_day, w.report_month, w.report_year,
        w.temp, w.feels_like, w.humidity, w.pop, w.wind_speed, w.wind_gust, w.visibility, w.clouds_all,
        w.weather_main, w.weather_description,
        cl.aqi, cl.co, cl.no, cl.no2, cl.o3, cl.so2, cl.pm2_5, cl.pm10, cl.nh3,
        uvid.uvi, w.city_id
    FROM weather w
    JOIN climate cl ON w.city_id = cl.city_id AND w.period = cl.period AND w.report_day = cl.report_day AND w.report_month = cl.report_month AND w.report_year = cl.report_year
    JOIN uv uvid ON w.city_id = uvid.city_id AND w.period = uvid.period AND w.report_day = uvid.report_day AND w.report_month = uvid.report_month AND w.report_year = uvid.report_year
    WHERE
        w.report_day = ? AND w.report_month = ? AND w.report_year = ? AND w.city_id = ?;
"""

# Hàm lấy tên thành phố từ city_id
async def get_city_name(city_id: int) -> str:
    """Lấy tên thành phố từ database theo city_id."""
    pool = await get_db()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(GET_CITY_NAME_QUERY, city_id)
    
    if row:
        return row['city_name']
    return f"thành phố ID {city_id}"

# hàm lấy dữ liệu từ 3 bảng weather, climate, uv
async def get_data_weather_climate_uv(day: int, month: int, year: int, city_id: int):
    print(f"[DEBUG QUERY] Params: day={day}, month={month}, year={year}, city_id={city_id}, type={type(city_id)}")
    pool = await get_db()
    async with pool.acquire() as conn:
        rows = await conn.fetch(GET_DATA_QUERY_WEATHER_CLIMATE_UV, day, month, year, city_id)
    
    print(f"[DEBUG QUERY] Rows returned: {len(rows)}")
    if rows:
        print(f"[DEBUG QUERY] First row sample: period={rows[0].get('period')}, temp={rows[0].get('temp')}")
    
    if not rows:
        return []

    grouped_data = {}
    for row in rows:
        city_id_key = row['city_id']
        if city_id_key not in grouped_data:
            grouped_data[city_id_key] = {
                "city_id": city_id_key,
                "daily_data": []
            }
        
        grouped_data[city_id_key]["daily_data"].append({
            "period": row['period'],
            "report_time": {
                "report_day": row['report_day'],
                "report_month": row['report_month'],
                "report_year": row['report_year'],
            },
            "weather_details": {
                "temp": row['temp'], "feels_like": row['feels_like'], "humidity": row['humidity'],
                "pop": row['pop'], "wind_speed": row['wind_speed'], "wind_gust": row['wind_gust'],
                "visibility": row['visibility'], "clouds_all": row['clouds_all'],
                "weather_main": row['weather_main'], "weather_description": row['weather_description']
            },
            "climate_details": {
                "aqi": row['aqi'], "co": row['co'], "no": row['no'], "no2": row['no2'],
                "o3": row['o3'], "so2": row['so2'], "pm2_5": row['pm2_5'],
                "pm10": row['pm10'], "nh3": row['nh3']
            },
            "uvi_details": {
                "uvi": row['uvi']
            }
        })

    period_order = {
        'Morning': 1, 'Noon': 2, 'Afternoon': 3,
        'Evening': 4, 'Night': 5
    }

    final_data = list(grouped_data.values())[0]
    final_data["daily_data"].sort(key=lambda x: period_order.get(x['period'], 99))
    
    # 🌟 ML-Enhanced Interpretation
    ml_enhanced_interpretations = []
    for period_data in final_data["daily_data"]:
        # Get rule-based interpretation (giữ lại văn phong cũ)
        rule_text = interpret_daily_data_for_single_user_city({"daily_data": [period_data]})[0]
        
        # Get ML prediction
        weather_input = {
            'temp': period_data['weather_details']['temp'],
            'temp_min': period_data['weather_details'].get('temp'),  # fallback
            'temp_max': period_data['weather_details'].get('temp'),  # fallback
            'humidity': period_data['weather_details']['humidity'],
            'precipitation': period_data['weather_details']['pop'],
            'wind_speed': period_data['weather_details']['wind_speed'],
            'uv_index': period_data['uvi_details']['uvi'],
            'pm2_5': period_data['climate_details']['pm2_5'],
            'pm10': period_data['climate_details']['pm10'],
            'aqi': period_data['climate_details']['aqi'],
            'co': period_data['climate_details']['co'],
            'no2': period_data['climate_details']['no2'],
            'o3': period_data['climate_details']['o3'],
            'so2': period_data['climate_details']['so2'],
            'nh3': period_data['climate_details']['nh3']
        }
        
        ml_result = predict_health_risk(weather_input)
        
        # Combine rule-based + ML insights
        top_factors_str = ', '.join([f"{factor['feature']}: {factor['value']}" for factor in ml_result['top_factors'][:3]])
        ml_summary = f"\n\n[ML Health Assessment]: Risk Level = {ml_result['risk_level'].upper()} (Confidence: {ml_result['confidence']:.1f}%). {ml_result['explanation']} Top risk factors: {top_factors_str}."
        
        combined_text = rule_text + ml_summary
        ml_enhanced_interpretations.append(combined_text)
    
    return ml_enhanced_interpretations

#--------------------------------------------------------------------------------------
# hàm lấy dữ liệu tên bệnh của bệnh nhân
GET_DATA_DISEASE = """
    SELECT d.disease_name, u.describe_disease
    FROM users u
    JOIN disease d ON u.disease_id = d.disease_id
    WHERE u.user_id = ?
"""

async def get_name_disease(user_id: int):
    pool = await get_db()
    async with pool.acquire() as conn:
        # Sử dụng fetchrow() để lấy một record duy nhất
        row = await conn.fetchrow(GET_DATA_DISEASE, user_id)
    
    if not row:
        # Trả về None nếu không tìm thấy bệnh
        return None
    
    # Dịch tên bệnh sang tiếng Việt
    disease_translations = {
        "cardiovascular": "bệnh tim mạch",
        "respiratory": "bệnh hô hấp",
        "diabetes": "bệnh tiểu đường",
        "asthma": "hen suyễn",
        "hypertension": "tăng huyết áp",
        "allergies": "dị ứng"
    }
    
    disease_name_en = row['disease_name'].lower()
    disease_name_vi = disease_translations.get(disease_name_en, row['disease_name'])
    
    # row bây giờ là một record, bạn có thể truy cập bằng tên cột
    info = f"""Tên bệnh: {disease_name_vi}.
    Người dùng mô tả tình trạng sức khoẻ của họ như sau: {row['describe_disease']}
     """
    return info

#--------------------------------------------------------------------------------------


# 🌟 NO GEMINI API - Using local models (paraphrase-multilingual-mpnet-base-v2 + Vistral-7B-Chat)
# Không cần API keys, không cần rate limit handling

# Hàm lấy dữ liệu từ vector database
async def get_data_from_vector_database(query_question: str, disease_name: str):
    """
    "disease_name" được dùng làm tham số cho "name_collection"
    🌟 Using LOCAL embedding model (no API keys needed)
    """
    
    try:
        # 🌟 Local embedding model (768D, paraphrase-multilingual-mpnet-base-v2)
        embeddings = LocalEmbeddings()
        print("[RAG] Initialized Local Embeddings model (768D).")

        # Sanitize disease_name to valid ChromaDB collection name (only a-zA-Z0-9._-)
        collection_name = disease_name.strip().replace(' ', '_').replace('\n', '_')
        # Remove any invalid characters
        import re
        collection_name = re.sub(r'[^a-zA-Z0-9._-]', '', collection_name)
        # Ensure starts and ends with alphanumeric
        collection_name = re.sub(r'^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$', '', collection_name)
        print('collection_name:', collection_name)
        vector_store = Chroma(
            client=chromadb.PersistentClient(path='./chroma_data'),
            collection_name=collection_name,
            embedding_function=embeddings
        )

        print(f"[RAG] Initialized Chroma vector store for collection: '{collection_name}'")
        retriever = vector_store.as_retriever(search_kwargs={"k": 1})  # Chỉ lấy 1 doc quan trọng nhất
        # `ainvoke` là phương thức bất đồng bộ để gọi retriever
        retrieved_docs = await retriever.ainvoke(query_question)

        # 5. Hợp nhất các documents thành một đoạn văn bản duy nhất (giới hạn 1000 ký tự)
        retrieved_documents = [doc.page_content[:1000] for doc in retrieved_docs]  # Rút gọn mỗi doc
        context_documents_text = "\n\n".join(retrieved_documents)

        print('[RAG] Đã rút trích thành công từ vector database')
        return context_documents_text

    except Exception as e:
        print(f"[RAG ERROR] Failed to perform RAG: {e}")
        return None