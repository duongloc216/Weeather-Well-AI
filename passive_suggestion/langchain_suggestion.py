from core.sqlserver_client import get_db
from langchain_core.prompts import ChatPromptTemplate
from core.langchain_local_adapter import LocalEmbeddings, LocalChatModel
from langchain_chroma import Chroma
from typing import Dict, List
import asyncio
import json
import chromadb
from dotenv import load_dotenv, find_dotenv
import os
from .create_query_question import make_query_question

load_dotenv()
CHROMA_SERVER_HOST = os.environ.get("CHROMA_SERVER_HOST", "localhost")
CHROMA_SERVER_PORT = int(os.environ.get("CHROMA_SERVER_PORT", 8000))

# 🌟 NO GEMINI API - Using local models (paraphrase-multilingual-mpnet-base-v2 + Vistral-7B-Chat)
# Không cần API keys, không cần rate limit handling

async def rag_for_suggestion(job_data: dict):
    """
    Thực hiện quy trình RAG để tạo gợi ý sức khỏe hoàn chỉnh bằng LLM.
    
    Args:
        job_data (Dict): Dữ liệu job từ Redis chứa thông tin user, city và daily data.

    Returns:
        Lưu thông tin vào bảng suggestion
    """

    try:
        # Lấy thông tin cần thiết từ job_data
        user_id = job_data.get('user_id')
        city_id = job_data.get('city_id')
        
        # Kiểm tra xem user_id và city_id có tồn tại không
        if user_id is None or city_id is None:
            print("ERROR: Dữ liệu job_data không chứa user_id hoặc city_id.")
            return

        # Nếu job_data đã có daily_data (từ scheduler), dùng luôn
        # Nếu không (manual trigger), query database lấy dữ liệu hôm nay
        if 'daily_data' in job_data and job_data['daily_data']:
            first_daily_data = job_data['daily_data'][0]
            report_time = first_daily_data.get('report_time')
            report_year = report_time.get('report_year')
            report_month = report_time.get('report_month')
            report_day = report_time.get('report_day')
        else:
            # Manual trigger: lấy dữ liệu ngày hôm nay
            from datetime import datetime
            now = datetime.now()
            report_year, report_month, report_day = now.year, now.month, now.day
            
            # Query database để tạo daily_data structure
            from scheduler.queries import GET_FULL_DATA_QUERY
            pool = await get_db()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    GET_FULL_DATA_QUERY, 
                    report_day, report_month, report_year,
                    report_day, report_month, report_year,
                    report_day, report_month, report_year
                )
            
            if not rows:
                print(f"ERROR: Không có dữ liệu cho user {user_id}, city {city_id} ngày {report_day}/{report_month}/{report_year}")
                return
            
            # Filter rows for this user/city
            user_rows = [r for r in rows if r['user_id'] == user_id and r['city_id'] == city_id]
            if not user_rows:
                print(f"ERROR: Không có dữ liệu cho user {user_id}, city {city_id}")
                return
            
            # Build daily_data structure
            job_data['daily_data'] = [{
                'report_time': {'report_year': report_year, 'report_month': report_month, 'report_day': report_day},
                'periods': []
            }]
            
            for row in user_rows:
                job_data['daily_data'][0]['periods'].append({
                    'period': row['period'],
                    'weather_details': {
                        'temp': row['temp'], 'feels_like': row['feels_like'], 'humidity': row['humidity'],
                        'pop': row['pop'], 'wind_speed': row['wind_speed'], 'wind_gust': row.get('wind_gust'),
                        'visibility': row.get('visibility'), 'clouds_all': row['clouds_all'], 
                        'weather_main': row['weather_main'], 'weather_description': row['weather_description']
                    },
                    'climate_details': {
                        'aqi': row['aqi'], 'pm2_5': row['pm2_5'], 'pm10': row['pm10'],
                        'co': row['co'], 'no2': row['no2'], 'o3': row['o3'],
                        'so2': row['so2'], 'nh3': row['nh3']
                    },
                    'uvi_details': {'uvi': row['uvi']}
                })
            
            job_data['disease_name'] = user_rows[0]['disease_name']
            job_data['describe_disease'] = user_rows[0]['describe_disease']

        query_question, describe_disease = make_query_question(job_data) # vừa lấy query question lẫn describe_disease sau khi translate

        # 2. Khởi tạo local embedding model (no API key needed)
        embeddings = LocalEmbeddings()
        print("[RAG] Initialized Local Embeddings model (768D).")
        
        # 3. Khởi tạo Chroma vector store với client và embedding model
        collection_name = job_data.get('disease_name', 'respiratory')
        print('collection_name:', collection_name)
        vector_store = Chroma(
            client=chromadb.PersistentClient(path='./chroma_data'),
            collection_name=collection_name,
            embedding_function=embeddings
        )

        print(f"[RAG] Initialized Chroma vector store for collection: '{collection_name}'")

        # 4. Thực hiện tìm kiếm bất đồng bộ với retriever
        # `as_retriever` sẽ biến vector store thành một đối tượng có thể tìm kiếm
        # `k=5` sẽ tìm kiếm 5 tài liệu gần nhất

        retriever = vector_store.as_retriever(search_kwargs={"k": 2})
        # `ainvoke` là phương thức bất đồng bộ để gọi retriever
        retrieved_docs = await retriever.ainvoke(query_question)

        # 5. Hợp nhất các documents thành một đoạn văn bản duy nhất
        retrieved_documents = [doc.page_content for doc in retrieved_docs]                
        context_documents_text = "\n\n".join(retrieved_documents)
        
        # 6. Xây dựng prompt và gọi local LLM để tạo phản hồi
        llm = LocalChatModel(
            temperature=0.7,
            max_output_tokens=512  # Reduced from 4096 for faster generation
        )

        disease_name = job_data.get('disease_name', 'disease')

        # ==============================================================================
        # PROMPT - TUYỆT ĐỐI KHÔNG CHO PHÉP THÊM GIỜ
        # ==============================================================================
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", 
                f"You are a specialist doctor for the '{disease_name}' disease. Based on the following information, provide useful health advice for a user with this disease. "
                "Focus on the provided weather, climate, and UV factors. Your response must be clear, concise, and only focus on providing advice. "
                "Do not mention that you used documents to answer. "
                "Reference information:\n{{context}}"
            ),
            ("human", 
                f"Based on weather data: {{query_question}}\n\n"
                f"Patient condition: {{describe_disease}}\n\n"
                f"Provide health advice in Vietnamese. Use ONLY these period names WITHOUT any time information:\n"
                f"- Sáng sớm: [advice]\n"
                f"- Buổi sáng: [advice]\n"
                f"- Buổi trưa: [advice]\n"
                f"- Buổi chiều: [advice]\n"
                f"- Buổi tối: [advice]\n\n"
                f"CRITICAL: Write ONLY period name + colon + advice. NO time ranges like (05:00-12:00). NO parentheses. NO numbers after period names."
            )
        ])
            
        # 7. Tạo chain và gọi LLM
        llm_chain = prompt_template | llm
        
        final_response = await llm_chain.ainvoke({
            "context": context_documents_text,
            "query_question": query_question,
            "disease_name": disease_name,
            "describe_disease": describe_disease
        })
        
        # kiểm tra xem có đang bị cut do MAX TOKEN không
        if hasattr(final_response, "response_metadata"):  # Nếu object có metadata
            finish_reason = final_response.response_metadata.get("finish_reason", "")
        if finish_reason != "STOP":  # Nếu không phải STOP
            print(f"[LLM WARNING] Response cut off, finish_reason={finish_reason}")

        print("\n[LLM Response] Generated final response.")
        if hasattr(final_response, "content") and final_response.content:
            text_suggestion = final_response.content
        else:
            print("[LLM WARNING] Empty content, fallback to raw response")
            text_suggestion = json.dumps(final_response.dict(), ensure_ascii=False)
        
        print('check_response_object (RAW): ', text_suggestion)
        
        # Post-processing: XÓA TRIỆT ĐỂ MỌI DẠNG KHUNG GIỜ
        import re
        
        # Bước 1: Xóa toàn bộ nội dung trong ngoặc đơn ngay sau tên buổi
        # "Buổi sáng (bất kỳ nội dung gì):" → "Buổi sáng:"
        text_suggestion = re.sub(
            r'(Sáng\s+sớm|Buổi\s+(?:sáng|trưa|chiều|tối))\s*\([^)]*\)\s*:',
            r'\1:',
            text_suggestion
        )
        
        # Bước 2: Xóa các pattern số giờ rời rạc: "00 - 12:00):" hoặc "05:00 - 12:00"
        text_suggestion = re.sub(r'\d{1,2}\s*-\s*\d{1,2}:\d{2}\)?\s*:', '', text_suggestion)
        text_suggestion = re.sub(r'\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}', '', text_suggestion)
        
        # Bước 3: Xóa mọi ngoặc đơn còn sót
        text_suggestion = re.sub(r'\([^)]*\)', '', text_suggestion)
        
        # Bước 4: Xóa mọi số giờ đơn lẻ còn sót: "05:00", "12:00", "18:00"
        text_suggestion = re.sub(r'\b\d{1,2}:\d{2}\b', '', text_suggestion)
        
        # Bước 5: Làm sạch dấu : thừa và whitespace
        text_suggestion = re.sub(r':\s*:', ':', text_suggestion)  # :: → :
        text_suggestion = re.sub(r'\s+', ' ', text_suggestion)  # Multiple spaces → 1
        text_suggestion = re.sub(r'\n{3,}', '\n\n', text_suggestion)  # Multiple newlines → 2
        text_suggestion = text_suggestion.strip()
        
        # Fallback if empty
        if len(text_suggestion) < 50:
            text_suggestion = "Dữ liệu thời tiết hôm nay không đủ để đưa ra lời khuyên chi tiết. Vui lòng theo dõi sức khỏe và liên hệ bác sĩ nếu có triệu chứng bất thường."
        
        print('check_response_object (FINAL): ', text_suggestion)
        pool = await get_db()
        async with pool.acquire() as conn:
            insert_query = """
                MERGE INTO suggestion AS target
                USING (SELECT ? AS user_id, ? AS city_id) AS source
                ON target.user_id = source.user_id AND target.city_id = source.city_id
                WHEN MATCHED THEN
                    UPDATE SET text_suggestion = ?, report_year = ?, report_month = ?, report_day = ?
                WHEN NOT MATCHED THEN
                    INSERT (user_id, city_id, text_suggestion, report_year, report_month, report_day)
                    VALUES (?, ?, ?, ?, ?, ?);
            """
            await conn.execute(
                insert_query,
                user_id, city_id,  # source values for USING
                text_suggestion, report_year, report_month, report_day,  # UPDATE values
                user_id, city_id, text_suggestion, report_year, report_month, report_day  # INSERT values
            )
        print('Already Insert to Database')
        return
    except Exception as e:
        print(f"[RAG ERROR] Failed to perform RAG for job: {e}")
        import traceback
        traceback.print_exc()
        return


