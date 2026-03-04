import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import asyncio
from core.langchain_local_adapter import LocalChatModel
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from .tool_agent import get_data_weather_climate_uv, get_name_disease, get_data_from_vector_database, get_city_name
from dotenv import load_dotenv, find_dotenv
from core.redis_client import get_redis_data, get_redis_cache_conn, get_redis_history_conn
import json
import traceback
from backend.storage_history_message import append_chat_history
import redis.asyncio as redis
import time
from redis.exceptions import ResponseError, ConnectionError, TimeoutError


load_dotenv()
QUEUE_CHATBOT = os.getenv("QUEUE_CHATBOT", "queue_chatbot")

# 🌟 NO GEMINI API - Using local Vistral-7B-Chat model
# Không cần API keys, không cần key rotation

# tool lấy dữ liệu thời tiết, climate, uv
@tool
async def get_weather_report(dates: list[dict], city_id: int):
    """
    Truy vấn cơ sở dữ liệu để lấy và diễn giải dữ liệu thời tiết cho các ngày và thành phố cụ thể.
    Dùng công cụ này khi người dùng hỏi về thời tiết, chất lượng không khí, hoặc chỉ số UV.

    Args:
        dates (list[dict]): Danh sách các từ điển, mỗi từ điển biểu diễn một ngày.
                            Mỗi từ điển phải có các khóa sau:
                            - 'day' (int): Ngày trong tháng (ví dụ: 17).
                            - 'month' (int): Tháng trong năm (ví dụ: 9).
                            - 'year' (int): Năm (ví dụ: 2025).
        city_id (int): ID của thành phố để lấy dữ liệu.
    """
    print(f"\n--- Công cụ 'get_weather_report' được gọi với các ngày: {dates} và city_id: {city_id} ---")
    
    reports = []
    for date_data in dates:
        day = date_data['day']
        month = date_data['month']
        year = date_data['year']
        
        # Hàm get_data_weather_climate_uv bây giờ trả về một danh sách các chuỗi
        daily_interpretations_list = await get_data_weather_climate_uv(day, month, year, city_id)
        
        if daily_interpretations_list:
            # 🌟 Sửa lỗi ở đây: Nối các chuỗi trong danh sách lại
            daily_interpretation = "\n".join(daily_interpretations_list)
            reports.append(f"Ngày {day}/{month}/{year}:\n{daily_interpretation}")
        else:
            reports.append(f"Ngày {day}/{month}/{year}: Không có dữ liệu.")
            
    return reports

# tool lấy dữ liệu bệnh lý
@tool
async def get_user_disease_info(user_id: int):
    """
    Truy vấn cơ sở dữ liệu để lấy thông tin về bệnh lý và tình trạng sức khỏe của người dùng.
    
    Sử dụng tool này nếu cần biết về thông tin bệnh lý của người dùng. Tool này trả về tên bệnh và mô tả tình trạng sức khoẻ
    mà người dùng đã cung cấp.

    Args:
        user_id (int): ID của người dùng để truy vấn thông tin.
    """
    response_text = await get_name_disease(user_id)
    if response_text is None: return "không có dữ liệu"
    return response_text

@tool
async def retrieve_health_guideline(query_question: str, disease_name: str):
    """
    Truy vấn cơ sở dữ liệu vector để tìm kiếm các tài liệu học thuật chi tiết
    về mối liên hệ giữa các yếu tố môi trường (thời tiết, khí hậu, UV) và bệnh lý của người dùng.
    
    Sử dụng tool này khi người dùng hỏi các câu hỏi chi tiết về mối quan hệ giữa
    thời tiết hoặc khí hậu và một bệnh cụ thể. Ví dụ: "Làm thế nào để phòng tránh tác động của tia UV
    đối với bệnh dị ứng?", hoặc "Không khí ô nhiễm có làm trầm trọng thêm
    bệnh hen suyễn không?".
    Args:
        query_question (str): Câu hỏi chi tiết của người dùng cần được truy vấn.
        disease_name (str): Tên bệnh của người dùng được lấy từ tool "get_user_disease_info". 
        Vì nó chính là collection name cần truy xuất
    """
    response_text = await get_data_from_vector_database(query_question, disease_name)
    if response_text is None: return "không có dữ liệu"
    return response_text

async def agent_process(city_id_from_fastapi: int, user_id_from_fastapi: int, input_from_user: str, history_context: str ):
    """Xử lý request chatbot bằng local Vistral-7B model."""
    
    try:
            # Lấy ngày hiện tại ở múi giờ Việt Nam
            vietnam_timezone = ZoneInfo("Asia/Ho_Chi_Minh")
            now_vietnam = datetime.now(vietnam_timezone)
            current_date_str = now_vietnam.strftime("%Y-%m-%d")

            # Khởi tạo local Qwen model (no API key needed)
            # Temperature 0.3: Vừa đủ đa dạng nhưng vẫn chính xác
            llm = LocalChatModel(temperature=0.3, max_output_tokens=512)

            # Định nghĩa các công cụ mà agent có thể sử dụng
            tools_list = [get_weather_report, get_user_disease_info, retrieve_health_guideline]

            # Lấy tên thành phố từ city_id
            city_name = await get_city_name(city_id_from_fastapi)
            
            # Định nghĩa prompt cho agent
            prompt = ChatPromptTemplate.from_messages([
                ("system", f"""Bạn là một trợ lý sức khỏe và thời tiết thông minh.
                Mục tiêu của bạn là cung cấp lời khuyên cá nhân hóa, dựa trên dữ liệu thời tiết, thông tin bệnh lý và các kiến thức tham khảo.
                Hãy luôn trả lời một cách hữu ích, dễ hiểu và chuyên nghiệp bằng ngôn ngữ *Tiếng Việt*.
                Hôm nay là {current_date_str}.
                Thành phố của người dùng là: {city_name}.
                
                FORMAT TRẢ LỜI:
                - BẮT BUỘC sử dụng format số thứ tự (1., 2., 3., ...) cho mỗi lời khuyên.
                - Mỗi ý là một điểm riêng biệt, xuống dòng rõ ràng.
                - Câu mở đầu: "Dựa trên dữ liệu thời tiết và thông tin sức khỏe của bạn, tôi có một số lời khuyên cho [ngày]:"
                
                QUAN TRỌNG:
                - Trả lời ngắn gọn, tập trung vào vấn đề chính.
                - KHÔNG lặp lại các điểm tương tự.
                - Gộp các lời khuyên giống nhau thành một điểm duy nhất.
                - Chỉ liệt kê 3-5 điểm quan trọng nhất, không cần liệt kê nhiều.
                - Sử dụng TÊN THÀNH PHỐ thay vì city_id khi trả lời.
                - CHỈ đưa ra lời khuyên liên quan đến câu hỏi của người dùng.
                - KHÔNG tự ý thêm lời khuyên về khẩu trang hay chất lượng không khí nếu người dùng chỉ hỏi về mưa/nắng.
                - Nếu người dùng hỏi về hoạt động thể thao (đá bóng, chạy bộ...) dưới trời mưa, chỉ tư vấn về mưa (mang ô, áo mưa, sân trơn...), KHÔNG nói về khẩu trang.
                
                LỜI KHUYÊN BẮT BUỘC:
                - LUÔN thêm câu: "Nếu thời tiết xấu hơn (mưa to, bão, nhiệt độ cực đoan), bạn nên cân nhắc thay đổi kế hoạch hoặc hạn chế hoạt động ngoài trời."
                - Nếu người dùng có bệnh và thời tiết thay đổi: "Với tình trạng bệnh của bạn, hãy theo dõi chặt chẽ và nếu có dấu hiệu bất thường, liên hệ bác sĩ ngay."
                
                Bạn có thể sử dụng các công cụ sau để thu thập thông tin:
                - Tool 1: Lấy dữ liệu thời tiết, chất lượng không khí và chỉ số UV cho các ngày cụ thể.
                - Tool 2: Lấy thông tin về các bệnh của người dùng.
                - Tool 3: Lấy thông tin từ cơ sở dữ liệu kiến thức để đưa ra lời khuyên về sức khỏe.
                Khi trả lời, hãy tổng hợp thông tin từ tất cả các công cụ cần thiết.
                Ví dụ: Nếu người dùng hỏi Thời tiết ngày mai có ảnh hưởng gì đến bệnh của tôi không ?,
                bạn cần sử dụng tool thời tiết và tool sức khỏe để đưa ra câu trả lời đầy đủ."""),
                ("placeholder", "{chat_history}"),
                ("human", "{input}"),
                ("placeholder", "{agent_scratchpad}")
            ])
            
            # Parse dates from user query and call tools directly
            user_query = f"Thành phố của tôi là: {city_name}, và mã user_id của tôi là {user_id_from_fastapi}. Tôi muốn hỏi bạn " + input_from_user
            
            # Determine which dates to query based on user input
            # Priority: Specific weekday (thứ X) > ngày mai > hôm nay
            dates_to_query = []
            input_lower = input_from_user.lower()
            
            # Parse thứ 4, 5, 6, 7, chủ nhật (HIGHEST PRIORITY)
            weekday_map = {
                'thứ 4': 2, 'thứ tư': 2, 'thứ 5': 3, 'thứ năm': 3, 
                'thứ 6': 4, 'thứ sáu': 4, 'thứ 7': 5, 'thứ bảy': 5,
                'chủ nhật': 6
            }
            found_weekday = False
            for weekday_str, weekday_num in weekday_map.items():
                if weekday_str in input_lower:
                    # Calculate date for this weekday
                    current_weekday = now_vietnam.weekday()  # 0=Monday, 6=Sunday
                    days_ahead = weekday_num - current_weekday
                    if days_ahead <= 0:  # Target day already happened this week
                        days_ahead += 7
                    target_date = now_vietnam + timedelta(days=days_ahead)
                    dates_to_query.append({'day': target_date.day, 'month': target_date.month, 'year': target_date.year})
                    found_weekday = True
                    break  # Only take first weekday match
            
            # Parse ngày mai (if no weekday specified)
            if not found_weekday and any(word in input_lower for word in ['ngày mai', 'mai']):
                tomorrow = now_vietnam + timedelta(days=1)
                dates_to_query.append({'day': tomorrow.day, 'month': tomorrow.month, 'year': tomorrow.year})
            
            # Parse hôm nay (if no other date specified)
            elif not found_weekday and not dates_to_query and any(word in input_lower for word in ['hôm nay', 'bây giờ', 'hiện tại']):
                dates_to_query.append({'day': now_vietnam.day, 'month': now_vietnam.month, 'year': now_vietnam.year})
            
            # If no specific date mentioned, default to today
            if not dates_to_query:
                dates_to_query.append({'day': now_vietnam.day, 'month': now_vietnam.month, 'year': now_vietnam.year})
            
            print(f"[DEBUG] Parsed dates from query: {dates_to_query}")
            
            # Execute tools to get context
            context_parts = []
            
            # Get weather data for parsed dates
            weather_results = await get_weather_report.ainvoke({'dates': dates_to_query, 'city_id': city_id_from_fastapi})
            if weather_results:
                # Rút gọn weather data - chỉ lấy 800 ký tự đầu
                weather_summary = str(weather_results)[:800] + "..." if len(str(weather_results)) > 800 else str(weather_results)
                context_parts.append(f"Dữ liệu thời tiết: {weather_summary}")
            
            # Get disease info
            disease_info = await get_user_disease_info.ainvoke({'user_id': user_id_from_fastapi})
            if disease_info and disease_info != "không có dữ liệu":
                context_parts.append(f"Thông tin bệnh lý: {disease_info}")
                
                # Chỉ gọi RAG khi câu hỏi liên quan đến sức khỏe/bệnh lý/chất lượng không khí
                health_keywords = ['bệnh', 'sức khỏe', 'khỏe', 'ốm', 'đau', 'dị ứng', 'hen', 'suyễn', 
                                   'aqi', 'pm2.5', 'pm10', 'ô nhiễm', 'chất lượng không khí', 
                                   'khó thở', 'ho', 'hắt hơi', 'sổ mũi', 'ngạt']
                should_use_rag = any(keyword in input_from_user.lower() for keyword in health_keywords)
                
                if should_use_rag:
                    disease_name = disease_info.split(":")[1].strip() if ":" in disease_info else "respiratory"
                    rag_data = await retrieve_health_guideline.ainvoke({'query_question': input_from_user, 'disease_name': disease_name})
                    if rag_data and rag_data != "không có dữ liệu":
                        context_parts.append(f"Hướng dẫn sức khỏe: {rag_data}")
            
            full_context = "\n\n".join(context_parts)
            
            if history_context:
                chat_history_str = history_context
            else:
                chat_history_str = ""

            # Create LLM chain and invoke
            llm_chain = prompt | llm
            response = await llm_chain.ainvoke({
                "input": user_query,
                "chat_history": [SystemMessage(content=chat_history_str)] if chat_history_str else [],
                "agent_scratchpad": [SystemMessage(content=full_context)] if full_context else []
            })
            
            # Extract content from AIMessage object
            agent_output = response.content if hasattr(response, 'content') else str(response)
            print(f"[AI AGENT] Successfully processed query using local model")
            return agent_output
            
    except Exception as e:
        print(f"[AI AGENT ERROR] Failed to process query: {e}")
        import traceback
        traceback.print_exc()
        return "Xin lỗi, tôi gặp lỗi khi xử lý câu hỏi của bạn. Vui lòng thử lại."

# hàm giúp agent luôn tỉnh và chờ job
PING_INTERVAL = 1800  # 30 phút ping Redis 1 lần
async def worker_loop():
    global redis_data
    global redis_cache
    redis_data = await get_redis_data()
    redis_cache = await get_redis_cache_conn()
    print("[Chatbot_Agent] Started worker loop...")
    last_ping = time.time()
    while True:
        if time.time() - last_ping > PING_INTERVAL:
            try:
                pong1 = await redis_data.ping()
                pong2 = await redis_cache.ping()
                if pong1 is True and pong2 is True:
                    print("[Worker] Redis ping OK")
                else:
                    print("[Worker] Redis ping failed → reconnecting")
                    redis_data = await get_redis_data()
                    redis_cache = await get_redis_cache_conn()
            except Exception as e:
                print(f"[Worker] Redis ping error: {e} → reconnecting")
                redis_data = await get_redis_data()
                redis_cache = await get_redis_cache_conn()

            last_ping = time.time()
        
        try:
            if redis_data is None or redis_cache is None:
                redis_data = await get_redis_data()
                redis_cache = await get_redis_cache_conn()

            job_json = await redis_data.brpop(QUEUE_CHATBOT, timeout=5)
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
        request_id = job_data["request_id"]
        city_id = job_data["city_id"]
        user_id = job_data["user_id"]
        user_input = job_data["user_input"]
        summary_history = job_data["history_context"]
        try:
            agent_output = await agent_process(city_id, user_id, user_input, summary_history)
            if agent_output is None: agent_output = "Không thể xử lý câu hỏi này"
            # Lưu kết quả vào Redis Cache (DB1) với TTL
            # TTL (time-to-live) là 1800 giây (30 phút)
            TTL_SECONDS = 1800
            await redis_cache.setex(
                name=request_id, 
                time=TTL_SECONDS, 
                value=agent_output
            )
            print(f"[Chatbot_Agent] Hoàn thành job {request_id}. Kết quả đã được lưu vào Redis cache với TTL {TTL_SECONDS} giây.")
            # 2. Push bot response vào Redis history (DB2)
            redis_history = await get_redis_history_conn()
            await append_chat_history(user_id, "bot", agent_output, redis_history)
            print(f"[Chatbot_Agent] Đã lưu vào redis history chat")

        except Exception as e:
            print(f"[Chatbot_Agent] Error in worker loop for job {request_id}: {e}")
            traceback.print_exc()
    
# Chạy chương trình
if __name__ == "__main__":
    try:
        asyncio.run(worker_loop())
    except KeyboardInterrupt:
        print("\n[Chatbot_Agent] Stopped by user (Ctrl+C)")

# python -m chatbot.ai_agent