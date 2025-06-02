import sys
import os
import argparse


# ✅ Thêm thư mục gốc vào path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.text_splitter import split_text_into_chunks
from app.vector.vector_creator import VectorCreator

SUPPORTED_EXTENSIONS = [".txt", ".docx", ".pdf"]

def read_text_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def read_docx_file(path):
    from docx import Document
    doc = Document(path)
    return "\n".join([para.text.strip() for para in doc.paragraphs if para.text.strip()])

def load_documents_from_folder(folder):
    chunks = []
    for filename in os.listdir(folder):
        ext = os.path.splitext(filename)[1].lower()
        path = os.path.join(folder, filename)
        if ext == ".txt":
            text = read_text_file(path)
        elif ext == ".docx":
            text = read_docx_file(path)
        else:
            continue
        chunks.extend(split_text_into_chunks(text))
    return chunks

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", required=True, help="Tên lĩnh vực (ví dụ: xuatnhapcanh)")
    args = parser.parse_args()

    domain = args.domain
    folder = f"dataset/{domain}"

    print(f"📚 Đang xử lý dữ liệu trong {folder}...")

    chunks = load_documents_from_folder(folder)
    vc = VectorCreator()
    vc.load_corpus_from_chunks(chunks)
    vc.save_corpus(domain)

    print(f"✅ Đã tạo xong vector_store/{domain}/corpus.json ({len(chunks)} đoạn)")
