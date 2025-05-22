import os
import json
import docx
import pandas as pd
from PyPDF2 import PdfReader

class DocumentProcessor:
    def extract_text(self, file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            return self._from_pdf(file_path)
        elif ext == ".docx":
            return self._from_docx(file_path)
        elif ext == ".xlsx":
            return self._from_xlsx(file_path)
        elif ext == ".json":
            return self._from_json(file_path)
        elif ext == ".txt":
            return self._from_txt(file_path)
        else:
            print(f"Định dạng không hỗ trợ: {ext}")
            return ""

    def _from_pdf(self, file_path: str) -> str:
        text = ""
        try:
            with open(file_path, "rb") as file:
                reader = PdfReader(file)
                for page in reader.pages:
                    text += page.extract_text() or ""
        except Exception as e:
            print(f"Lỗi khi đọc PDF: {e}")
        return text

    def _from_docx(self, file_path: str) -> str:
        text = ""
        try:
            doc = docx.Document(file_path)
            for para in doc.paragraphs:
                text += para.text + "\n"
        except Exception as e:
            print(f"Lỗi khi đọc DOCX: {e}")
        return text

    def _from_xlsx(self, file_path: str) -> str:
        try:
            df = pd.read_excel(file_path)
            return df.to_string(index=False)
        except Exception as e:
            print(f"Lỗi khi đọc XLSX: {e}")
            return ""

    def _from_json(self, file_path: str) -> str:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return json.dumps(data, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Lỗi khi đọc JSON: {e}")
            return ""

    def _from_txt(self, file_path: str) -> str:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"Lỗi khi đọc TXT: {e}")
            return ""