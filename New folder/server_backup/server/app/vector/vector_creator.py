# app/vector/vector_creator.py

from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

class VectorCreator:
    def __init__(self):
        """
        Khởi tạo bộ vectorizer.
        """
        self.vectorizer = TfidfVectorizer()
        self.corpus = []
        self.vectors = []

    def add_document(self, content: str):
        """
        Thêm tài liệu vào corpus và tạo vector.
        """
        self.corpus.append(content)
        self.vectors = self.vectorizer.fit_transform(self.corpus)

    def get_vectors(self) -> np.ndarray:
        """
        Lấy toàn bộ vectors đã tạo.
        """
        return self.vectors

    def get_feature_names(self) -> list:
        """
        Lấy danh sách từ khóa đã học.
        """
        return self.vectorizer.get_feature_names_out()
