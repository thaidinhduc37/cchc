# 🚀 Hướng Dẫn Triển Khai Hệ Thống RAG Siêu Nhẹ

## 📋 Tổng Quan

Hệ thống RAG siêu nhẹ cho lĩnh vực **Xuất Nhập Cảnh** với các đặc điểm:
- **Memory usage**: <500MB (thay vì 2GB+)
- **Response time**: <3s (thay vì 10s+)
- **Storage**: ChromaDB (thay vì FAISS)
- **LLM**: Gemini API + Gemma:2b backup
- **Embedding**: sentence-transformers (23MB thay vì 500MB)

---

## 🏗️ Cấu Trúc Thư Mục

```
server/
├── dataset/
│   └── xuatnhapcanh/
│       ├── documents/           # 📁 Chứa PDF, TXT, DOCX
│       │   ├── luat_xnc_2014.pdf
│       │   ├── nghidinh_08_2015.txt
│       │   ├── thongtu_01_2016.docx
│       │   └── huongdan_visa.txt
│       └── process/             # 🔄 Tự động tạo khi build
│           ├── vectorstore/     # ChromaDB storage
│           ├── cache/           # Embedding cache
│           └── logs/            # System logs
└── services/
    ├── unified_processor.py     # 🔗 Integration point
    └── vector_rag/             # 🧠 RAG modules
        ├── lightweight_config.py
        ├── lightweight_embeddings.py
        ├── lightweight_document_processor.py
        ├── lightweight_vector_manager.py
        ├── lightweight_llm_handler.py
        ├── lightweight_rag_engine.py
        └── build_vector.py
```

---

## 📦 Cài Đặt Dependencies

### 1. Core Dependencies
```bash
# Core RAG components
pip install chromadb sentence-transformers

# LLM providers
pip install google-generativeai  # Gemini API

# Document processing
pip install PyPDF2 python-docx

# Optional utilities
pip install numpy pandas
```

### 2. Verify Installation
```bash
python -c "import chromadb, sentence_transformers, google.generativeai; print('✅ All dependencies installed')"
```

---

## 🔧 Cấu Hình Hệ Thống

### 1. Environment Variables
```bash
# Gemini API (Recommended)
export GEMINI_API_KEY="your-gemini-api-key-here"

# Optional: Ollama for local backup
# Ensure Ollama server running with gemma:2b model
```

### 2. Kiểm Tra Ollama (Optional)
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull Gemma model
ollama pull gemma:2b

# Verify
ollama list
```

---

## 📄 Chuẩn Bị Dữ Liệu

### 1. Tạo Thư Mục Documents
```bash
mkdir -p server/dataset/xuatnhapcanh/documents
```

### 2. Thêm Tài Liệu Pháp Lý
Đặt các file PDF, TXT, DOCX vào thư mục `documents/`:

**Ví dụ:**
- `luat_xnc_2014.pdf` - Luật Xuất nhập cảnh 2014
- `nghidinh_08_2015.txt` - Nghị định 08/2015/NĐ-CP
- `thongtu_01_2016.docx` - Thông tư 01/2016/TT-BCA
- `huongdan_visa.txt` - Hướng dẫn thủ tục visa

### 3. Naming Convention (Khuyến nghị)
```
{doc_type}_{topic}_{year}.{ext}

Ví dụ:
- luat_xuatnhapcanh_2014.pdf
- nghidinh_visa_2015.txt
- thongtu_hochieu_2016.docx
```

---

## 🔨 Build Vector Store

### 1. Chạy Build Script
```bash
cd server/services/vector_rag

# Build vector store
python build_vector.py --build

# Force rebuild (nếu cần)
python build_vector.py --force

# Clean và rebuild
python build_vector.py --clean --build
```

### 2. Verify Build
```bash
# Validate vector store
python build_vector.py --validate

# Check structure
ls -la ../../dataset/xuatnhapcanh/process/
```

### 3. Expected Output
```
📊 BUILD SUMMARY
============================================================
Domain: xuatnhapcanh
Documents path: ./server/dataset/xuatnhapcanh/documents
Vector store path: ./server/dataset/xuatnhapcanh/process/vectorstore

Started at: 2024-06-03 10:30:15
Completed at: 2024-06-03 10:30:45
Build time: 30.25 seconds

Total files: 15
Processed files: 15
Total chunks: 342

✅ No errors
============================================================
```

---

## 🚀 Integration với Unified Processor

### 1. Basic Integration
```python
# server/your_chatbot.py
import asyncio
from services.unified_processor import get_unified_processor, initialize_unified_processor

# Initialize system
async def init_system():
    result = await initialize_unified_processor(
        gemini_api_key="your-api-key",
        force_rebuild=False
    )
    print(f"System initialized: {result['success']}")

# Process user query
async def process_user_message(message: str, user_id: str = None):
    processor = get_unified_processor()
    
    result = await processor.process_query(
        query=message,
        context={'user_id': user_id}
    )
    
    return {
        'response': result['response'],
        'success': result['success'],
        'metadata': result['metadata']
    }

# Example usage
async def main():
    await init_system()
    
    # Test queries
    queries = [
        "Tôi muốn xin visa du lịch Việt Nam cần thủ tục gì?",
        "Quy định về hộ chiếu là như thế nào?",
        "Người nước ngoài cư trú tại Việt Nam có điều kiện gì?"
    ]
    
    for query in queries:
        result = await process_user_message(query)
        print(f"Q: {query}")
        print(f"A: {result['response'][:200]}...")
        print(f"Time: {result['metadata']['processing_time']}s\n")

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. API Wrapper Integration
```python
from services.unified_processor import UnifiedProcessorAPI

# Create API instance
api = UnifiedProcessorAPI(gemini_api_key="your-key")

# Process message (sync wrapper if needed)
def process_message_sync(message: str, user_id: str = None):
    return asyncio.run(
        api.process_message(message, user_id)
    )

# Health check
def health_check():
    return asyncio.run(api.health_check())
```

---

## 📊 Monitoring & Maintenance

### 1. System Status
```python
# Get system status
processor = get_unified_processor()
status = processor.get_system_status()

print(f"Total requests: {status['unified_processor']['stats']['total_requests']}")
print(f"RAG requests: {status['unified_processor']['stats']['rag_requests']}")
print(f"Average response time: {status['unified_processor']['stats']['avg_response_time']}s")
```

### 2. Performance Monitoring
```python
# Health check endpoint
health = await processor.health_check()

if health['status'] == 'healthy':
    print("✅ System is healthy")
else:
    print(f"⚠️ System status: {health['status']}")
    for component, status in health['components'].items():
        print(f"  {component}: {status['status']}")
```

### 3. Cache Management
```python
# Clear caches để giải phóng memory
processor.clear_caches()

# Refresh toàn bộ hệ thống
await processor.refresh_system()
```

---

## 🔄 Adding New Documents

### 1. Runtime Addition
```python
# Add documents from new directory
result = await processor.add_documents("/path/to/new/documents")

if result['success']:
    print(f"Added {result['documents_added']} new document chunks")
else:
    print(f"Failed: {result['message']}")
```

### 2. Batch Update
```bash
# Add new documents và rebuild
cp new_documents/* server/dataset/xuatnhapcanh/documents/
python build_vector.py --force
```

---

## 🐛 Troubleshooting

### 1. Common Issues

**Issue: ChromaDB not found**
```bash
pip install chromadb
```

**Issue: Sentence-transformers slow**
```bash
# Use lighter model in config
model_name = "all-MiniLM-L6-v2"  # 23MB
# instead of "keepitreal/vietnamese-sbert"  # 500MB
```

**Issue: Gemini API quota exceeded**
```bash
# System auto-fallback to Ollama
ollama pull gemma:2b
ollama serve
```

**Issue: Memory usage high**
```python
# Clear caches regularly
processor.clear_caches()

# Reduce batch size in config
batch_size = 16  # instead of 32
```

### 2. Debug Mode
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Detailed logs for troubleshooting
```

### 3. Validation Commands
```bash
# Check vector store integrity
python build_vector.py --validate

# Test query without full system
python -c "
from services.vector_rag.lightweight_rag_engine import test_rag_engine
test_rag_engine()
"
```

---

## ⚡ Performance Optimization

### 1. Memory Optimization
```python
# In lightweight_config.py
EMBEDDING_CONFIG.batch_size = 16  # Reduce if low memory
CHUNKING_CONFIG.chunk_size = 800  # Smaller chunks
VECTOR_CONFIG.k = 3  # Fewer results per query
```

### 2. Speed Optimization
```python
# Enable caching
SYSTEM_CONFIG.enable_cache = True
EMBEDDING_CONFIG.cache_embeddings = True

# Use faster embedding model
EMBEDDING_CONFIG.model_name = "all-MiniLM-L6-v2"
```

### 3. Storage Optimization
```bash
# Regularly clean cache
rm -rf server/dataset/xuatnhapcanh/process/cache/*

# Compress old logs
gzip server/dataset/xuatnhapcanh/process/logs/*.log
```

---

## 🚦 Production