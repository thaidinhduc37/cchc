# vector_db.py

from services.vector_db import VectorDatabase
import os

def build_all_vectors():
    print("📦 Đang tạo vector cho tất cả các lĩnh vực...")
    dataset_root = "dataset"
    vdb = VectorDatabase()

    for domain in os.listdir(dataset_root):
        domain_path = os.path.join(dataset_root, domain)
        if os.path.isdir(domain_path):
            vdb.build_vectors_for_domain(domain, dataset_root)

    print("✅ Hoàn tất vector hóa!")

if __name__ == "__main__":
    build_all_vectors()
