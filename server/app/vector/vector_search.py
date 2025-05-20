# app/vector/vector_search.py

from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class VectorSearch:
    def __init__(self, vectors: np.ndarray, corpus: list):
        """
        Khởi tạo VectorSearch với dữ liệu đã được vector hóa.
        """
        self.vectors = vectors
        self.corpus = corpus

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> list:
        """
        Tìm kiếm các văn bản có độ tương đồng cao nhất.
        """
        similarities = cosine_similarity(query_vector, self.vectors)
        scores = similarities[0]
        top_indices = np.argsort(scores)[::-1][:top_k]
        results = [(self.corpus[i], scores[i]) for i in top_indices]

        return results
