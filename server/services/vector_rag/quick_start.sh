#!/bin/bash

# Quick Start Script cho RAG Legal System
# Chạy: chmod +x quick_start.sh && ./quick_start.sh

set -e  # Exit on any error

echo "🚀 RAG Legal System - Quick Start"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python is installed
check_python() {
    print_status "Kiểm tra Python..."
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        print_success "Python $PYTHON_VERSION đã cài đặt"
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
        print_success "Python $PYTHON_VERSION đã cài đặt"
        PYTHON_CMD="python"
    else
        print_error "Python không được tìm thấy. Vui lòng cài đặt Python 3.8+"
        exit 1
    fi
}

# Check if pip is installed
check_pip() {
    print_status "Kiểm tra pip..."
    if command -v pip3 &> /dev/null; then
        print_success "pip3 đã cài đặt"
        PIP_CMD="pip3"
    elif command -v pip &> /dev/null; then
        print_success "pip đã cài đặt"
        PIP_CMD="pip"
    else
        print_error "pip không được tìm thấy. Vui lòng cài đặt pip"
        exit 1
    fi
}

# Install Python dependencies
install_dependencies() {
    print_status "Cài đặt Python dependencies..."
    
    if [ -f "requirements.txt" ]; then
        $PIP_CMD install -r requirements.txt
        print_success "Dependencies đã được cài đặt"
    else
        print_warning "requirements.txt không tìm thấy. Cài đặt dependencies cơ bản..."
        $PIP_CMD install langchain sentence-transformers faiss-cpu ollama PyPDF2 python-docx numpy scikit-learn
        print_success "Dependencies cơ bản đã được cài đặt"
    fi
}

# Check and install Ollama
install_ollama() {
    print_status "Kiểm tra Ollama..."
    
    if command -v ollama &> /dev/null; then
        print_success "Ollama đã được cài đặt"
    else
        print_status "Cài đặt Ollama..."
        curl -fsSL https://ollama.ai/install.sh | sh
        print_success "Ollama đã được cài đặt"
        
        # Start Ollama service
        print_status "Khởi động Ollama service..."
        ollama serve &
        sleep 5
    fi
    
    # Pull Gemma model
    print_status "Tải Gemma 2B model..."
    ollama pull gemma:2b
    print_success "Gemma 2B model đã sẵn sàng"
}

# Create directory structure
setup_directories() {
    print_status "Tạo cấu trúc thư mục..."
    
    mkdir -p documents
    mkdir -p vector_db
    mkdir -p logs
    
    print_success "Đã tạo thư mục: documents/, vector_db/, logs/"
}

# Create sample documents
create_sample_docs() {
    print_status "Tạo tài liệu mẫu..."
    
    # Sample legal document
    cat > documents/sample_legal_doc.txt << 'EOF'
THÔNG TƯ SỐ 01/2024
VỀ HƯỚNG DẪN THÀNH LẬP DOANH NGHIỆP

Điều 1. Điều kiện thành lập
1. Doanh nghiệp được thành lập khi có đủ các điều kiện sau:
   a) Có tên riêng phù hợp với quy định pháp luật
   b) Có người đại diện theo pháp luật
   c) Có trụ sở chính tại Việt Nam
   d) Có ngành nghề kinh doanh cụ thể

Điều 2. Hồ sơ thành lập
1. Hồ sơ đăng ký doanh nghiệp bao gồm:
   a) Đơn đăng ký doanh nghiệp
   b) Điều lệ công ty (đối với công ty TNHH và công ty cổ phần)
   c) Danh sách thành viên góp vốn
   d) Các giấy tờ khác theo quy định

Điều 3. Thời gian xử lý
1. Thời gian cấp Giấy chứng nhận đăng ký doanh nghiệp là 15 ngày làm việc kể từ ngày nhận đủ hồ sơ hợp lệ.
2. Trường hợp từ chối, cơ quan đăng ký kinh doanh phải thông báo bằng văn bản và nêu rõ lý do.
EOF

    cat > documents/sample_procedure.txt << 'EOF'
QUY TRÌNH ĐĂNG KÝ THUẾ CHO DOANH NGHIỆP

Bước 1: Chuẩn bị hồ sơ
- Giấy chứng nhận đăng ký doanh nghiệp
- Điều lệ công ty (bản sao có chứng thực)
- Hợp đồng thuê trụ sở (nếu có)

Bước 2: Nộp hồ sơ
- Nộp tại Chi cục Thuế nơi đặt trụ sở chính
- Thời gian tiếp nhận: trong giờ hành chính

Bước 3: Nhận kết quả  
- Thời gian: 3 ngày làm việc
- Nhận Giấy chứng nhận đăng ký thuế
EOF

    print_success "Đã tạo tài liệu mẫu trong documents/"
}

# Build vector database
build_vector_db() {
    print_status "Xây dựng vector database..."
    
    if [ -f "build_vectors.py" ]; then
        $PYTHON_CMD build_vectors.py --data_dir ./documents --output_dir ./vector_db
        print_success "Vector database đã được xây dựng"
    else
        print_error "Không tìm thấy build_vectors.py"
        return 1
    fi
}

# Test query
test_query() {
    print_status "Test query hệ thống..."
    
    if [ -f "query_rag.py" ]; then
        echo -e "\n${BLUE}=== TEST QUERY ===${NC}"
        $PYTHON_CMD query_rag.py --vector_db ./vector_db --query "Điều kiện thành lập doanh nghiệp là gì?"
        print_success "Test query hoàn thành"
    else
        print_error "Không tìm thấy query_rag.py"
        return 1
    fi
}

# Create launch scripts
create_launch_scripts() {
    print_status "Tạo launch scripts..."
    
    # Interactive mode script
    cat > run_interactive.sh << 'EOF'
#!/bin/bash
echo "🤖 Chạy RAG system ở chế độ tương tác..."
python3 query_rag.py --vector_db ./vector_db --interactive
EOF
    chmod +x run_interactive.sh
    
    # Build script
    cat > rebuild_vectors.sh << 'EOF'
#!/bin/bash
echo "🔄 Rebuild vector database..."
python3 build_vectors.py --data_dir ./documents --output_dir ./vector_db
echo "✅ Hoàn thành!"
EOF
    chmod +x rebuild_vectors.sh
    
    print_success "Đã tạo launch scripts: run_interactive.sh, rebuild_vectors.sh"
}

# Show usage instructions
show_usage() {
    echo -e "\n${GREEN}🎉 THIẾT LẬP HOÀN THÀNH!${NC}"
    echo "=========================="
    echo ""
    echo -e "${YELLOW}📁 Cấu trúc thư mục:${NC}"
    echo "  documents/     - Đặt file PDF, DOCX, TXT ở đây"
    echo "  vector_db/     - Vector database (đã build)"
    echo "  logs/          - Log files"
    echo ""
    echo -e "${YELLOW}🚀 Cách sử dụng:${NC}"
    echo ""
    echo -e "${BLUE}1. Thêm documents:${NC}"
    echo "   cp your_files.pdf documents/"
    echo "   ./rebuild_vectors.sh"
    echo ""
    echo -e "${BLUE}2. Query đơn lẻ:${NC}"
    echo "   python3 query_rag.py --vector_db ./vector_db --query \"Câu hỏi của bạn?\""
    echo ""
    echo -e "${BLUE}3. Chế độ tương tác:${NC}"
    echo "   ./run_interactive.sh"
    echo ""
    echo -e "${BLUE}4. Batch query:${NC}"
    echo "   python3 query_rag.py --vector_db ./vector_db --questions_file questions.txt"
    echo ""
    echo -e "${YELLOW}📖 Xem thêm:${NC} README.md"
    echo ""
}

# Main function
main() {
    echo -e "${BLUE}"
    cat << 'EOF'
 ____      _    ____   _                    _   
|  _ \    / \  / ___| | |    ___  __ _  __ _| |  
| |_) |  / _ \| |  _  | |   / _ \/ _` |/ _` | |  
|  _ <  / ___ \ |_| | | |__|  __/ (_| | (_| | |  
|_| \_\/_/   \_\____| |_____\___|\__, |\__,_|_|  
                                 |___/           
EOF
    echo -e "${NC}"
    
    # Run setup steps
    check_python
    check_pip
    install_dependencies
    install_ollama
    setup_directories
    create_sample_docs
    build_vector_db
    test_query
    create_launch_scripts
    show_usage
}

# Handle Ctrl+C
trap 'echo -e "\n${RED}❌ Thiết lập bị ngắt${NC}"; exit 1' INT

# Run main function
main "$@"