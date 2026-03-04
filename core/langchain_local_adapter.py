"""
LangChain-compatible wrappers for Local LLM
Bridge between local_llm_client and LangChain's ChatModel/Embeddings interfaces
"""
from typing import Any, List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.embeddings import Embeddings
from core.local_llm_client import get_embedding_model, get_llm_client


class LocalChatModel(BaseChatModel):
    """
    LangChain-compatible chat model using local Vistral-7B
    
    Replace: ChatGoogleGenerativeAI
    Usage:
        llm = LocalChatModel(temperature=0.7)
        response = llm.invoke("Hello")
    """
    
    temperature: float = 0.7
    max_tokens: int = 512
    model_name: str = "Vistral-7B-Chat"
    
    def __init__(self, temperature: float = 0.7, max_output_tokens: int = 512, **kwargs):
        super().__init__()
        self.temperature = temperature
        self.max_tokens = max_output_tokens
        self._llm = get_llm_client()
    
    @property
    def _llm_type(self) -> str:
        return "local-vistral-chat"
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any
    ) -> ChatResult:
        """Synchronous generation (not used in async code)"""
        # Convert LangChain messages to Vistral format
        formatted_messages = self._convert_messages(messages)
        
        # Generate response
        response_text = self._llm.chat(
            formatted_messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
        
        # Wrap in LangChain format
        message = AIMessage(content=response_text)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])
    
    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any
    ) -> ChatResult:
        """Async generation (used by LangChain agents)"""
        # For now, just call sync version (can optimize later with async Llama)
        return self._generate(messages, stop, **kwargs)
    
    def _convert_messages(self, messages: List[BaseMessage]) -> List[dict]:
        """Convert LangChain messages to Vistral chat format"""
        result = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                result.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                result.append({"role": "assistant", "content": msg.content})
            elif isinstance(msg, SystemMessage):
                # Vistral uses system prompt, prepend to first user message
                result.append({"role": "system", "content": msg.content})
        return result


class LocalEmbeddings(Embeddings):
    """
    LangChain-compatible embeddings using local paraphrase-multilingual-mpnet-base-v2
    
    Replace: GoogleGenerativeAIEmbeddings
    Usage:
        embeddings = LocalEmbeddings()
        vector = embeddings.embed_query("text")
    """
    
    model_name: str = "paraphrase-multilingual-mpnet-base-v2"
    dimension: int = 768
    
    def __init__(self, **kwargs):
        super().__init__()
        self._embedding_model = get_embedding_model()
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple documents (for indexing)"""
        return self._embedding_model.embed_texts(texts)
    
    def embed_query(self, text: str) -> List[float]:
        """Embed single query (for search)"""
        return self._embedding_model.embed_text(text)
    
    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """Async version of embed_documents"""
        # For now, just call sync version (SentenceTransformer is fast enough)
        return self.embed_documents(texts)
    
    async def aembed_query(self, text: str) -> List[float]:
        """Async version of embed_query"""
        return self.embed_query(text)


# ========== Backward Compatibility Aliases ==========
# For easy replacement in existing code

class ChatLocalLLM(LocalChatModel):
    """Alias for ChatGoogleGenerativeAI replacement"""
    pass

class LocalGenerativeAIEmbeddings(LocalEmbeddings):
    """Alias for GoogleGenerativeAIEmbeddings replacement"""
    pass
