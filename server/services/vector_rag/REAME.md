# 🤖 Hệ thống RAG Gọn Nhẹ cho Văn bản Pháp lý

Hệ thống RAG (Retrieval-Augmented Generation) tối ưu cho xử lý các văn bản pháp lý Việt Nam, kết hợp LangChain và Gemma 2B.

## ✨ Tính năng

- 🚀 **Gọn nhẹ & Nhanh**: Vector database FAISS tối ưu cho tốc độ
- 📚 **Đa định dạng**: Hỗ trợ PDF, DOCX, TXT
- ⚖️ **Chuyên biệt**: Tối ưu cho văn bản pháp lý VN (điều, khoản, điểm)
- 🔍 **Truy xuất thông minh**: Embedding tiếng Việt chuyên dụng
- 💬 **LLM địa phương**: Sử dụng Gemma 2B qua Ollama

## 🛠️ Cài đặt

### 1. Clone repository và cài đặt dependencies

```bash
git clone <repo-url>
cd rag-legal-system
pip install -r requirements.txt
```

### 2. Cài đặt Ollama và Gemma 2B

```bash
# Cài đặt Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull Gemma 2B model
ollama pull gemma:2b
```

### 3. Chuẩn bị dữ liệu

Tạo thư mục `documents` và đặt các file văn bản pháp lý:

```
documents/
├── luat_doanh_nghiep.pdf
├── nghi_dinh_123.docx
├── thong_tu_45.txt
└── ...
```

## 🚀 Sử dụng

### Bước 1: Build Vector Database

```bash
# Build vector database từ thư mục documents
python build_vectors.py --data_dir ./documents --output_dir ./vector_db

# Với tùy chọn nâng cao
python build_vectors.py \
    --data_dir ./documents \
    --output_dir ./vector_db \
    --chunk_size 800 \
    --chunk_overlap 100 \
    --batch_size 50
```

**Tham số:**
- `--data_dir`: Thư mục chứa documents
- `--output_dir`: Thư mục lưu vector database 
- `--chunk_size`: Kích thước chunk (default: 800)
- `--chunk_overlap`: Overlap giữa chunks (default: 100)
- `--batch_size`: Batch size xử lý (default: 100)

### Bước 2: Truy vấn hệ thống

#### Truy vấn đơn lẻ

```bash
python query_rag.py \
    --vector_db ./vector_db \
    --query "Thục tục thành lập doanh nghiệp cần những giấy tờ gì?"
```

#### Chế độ tương tác

```bash
python query_rag.py --vector_db ./vector_db --interactive
```

#### Batch query từ file

```bash
# Tạo file questions.txt với mỗi dòng là 1 câu hỏi
echo "Điều kiện thành lập doanh nghiệp?" > questions.txt
echo "Quy trình đăng ký thuế?" >> questions.txt

# Chạy batch query
python query_rag.py \
    --vector_db ./vector_db \
    --questions_file questions.txt \
    --output_file results.json
```

## 📊 Ví dụ sử dụng

### Build Vector Database

```bash
$ python build_vectors.py --data_dir ./documents --output_dir ./vector_db

🚀 Khởi tạo Vector Database Builder...
✅ Vector Database Builder initialized!
🔍 Tìm kiếm documents trong: ./documents
  Tìm thấy 5 file .pdf
  Tìm thấy 3 file .docx
  Tìm thấy 2 file .txt
📊 Tổng cộng: 10 documents
📋 Bắt đầu xử lý 10 documents...
📄 Xử lý: luat_doanh_nghiep.pdf
✅ Hoàn thành: luat_doanh_nghiep.pdf -> 45 chunks
...
🎉 Hoàn thành xây dựng Vector Database!

📊 BÁO CÁO TỔNG KẾT
=======================================
📁 Tổng số files: 10
✅ Files xử lý thành công: 9
❌ Files lỗi: 1  
📄 Tổng số chunks: 234
⏱️ Thời gian xử lý: 45.23s
```

### Query hệ thống

```bash
$ python query_rag.py --vector_db ./vector_db --query "Thủ tục thành lập công ty TNHH?"

❓ Câu hỏi: Thủ tục thành lập công ty TNHH?
===========================================================
✅ Trả lời:
------------------------------
Để thành lập công ty TNHH, bạn cần thực hiện các thủ tục sau:

1. **Chuẩn bị hồ sơ:**
   - Đơn đăng ký doanh nghiệp (theo mẫu)
   - Điều lệ công ty
   - Danh sách thành viên góp vốn
   - Giấy chứng nhận đầu tư (nếu có vốn FDI)

2. **Nộp hồ sơ:**
   - Nộp tại Phòng Đăng ký kinh doanh thuộc Sở KH&ĐT
   - Thời gian xử lý: 15 ngày làm việc

3. **Nhận kết quả:**
   - Giấy chứng nhận đăng ký doanh nghiệp
   - Mã số thuế

📊 Thống kê:
  • Thời gian tìm kiếm: 0.234s
  • Thời gian tạo câu trả lời: 1.567s  
  • Tổng thời gian: 1.801s
  • Số nguồn tham khảo: 3

📚 Nguồn tham khảo:
  1. luat_doanh_nghiep.pdf (.pdf)
  2. huong_dan_thanh_lap_dn.docx (.docx)
  3. mau_don_dang_ky.pdf (.pdf)
```

## ⚙️ Cấu hình nâng cao

### Tùy chỉnh Text Splitter

```python
# Trong rag_system.py, tùy chỉnh VietnameseLegalTextSplitter
splitter = VietnameseLegalTextSplitter(
    chunk_size=1000,        # Tăng kích thước chunk
    chunk_overlap=150       # Tăng overlap
)
```

### Tùy chỉnh Embedding Model

```python
# Thay đổi model embedding
embeddings = FastEmbeddings("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
```

### Tùy chỉnh LLM

```bash
# Sử dụng model LLM khác
python query_rag.py --vector_db ./vector_db --llm_model "llama2:7b" --query "..."
```

## 📁 Cấu trúc thư mục

```
rag-legal-system/
├── rag_system.py          # Core RAG system
├── build_vectors.py       # Script build vector DB
├── query_rag.py          # Script query system
├── requirements.txt       # Dependencies
├── README.md             # Hướng dẫn này
├── documents/            # Thư mục documents (tự tạo)
│   ├── *.pdf
│   ├── *.docx  
│   └── *.txt
├── vector_db/            # Vector database (tự tạo)
│   ├── faiss_index.index
│   ├── documents.pkl
│   └── metadata.json
└── logs/                 # Log files
    └── build_vectors.log
```

## 🔧 API Usage

### Sử dụng trong code Python

```python
from build_vectors import load_vector_database
from rag_system import GemmaLLM
from query_rag import RAGQuerySystem

# Load hệ thống
rag_system = RAGQuerySystem("./vector_db")

# Query
result = rag_system.query("Điều kiện thành lập doanh nghiệp?")
print(result['answer'])
```

### Tích hợp vào ứng dụng web

```python
from flask import Flask, request, jsonify
from query_rag import RAGQuerySystem

app = Flask(__name__)
rag_system = RAGQuerySystem("./vector_db")

@app.route('/api/query', methods=['POST'])
def api_query():
    data = request.json
    question = data.get('question', '')
    
    if not question:
        return jsonify({'error': 'Missing question'}), 400
    
    result = rag_system.query(question)
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

## 📈 Hiệu suất

### Benchmark trên dataset test

| Metric | Giá trị |
|--------|---------|
| **Tốc độ tìm kiếm** | ~0.2s/query |
| **Tốc độ sinh câu trả lời** | ~1.5s/query |
| **Tổng thời gian** | ~1.7s/query |
| **Memory usage** | ~2GB RAM |
| **Storage** | ~500MB/10K documents |

### Tối ưu hiệu suất

1. **GPU Acceleration**: Cài `faiss-gpu` thay vì `faiss-cpu`
2. **Batch Processing**: Tăng `batch_size` khi build vector DB
3. **Chunk Size**: Giảm `chunk_size` để tăng tốc retrieval
4. **Model Size**: Dùng embedding model nhỏ hơn nếu cần

## 🐛 Troubleshooting

### Lỗi thường gặp

**1. Ollama không kết nối được**
```bash
# Kiểm tra Ollama service
ollama serve

# Kiểm tra model có sẵn
ollama list
```

**2. Lỗi memory khi build vector DB**
```bash
# Giảm batch size
python build_vectors.py --data_dir ./documents --batch_size 20
```

**3. Embedding model không tải được**
```bash
# Thử model khác
python build_vectors.py --embedding_model "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
```

**4. PDF không đọc được**
```bash
# Cài thêm dependency
pip install pdfplumber
# Hoặc dùng OCR cho PDF scan
pip install pytesseract
```

## 🔄 Cập nhật dữ liệu

### Thêm documents mới

```bash
# Thêm files mới vào thư mục documents
cp new_documents/* ./documents/

# Rebuild vector database
python build_vectors.py --data_dir ./documents --output_dir ./vector_db
```

### Backup và restore

```bash
# Backup vector database
tar -czf vector_db_backup.tar.gz vector_db/

# Restore
tar -xzf vector_db_backup.tar.gz
```

## 📞 Hỗ trợ

- **Issues**: Tạo issue trên GitHub
- **Discussions**: GitHub Discussions
- **Email**: support@example.com

## 📄 License

MIT License - xem file LICENSE để biết chi tiết.

## 🙏 Credits

- **LangChain**: Framework RAG
- **FAISS**: Vector database
- **sentence-transformers**: Embedding models
- **Ollama**: Local LLM inference
- **Gemma**: Google's LLM model

---

**Made with ❤️ for Vietnamese Legal Tech**