
import os
from services.rag_system import DocumentRAGSystem

def build_all_vectors():
    dataset_root = "dataset"
    output_root = "vector_store"
    os.makedirs(output_root, exist_ok=True)

    print("📦 Đang tạo vector nâng cao cho tất cả các lĩnh vực...")
    for domain in os.listdir(dataset_root):
        domain_path = os.path.join(dataset_root, domain)
        if os.path.isdir(domain_path):
            print(f"➡️  Đang xử lý: {domain}")
            rag = DocumentRAGSystem()
            rag.process_directory(domain_path)
            rag.vector_store.save(os.path.join(output_root, domain))
    print("✅ Hoàn tất vector hóa nâng cao!")

if __name__ == "__main__":
    build_all_vectors()
