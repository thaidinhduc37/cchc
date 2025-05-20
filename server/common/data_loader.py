import json
import os
import PyPDF2
from PyPDF2 import PdfReader

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOMAINS_DIR = os.path.join(BASE_DIR, "..", "domains")
PDF_DIR = os.path.join(BASE_DIR, "..", "web_server", "pdfs")

def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_all_data():
    data = {}
    base_path = 'domains'
    for domain in os.listdir(base_path):
        domain_path = os.path.join(base_path, domain)
        if os.path.isdir(domain_path):
            json_file = os.path.join(domain_path, f'{domain}.json')
            if os.path.exists(json_file):
                data[domain] = load_json(json_file)

    print("Dữ liệu đã load từ JSON:", data)  # In dữ liệu JSON ra console
    return data

def search_in_pdf(domain, query):
    """ Tìm kiếm trong file PDF của lĩnh vực tương ứng """
    pdf_path = os.path.join(PDF_DIR, f"{domain}.pdf")
    if not os.path.exists(pdf_path):
        return None
    
    with open(pdf_path, "rb") as f:
        reader = PdfReader(f)
        text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
        
        if query.lower() in text.lower():
            return f"Thông tin liên quan được tìm thấy trong tài liệu {domain}.pdf"
    
    return None

def extract_text_from_pdf(pdf_path):
    text = ""
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text()
    return text

# Sử dụng
pdf_text = extract_text_from_pdf("web_server/pdfs/cancuoc.pdf")
print(pdf_text)