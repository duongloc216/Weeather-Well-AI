# HƯỚNG DẪN CHẠY NHANH HỆ THỐNG

## 1. Chuẩn bị môi trường

```powershell
# Cài đặt dependencies
pip install -r requirements.txt

# Download model LLM
python download_qwen_model.py

# Download spacy model
python -m spacy download en_core_web_sm
```

## 2. Khởi động các services

### Terminal 1: Redis
```powershell
cd redis
.\redis-server.exe
```

### Terminal 2: Backend FastAPI
```powershell
python -m uvicorn backend.app:app --reload
```

### Terminal 3: Chatbot Worker
```powershell
python -m chatbot.ai_agent
```

### Terminal 4: Frontend (Vite)
```powershell
cd vite-project
npm install
npm run dev
```

## 3. Thu thập dữ liệu thời tiết (TEST NHANH - không đợi 12h đêm)

### Terminal 5: Push jobs vào queue
```powershell
python manual_crawl_all_cities.py
```

### Terminal 6: Worker thu thập weather
```powershell
python -m worker.worker
```

**Đợi Terminal 6 xử lý xong 60 jobs** → Dữ liệu thời tiết đã có trong SQL Server

✅ **Kết quả mong đợi**: 
- Weather: ~1,500 records (60 cities × 25 rows)
- Climate: ~1,260 records (60 cities × 21 rows)
- UV Index: ~1,450 records (60 cities × 25 rows)

## 4. Tạo passive suggestions (lời khuyên chủ động)

### Terminal 5: Push suggestion jobs
```powershell
python push_suggestion_job.py
```

### Terminal 7: Worker tạo suggestions
```powershell
python -m passive_suggestion.suggest_worker
```

**Đợi Terminal 7 xử lý xong 60 jobs** → Lời khuyên đã có trong bảng `suggestion`

## 5. Tạo corpus RAG (chỉ chạy 1 lần)

### Bước 5.1: Crawl và chunk trên Colab
1. Upload `dev_phase/01_crawl_and_chunk_corpus.ipynb` lên Google Colab
2. Nén thư mục `dev_phase/corpus/` thành `corpus.zip`
3. Chạy lần lượt các cells trong notebook:
   - Cell 2: Cài đặt packages
   - Cell 3-4: Import và define functions
   - Cell 5: Upload `corpus.zip` → chọn file → đợi extract
   - Cell 6: Crawl URLs (5-10 phút)
   - Cell 7: Chunking (1-2 phút)
   - Cell 8: Kiểm tra kết quả
   - Cell 10: Download 4 file `*_chunks.csv`

### Bước 5.2: Embed và push trên Local
1. Copy 4 file `*_chunks.csv` vào `dev_phase/corpus/`
2. Mở `dev_phase/02_push_to_chromadb_with_gemini.ipynb` trong VS Code
3. Chạy lần lượt:
   - Cell 1: Cài đặt packages
   - Cell 2: Connect Gemini + ChromaDB
   - Cell 3: Embed và push (10-30 phút)
   - Cell 4: Verify collections
   - Cell 5: Xóa collections rác (optional)

### Bước 5.3: Restart chatbot
```powershell
# Terminal 3: Ctrl+C → chạy lại
python -m chatbot.ai_agent
```

## 6. Kiểm tra hệ thống

### Kiểm tra queues
```powershell
python check_queue.py
```

### Kiểm tra ChromaDB
```powershell
python check_chromadb_collections.py
```

### Kiểm tra bảng suggestion
```powershell
python check_suggestion_table.py
```

### Kiểm tra dữ liệu weather
```powershell
python check_weather_data.py
```

## 7. Truy cập ứng dụng

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 8. Tóm tắt terminals cần chạy

| Terminal | Command | Mục đích |
|----------|---------|----------|
| 1 | `cd redis; .\redis-server.exe` | Redis server |
| 2 | `python -m uvicorn backend.app:app --reload` | Backend API |
| 3 | `python -m chatbot.ai_agent` | Chatbot worker |
| 4 | `cd vite-project; npm run dev` | Frontend |
| 5 | (Dùng tạm để chạy scripts) | Push jobs |
| 6 | `python -m worker.worker` | Weather worker |
| 7 | `python -m passive_suggestion.suggest_worker` | Suggestion worker |

## 9. Lưu ý

- **Terminals 1-4**: Chạy liên tục
- **Terminals 6-7**: Chạy khi cần thu thập dữ liệu (test nhanh) hoặc để tự động chạy hàng ngày
- **Corpus RAG**: Chỉ setup 1 lần, sau đó không cần chạy lại
- **Nếu restart chatbot**: Phải chạy lại Terminal 3 để load ChromaDB mới
