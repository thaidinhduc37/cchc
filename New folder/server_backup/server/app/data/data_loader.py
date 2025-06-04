# app/data/data_loader.py
import json
import pandas as pd
import docx
from PyPDF2 import PdfReader

class DataLoader:
    def load_json(self, file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_txt(self, file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def load_pdf(self, file_path):
        text = ""
        with open(file_path, "rb") as f:
            reader = PdfReader(f)
            for page in reader.pages:
                text += page.extract_text()
        return text

    def load_docx(self, file_path):
        doc = docx.Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])

    def load_xlsx(self, file_path):
        df = pd.read_excel(file_path)
        return df.to_dict(orient="records")
