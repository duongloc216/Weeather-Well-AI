"""
Script để xem chi tiết cấu trúc dữ liệu trong ChromaDB
"""
import chromadb
import json

# Kết nối ChromaDB
client = chromadb.PersistentClient(path='./chroma_data')

# Lấy tất cả collections
collections = client.list_collections()

print(f"\n{'='*80}")
print(f"📚 ChromaDB có {len(collections)} collections")
print(f"{'='*80}\n")

for i, collection in enumerate(collections, 1):
    count = collection.count()
    print(f"\n{i}. Collection: '{collection.name}'")
    print(f"   Total documents: {count}")
    
    if count > 0:
        # Lấy 1 sample để xem cấu trúc đầy đủ
        sample = collection.get(
            limit=1, 
            include=['documents', 'metadatas', 'embeddings']
        )
        
        if sample['ids']:
            print(f"\n   📄 SAMPLE DOCUMENT STRUCTURE:")
            print(f"   {'─'*70}")
            
            # ID
            print(f"\n   🔑 ID: {sample['ids'][0]}")
            
            # Document text
            if sample['documents']:
                doc_text = sample['documents'][0]
                preview = doc_text[:300] + "..." if len(doc_text) > 300 else doc_text
                print(f"\n   📝 TEXT (first 300 chars):")
                print(f"      {preview}")
            
            # Metadata
            if sample['metadatas']:
                print(f"\n   🏷️  METADATA:")
                metadata = sample['metadatas'][0]
                for key, value in metadata.items():
                    print(f"      - {key}: {value}")
            
            # Embedding vector
            if sample['embeddings'] is not None and len(sample['embeddings']) > 0:
                embedding = sample['embeddings'][0]
                print(f"\n   🔢 EMBEDDING VECTOR:")
                print(f"      - Dimensions: {len(embedding)}")
                print(f"      - First 10 values: {[round(x, 6) for x in embedding[:10]]}")
                print(f"      - Data type: float")
                print(f"      - Example: [{embedding[0]:.6f}, {embedding[1]:.6f}, ..., {embedding[-1]:.6f}]")
            
            print(f"\n   {'─'*70}")

print(f"\n{'='*80}\n")

print("💡 CẤU TRÚC LƯU TRỮ:")
print("""
ChromaDB lưu mỗi document với 3 phần:
1. TEXT (documents)     - Nội dung gốc để đưa cho LLM
2. METADATA (metadatas) - Thông tin phụ (source, url, disease...)
3. VECTOR (embeddings)  - 768 số float để tính similarity

Khi query:
  Query text → Embedding model → Query vector
  → ChromaDB tìm vectors tương tự
  → Trả về TEXT + METADATA (không trả vector)
  → TEXT được đưa vào LLM
""")
