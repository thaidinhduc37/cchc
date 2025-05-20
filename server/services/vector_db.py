import os
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from services.unified_processor import DocumentProcessor

class VectorDatabase:
    def __init__(self):
        self.vectorizer = TfidfVectorizer()
        self.document_processor = DocumentProcessor()
        self.domain_docs = {}         # { domain: [doc1, doc2, ...] }
        self.domain_vectors = {}      # { domain: vector_matrix }

    def build_vectors_for_domain(self, domain: str, dataset_dir: str):
        domain_path = os.path.join(dataset_dir, domain)
        if not os.path.isdir(domain_path):
            print(f"❌ Không tìm thấy thư mục {domain_path}")
            return

        docs = []
        for file in os.listdir(domain_path):
            file_path = os.path.join(domain_path, file)
            if os.path.isfile(file_path):
                content = self.document_processor.extract_text(file_path)
                if content:
                    docs.append(content)

        if not docs:
            print(f"⚠️ Không có nội dung hợp lệ trong {domain}")
            return

        vectors = self.vectorizer.fit_transform(docs)
        self.domain_docs[domain] = docs
        self.domain_vectors[domain] = vectors
        self._save_embeddings(domain, docs)

        print(f"✅ Đã tạo vector cho lĩnh vực: {domain} ({len(docs)} tài liệu)")

    def _save_embeddings(self, domain: str, docs: list):
        os.makedirs("vector_db/embeddings", exist_ok=True)
        path = f"vector_db/embeddings/{domain}.json"
        data = [{"content": doc} for doc in docs]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_vectors_for_domain(self, domain: str):
        path = f"vector_db/embeddings/{domain}.json"
        if not os.path.exists(path):
            return

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        docs = [item["content"] for item in data]
        if docs:
            vectors = self.vectorizer.fit_transform(docs)
            self.domain_docs[domain] = docs
            self.domain_vectors[domain] = vectors

    def search(self, domain: str, query: str, top_k: int = 3):
        if domain not in self.domain_docs:
            self.load_vectors_for_domain(domain)

        if domain not in self.domain_vectors:
            return []

        query_vec = self.vectorizer.transform([query])
        sims = cosine_similarity(query_vec, self.domain_vectors[domain]).flatten()
        indices = sims.argsort()[::-1][:top_k]
        return [(self.domain_docs[domain][i], float(sims[i])) for i in indices]
