import os
import argparse
from services.vector_rag.document_processor import DocumentProcessor
from services.vector_rag.vector_manager import VectorStoreManager
from services.vector_rag.config import SystemConfig





def build_vector_for_domain(domain, force_rebuild=False):
    cfg = SystemConfig()
    data_dir = os.path.join(cfg.data_path, domain)
    store_dir = os.path.join(cfg.vector_store_path, f"{domain}_vectorstore")

    if force_rebuild and os.path.exists(store_dir):
        import shutil
        shutil.rmtree(store_dir)
        print(f"[CLEAN] Đã xóa vectorstore cũ: {store_dir}")

    print(f"[INFO] Đang xử lý dữ liệu lĩnh vực: {domain} - {data_dir}")
    print(f"[DEBUG] data_dir: {data_dir}, exists: {os.path.exists(data_dir)}")

    processor = DocumentProcessor(system_config=cfg)
    docs = processor.process_documents(data_dir, domain=domain)
    print(f"[INFO] Đã load {len(docs)} tài liệu/chunks.")

    vector_manager = VectorStoreManager(system_config=cfg)
    vector_manager.create_domain_vector_store(docs, domain)
    print(f"[SUCCESS] Đã tạo vector store cho lĩnh vực: {domain}")

def clean_all_vectorstores():
    cfg = SystemConfig()
    if os.path.exists(cfg.vector_store_path):
        import shutil
        shutil.rmtree(cfg.vector_store_path)
        print(f"[CLEAN] Đã xóa toàn bộ vector_store ở {cfg.vector_store_path}")
    os.makedirs(cfg.vector_store_path, exist_ok=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build vector store cho từng lĩnh vực.")
    parser.add_argument('--domain', type=str, help="Chỉ build 1 lĩnh vực (VD: xuatnhapcanh)")
    parser.add_argument('--build', action='store_true', help="Chỉ build, không xóa vectorstore cũ")
    parser.add_argument('--force', action='store_true', help="Force: Xóa và build lại vectorstore")
    parser.add_argument('--clean', action='store_true', help="Xóa toàn bộ vectorstore")

    args = parser.parse_args()
    cfg = SystemConfig()

    if args.clean:
        clean_all_vectorstores()

    if args.domain:
        build_vector_for_domain(args.domain, force_rebuild=args.force)
    elif args.build or args.force:
        # Build cho tất cả domain (trừ vector_stores)
        for domain in os.listdir(cfg.data_path):
            domain_path = os.path.join(cfg.data_path, domain)
            if os.path.isdir(domain_path) and not domain.startswith("vector_stores"):
                build_vector_for_domain(domain, force_rebuild=args.force)
    else:
        parser.print_help()
