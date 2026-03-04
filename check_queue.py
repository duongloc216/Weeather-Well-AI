import asyncio
from core.redis_client import get_redis_data

async def check_queue():
    redis = await get_redis_data()
    
    # Check queue_data (weather crawl)
    length_data = await redis.llen("queue_data")
    print(f"🔢 Queue 'queue_data' (weather crawl): {length_data} jobs")
    
    # Check queue_passive_suggestion
    length_suggestion = await redis.llen("queue_passive_suggestion")
    print(f"🔢 Queue 'queue_passive_suggestion': {length_suggestion} jobs")
    
    # Check queue_chatbot
    length_chatbot = await redis.llen("queue_chatbot")
    print(f"🔢 Queue 'queue_chatbot': {length_chatbot} jobs")
    
asyncio.run(check_queue())
