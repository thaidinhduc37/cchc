# DVC Chatbot - Công cụ hướng dẫn thủ tục Dịch vụ công

### ✅ Mô tả
Chatbot này giúp hướng dẫn người dân thực hiện các thủ tục Dịch vụ công bằng cách trả lời từ dữ liệu DOCX, JSON và sử dụng mô hình Genma:2B để trả lời tự nhiên.

### 📦 Cài đặt
1. Cài đặt các thư viện phụ thuộc:
   ```bash
   pip install -r requirements.txt
   ```

2. Cấu trúc thư mục dữ liệu:
   - `dataset/{lĩnh_vực}/`
   - Ví dụ:
     - `dataset/cancuoc/`
     - `dataset/hochieu/`

3. Build vector
```bash
python services/vector_rag/build_vector.py --domain xuatnhapcanh --build
```

### 🚀 Chạy ứng dụng
```bash
python app.py
```

### 🛠️ Tính năng
- Hỗ trợ trả lời từ dữ liệu PDF, DOCX, XLSX, TXT, JSON.
- Tạo vector để tra cứu nhanh dữ liệu.
- Tính năng trợ lý ảo với Text-to-Speech và Speech-to-Text.
- Duy trì ngữ cảnh hội thoại để trả lời liền mạch.
