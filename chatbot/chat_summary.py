from core.langchain_local_adapter import LocalChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from typing import List, Dict
from dotenv import load_dotenv, find_dotenv
import os
import asyncio
load_dotenv()

# 🌟 NO GEMINI API - Using local Vistral-7B-Chat model
# Không cần API keys, không cần key rotation

async def summarize_chat_history(history_context: List[Dict[str, str]]) -> str:
    """
    Nhận history_context (list of dict {"role": ..., "content": ...})
    Trả về 1 chuỗi tóm tắt ~6 câu bằng local LLM.
    🌟 Using LOCAL Vistral-7B model (no API keys needed)
    """
    
    try:
        # 1. Chuyển list of dict thành 1 chuỗi dài
        history_text = ""
        for msg in history_context:
            role = msg["role"]
            content = msg["content"]
            history_text += f"{role.upper()}: {content}\n"

        # 2. Tạo prompt tóm tắt
        prompt = (
            "Bạn là một trợ lý AI, nhiệm vụ là tóm tắt đoạn hội thoại dưới đây để "
            "cung cấp context cho một agent xử lý tiếp theo. "
            "Tóm tắt nên giữ các thông tin quan trọng, ý chính, "
            "bỏ bớt chi tiết không cần thiết và viết gọn thành khoảng 6 câu. "
            "Hãy sử dụng ngôn ngữ tự nhiên, dễ đọc, và theo trình tự thời gian của các tin nhắn.\n\n"
            f"Hội thoại:\n{history_text}\n\n"
            "Trả về kết quả tóm tắt duy nhất, không kèm thẻ hay định dạng khác."
        )

        # 3. Gọi local Vistral-7B model (no API key needed)
        chat_model = LocalChatModel(
            temperature=0.0,
            max_output_tokens=200  # Summary should be short
        )

        response = await chat_model.agenerate([[HumanMessage(content=prompt)]])
        
        summary_text = response.generations[0][0].message.content.strip()
        print(f"[CHAT SUMMARY] Successfully summarized chat history using local model")
        return summary_text

    except Exception as e:
        print(f"[CHAT SUMMARY ERROR] Failed to summarize chat history: {e}")
        # Trả về chuỗi rỗng thay vì raise error để không làm gián đoạn chatbot
        return ""