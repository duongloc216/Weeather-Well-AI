"""
Script kiểm tra các collections trong ChromaDB
"""
import chromadb

# Kết nối ChromaDB
client = chromadb.PersistentClient(path='./chroma_data')

# Lấy tất cả collections
collections = client.list_collections()

print(f"\n📚 ChromaDB có {len(collections)} collections:\n")
print("=" * 60)

for i, collection in enumerate(collections, 1):
    count = collection.count()
    print(f"{i}. Collection: '{collection.name}'")
    print(f"   └─ Số tài liệu: {count} documents")
    
    # Lấy 1 sample document để xem nội dung
    if count > 0:
        sample = collection.get(limit=1, include=['documents', 'metadatas'])
        if sample['documents']:
            doc_preview = sample['documents'][0][:200] + "..." if len(sample['documents'][0]) > 200 else sample['documents'][0]
            print(f"   └─ Sample: {doc_preview}")
    print()

print("=" * 60)
