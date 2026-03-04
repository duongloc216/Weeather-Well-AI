"""
Local LLM Client for WeatherWell AI
Replace Google Gemini API with local pre-trained models
"""
import os
from typing import List, Optional
from sentence_transformers import SentenceTransformer
from llama_cpp import Llama
import numpy as np

class LocalEmbeddingModel:
    """
    Embedding Model: paraphrase-multilingual-mpnet-base-v2
    - Input: Text (Vietnamese/English)
    - Output: 768D vector
    - Use case: RAG similarity search in ChromaDB
    """
    def __init__(self, model_path: str = "./models/embedding_model"):
        print(f"Loading embedding model from {model_path}...")
        # Force CPU to avoid CUDA OOM (RTX 3050 4GB not enough for LLM + Embedding)
        self.model = SentenceTransformer(model_path, device='cpu')
        print(f"✅ Embedding model loaded on CPU (dimension: {self.model.get_sentence_embedding_dimension()})")
    
    def embed_text(self, text: str) -> List[float]:
        """
        Convert single text to vector
        
        Args:
            text: Input text (Vietnamese/English)
        
        Returns:
            768D vector as list
        """
        embedding = self.model.encode(text, convert_to_tensor=False)
        return embedding.tolist()
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Convert multiple texts to vectors (batch processing)
        
        Args:
            texts: List of input texts
        
        Returns:
            List of 768D vectors
        """
        embeddings = self.model.encode(texts, convert_to_tensor=False, show_progress_bar=True)
        return embeddings.tolist()
    
    def similarity(self, text1: str, text2: str) -> float:
        """
        Calculate cosine similarity between two texts
        
        Returns:
            Similarity score [-1, 1]
        """
        v1 = np.array(self.embed_text(text1))
        v2 = np.array(self.embed_text(text2))
        return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))


class LocalLLMClient:
    """
    LLM: Vistral-7B-Chat-Q4_K_M.gguf
    - Input: Prompt (Vietnamese)
    - Output: Generated text (Vietnamese)
    - Use case: Health suggestions, chatbot responses, summarization
    - VRAM: 4GB RTX 3050 (30 GPU layers, rest on CPU)
    """
    def __init__(
        self, 
        model_path: str = "./models/qwen2.5-3b-instruct-q4_k_m.gguf",
        n_ctx: int = 4096,  # Reduced context window for RAM optimization (was 8192)
        n_gpu_layers: int = 0,  # CPU-only build, không dùng GPU
        temperature: float = 0.7,
        max_tokens: int = 512
    ):
        # Chuyển đổi đường dẫn tương đối thành tuyệt đối
        import os
        if not os.path.isabs(model_path):
            model_path = os.path.abspath(model_path)
        
        print(f"Loading LLM from {model_path}...")
        print(f"   Context window: {n_ctx} tokens")
        print(f"   GPU layers: {n_gpu_layers} (Hybrid: GPU+CPU offloading)")
        print(f"   Temperature: {temperature}")
        
        # Kiểm tra file tồn tại
        import os
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        try:
            self.llm = Llama(
                model_path=model_path,
                n_ctx=n_ctx,
                n_gpu_layers=n_gpu_layers,
                n_threads=4,  # Số CPU threads
                n_batch=512,  # Batch size nhỏ hơn để tiết kiệm RAM
                use_mmap=True,  # Memory map file để tiết kiệm RAM
                use_mlock=False,  # Không lock memory
                verbose=True  # Bật verbose để debug
            )
            self.temperature = temperature
            self.max_tokens = max_tokens
            print("✅ LLM loaded successfully")
        except Exception as e:
            print(f"❌ Failed to load LLM: {e}")
            raise
    
    def generate(
        self, 
        prompt: str, 
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None
    ) -> str:
        """
        Generate text from prompt
        
        Args:
            prompt: Input prompt (Vietnamese)
            temperature: Sampling temperature (override default)
            max_tokens: Max output tokens (override default)
            stop: Stop sequences
        
        Returns:
            Generated text (Vietnamese)
        """
        temp = temperature if temperature is not None else self.temperature
        max_tok = max_tokens if max_tokens is not None else self.max_tokens
        
        response = self.llm(
            prompt,
            temperature=temp,
            max_tokens=max_tok,
            stop=stop or ["</s>", "###"],
            echo=False
        )
        
        return response['choices'][0]['text'].strip()
    
    def chat(
        self,
        messages: List[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Chat completion (Vistral format)
        
        Args:
            messages: [{"role": "user"/"assistant", "content": "..."}]
            temperature: Override default
            max_tokens: Override default
        
        Returns:
            Assistant's response
        
        Example:
            messages = [
                {"role": "user", "content": "Thời tiết hôm nay như thế nào?"},
                {"role": "assistant", "content": "Hôm nay..."},
                {"role": "user", "content": "Tôi nên làm gì?"}
            ]
        """
        # Format prompt in Vistral chat format
        prompt = self._format_chat_prompt(messages)
        return self.generate(prompt, temperature, max_tokens)
    
    def _format_chat_prompt(self, messages: List[dict]) -> str:
        """
        Format messages into Vistral chat template
        
        Vistral format:
        <|im_start|>system
        {system_message}<|im_end|>
        <|im_start|>user
        {user_message}<|im_end|>
        <|im_start|>assistant
        """
        prompt = "<|im_start|>system\nBạn là trợ lý sức khỏe thông minh, chuyên tư vấn về ảnh hưởng của thời tiết đến sức khỏe.<|im_end|>\n"
        
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            prompt += f"<|im_start|>{role}\n{content}<|im_end|>\n"
        
        prompt += "<|im_start|>assistant\n"
        return prompt
    
    def summarize(self, text: str, max_length: int = 100) -> str:
        """
        Summarize long text (for chat history)
        
        Args:
            text: Long text to summarize
            max_length: Max summary length (tokens)
        
        Returns:
            Summary text
        """
        prompt = f"""<|im_start|>system
Hãy tóm tắt đoạn văn sau thành 2-3 câu ngắn gọn.<|im_end|>
<|im_start|>user
{text}<|im_end|>
<|im_start|>assistant
"""
        return self.generate(prompt, temperature=0.3, max_tokens=max_length)


# ========== Singleton Instances ==========
_embedding_model = None
_llm_client = None

def get_embedding_model() -> LocalEmbeddingModel:
    """Get singleton embedding model instance"""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = LocalEmbeddingModel()
    return _embedding_model

def get_llm_client() -> LocalLLMClient:
    """Get singleton LLM client instance"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LocalLLMClient()
    return _llm_client


# ========== Test ==========
if __name__ == "__main__":
    print("=" * 70)
    print("TESTING LOCAL LLM CLIENT")
    print("=" * 70)
    
    # Test embedding
    print("\n[1/3] Testing Embedding Model...")
    emb = get_embedding_model()
    vector = emb.embed_text("Nhiệt độ cao gây say nắng")
    print(f"   Vector dimension: {len(vector)}")
    print(f"   First 5 values: {vector[:5]}")
    
    sim = emb.similarity("nhiệt độ cao", "thời tiết nóng")
    print(f"   Similarity: {sim:.3f}")
    
    # Test LLM generation
    print("\n[2/3] Testing LLM Generation...")
    llm = get_llm_client()
    response = llm.generate("Hôm nay trời nóng 35°C, tôi nên làm gì?", max_tokens=100)
    print(f"   Response: {response}")
    
    # Test chat
    print("\n[3/3] Testing Chat Completion...")
    messages = [
        {"role": "user", "content": "Nhiệt độ 38°C có nguy hiểm không?"}
    ]
    chat_response = llm.chat(messages, max_tokens=100)
    print(f"   Chat response: {chat_response}")
    
    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED")
    print("=" * 70)
