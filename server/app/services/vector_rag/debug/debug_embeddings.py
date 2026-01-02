# server/services/vector_rag/test_embeddings.py
"""
Vietnamese Legal Embedding Models Benchmark
🧪 Test multiple embedding models on Vietnamese legal content
📊 Compare performance on actual legal queries
"""

import sys
import os
import time
import numpy as np
import requests
from typing import List, Dict, Any, Tuple
from pathlib import Path
from datetime import datetime
import json

# Add parent to path
sys.path.append(str(Path(__file__).parent.parent.parent))

try:
    from sentence_transformers import SentenceTransformer
    ST_AVAILABLE = True
except ImportError:
    ST_AVAILABLE = False

try:
    from transformers import AutoTokenizer, AutoModel
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

class EmbeddingBenchmark:
    """Benchmark embedding models on Vietnamese legal content"""
    
    def __init__(self):
        self.models = {}
        self.legal_text = ""
        self.legal_chunks = []
        self.results = {}
        
        # Test queries from Round 2 failures
        self.test_queries = [
            ("Công dân Việt Nam có quyền xuất cảnh không?", "điều 5"),
            ("Hộ chiếu phổ thông có thời hạn bao lâu?", "điều 15"),
            ("Xuất cảnh bằng hộ chiếu nào?", "điều 6"),
            ("Điều kiện để được cấp hộ chiếu phổ thông?", "điều 15"),
            ("Trường hợp nào bị từ chối cấp hộ chiếu?", "điều 21"),
            ("Người đang chấp hành án phạt tù có được xuất cảnh không?", "điều 8"),
            ("Điều 36 quy định về trường hợp nào bị tạm hoãn xuất cảnh?", "điều 36"),
            ("Thẩm quyền thu hồi hộ chiếu thuộc về ai?", "điều 30"),
            ("Người có hai quốc tịch xuất cảnh Việt Nam bằng hộ chiếu nào?", "điều 6"),
            ("Công dân Việt Nam bị kết án tù chung thân, sau khi được ân xá có được xuất cảnh không?", "điều 8")
        ]
        
        # Log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = Path("services/vector_rag") / f"embedding_benchmark_{timestamp}.log"
        self.log_file.parent.mkdir(exist_ok=True)
        
        print(f"📄 Benchmark log: {self.log_file}")
    
    def log(self, message, level="INFO"):
        """Log to both console and file"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_line = f"[{timestamp}] {level}: {message}"
        print(log_line)
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_line + "\n")
    
    def download_legal_text(self):
        """Download legal text from thuvienphapluat.vn"""
        self.log("📥 Downloading legal text...")
        
        # For demo purposes, we'll use a sample text
        # In reality, you'd scrape or have the full legal text
        sample_legal_text = """
        LUẬT XUẤT CẢNH, NHẬP CẢNH CỦA CÔNG DÂN VIỆT NAM
        
        Điều 5. Quyền và nghĩa vụ của công dân Việt Nam
        1. Công dân Việt Nam có các quyền sau đây:
        a) Được bảo hộ của Nhà nước Việt Nam khi ở nước ngoài;
        b) Được cấp giấy tờ xuất nhập cảnh theo quy định của Luật này;
        c) Được xuất cảnh, nhập cảnh theo quy định của Luật này;
        d) Được thông tin về tình hình an ninh, trật tự, an toàn xã hội của nước, vùng lãnh thổ dự định đến;
        
        Điều 6. Giấy tờ xuất nhập cảnh
        1. Giấy tờ xuất nhập cảnh của công dân Việt Nam bao gồm:
        a) Hộ chiếu ngoại giao;
        b) Hộ chiếu công vụ;
        c) Hộ chiếu phổ thông;
        d) Giấy thông hành.
        
        Điều 8. Đối tượng không được xuất cảnh
        1. Công dân Việt Nam không được xuất cảnh trong các trường hợp sau đây:
        a) Bị truy cứu trách nhiệm hình sự hoặc đang chấp hành hình phạt tù;
        b) Đang bị áp dụng biện pháp ngăn chặn xuất cảnh;
        c) Có nghĩa vụ tài chính với Nhà nước chưa thực hiện xong;
        
        Điều 15. Cấp hộ chiếu phổ thông ở trong nước
        1. Hộ chiếu phổ thông cấp cho công dân Việt Nam từ đủ 14 tuổi trở lên có thời hạn 10 năm.
        2. Hộ chiếu phổ thông cấp cho công dân Việt Nam chưa đủ 14 tuổi có thời hạn 05 năm.
        3. Hộ chiếu phổ thông cấp theo thủ tục rút gọn có thời hạn không quá 12 tháng.
        
        Điều 21. Từ chối cấp giấy tờ xuất nhập cảnh
        1. Việc cấp giấy tờ xuất nhập cảnh bị từ chối trong các trường hợp sau đây:
        a) Chưa chấp hành xong quyết định xử phạt vi phạm hành chính;
        b) Bị tạm hoãn xuất cảnh theo quy định của Luật này;
        c) Vì lý do quốc phòng, an ninh theo quyết định của Bộ trưởng Bộ Quốc phòng;
        
        Điều 30. Thu hồi, hủy giá trị sử dụng hộ chiếu ngoại giao, hộ chiếu công vụ
        1. Hộ chiếu ngoại giao, hộ chiếu công vụ bị thu hồi, hủy giá trị sử dụng trong các trường hợp sau đây:
        a) Người được cấp hộ chiếu không còn thuộc đối tượng được cấp hộ chiếu;
        b) Hộ chiếu bị mất theo thông báo của người được cấp hộ chiếu;
        
        Điều 36. Các trường hợp bị tạm hoãn xuất cảnh
        1. Công dân Việt Nam bị tạm hoãn xuất cảnh trong các trường hợp sau đây:
        a) Là bị can, bị cáo đang trong quá trình điều tra, truy tố, xét xử;
        b) Đang phải chấp hành các bản án, quyết định về hình sự, dân sự;
        c) Chưa hoàn thành nghĩa vụ nộp thuế theo quy định của pháp luật về thuế;
        d) Đang bị cưỡng chế thi hành quyết định xử phạt vi phạm hành chính;
        """
        
        self.legal_text = sample_legal_text
        self.log(f"✅ Legal text loaded: {len(self.legal_text)} chars")
        
        # Split into chunks by articles
        self._split_into_chunks()
    
    def _split_into_chunks(self):
        """Split legal text into article chunks"""
        import re
        
        # Split by articles
        article_pattern = r'(Điều\s+\d+\..*?)(?=Điều\s+\d+\.|$)'
        matches = re.findall(article_pattern, self.legal_text, re.DOTALL)
        
        self.legal_chunks = []
        for match in matches:
            chunk = match.strip()
            if len(chunk) > 50:  # Skip very short chunks
                self.legal_chunks.append(chunk)
        
        self.log(f"📊 Split into {len(self.legal_chunks)} article chunks")
    
    def load_models(self):
        """Load embedding models"""
        self.log("🤖 Loading embedding models...")
        
        model_configs = {
            "current": {
                "name": "sentence-transformers/all-MiniLM-L6-v2",
                "type": "sentence_transformer"
            },
            "truro7": {
                "name": "truro7/vn-law-embedding", 
                "type": "sentence_transformer"
            },
            "huydang": {
                "name": "huyydangg/DEk21_hcmute_embedding_wseg",
                "type": "sentence_transformer"
            }
        }
        
        # Try to load Vietnamese-specific models
        try:
            model_configs["vietnamese"] = {
                "name": "huyydangg/DEk21_hcmute_embedding",
                "type": "sentence_transformer"
            }
        except:
            self.log("⚠️ Could not load Vietnamese embedding model")
        
        # Try to load PhoBERT
        try:
            model_configs["phobert"] = {
                "name": "vinai/phobert-base",
                "type": "transformer"
            }
        except:
            self.log("⚠️ Could not load PhoBERT")
        
        # Load available models
        for model_id, config in model_configs.items():
            try:
                self.log(f"Loading {model_id}: {config['name']}...")
                
                if config["type"] == "sentence_transformer" and ST_AVAILABLE:
                    model = SentenceTransformer(config["name"])
                    self.models[model_id] = {
                        "model": model,
                        "type": "sentence_transformer",
                        "name": config["name"]
                    }
                    self.log(f"✅ Loaded {model_id}")
                    
                elif config["type"] == "transformer" and TRANSFORMERS_AVAILABLE:
                    tokenizer = AutoTokenizer.from_pretrained(config["name"])
                    model = AutoModel.from_pretrained(config["name"])
                    self.models[model_id] = {
                        "model": model,
                        "tokenizer": tokenizer,
                        "type": "transformer",
                        "name": config["name"]
                    }
                    self.log(f"✅ Loaded {model_id}")
                    
            except Exception as e:
                self.log(f"❌ Failed to load {model_id}: {e}")
        
        self.log(f"📊 Successfully loaded {len(self.models)} models")
    
    def encode_text(self, model_id: str, texts: List[str]) -> np.ndarray:
        """Encode texts using specified model"""
        model_info = self.models[model_id]
        
        if model_info["type"] == "sentence_transformer":
            return model_info["model"].encode(texts)
            
        elif model_info["type"] == "transformer":
            model = model_info["model"]
            tokenizer = model_info["tokenizer"]
            
            embeddings = []
            for text in texts:
                inputs = tokenizer(text, return_tensors="pt", 
                                 max_length=512, truncation=True, padding=True)
                with torch.no_grad():
                    outputs = model(**inputs)
                    # Use mean pooling
                    embedding = outputs.last_hidden_state.mean(dim=1).squeeze().numpy()
                    embeddings.append(embedding)
            
            return np.array(embeddings)
        
        else:
            raise ValueError(f"Unknown model type: {model_info['type']}")
    
    def benchmark_model(self, model_id: str) -> Dict[str, Any]:
        """Benchmark a single model"""
        self.log(f"🧪 Benchmarking {model_id}...")
        
        model_info = self.models[model_id]
        
        # Measure encoding speed
        start_time = time.time()
        chunk_embeddings = self.encode_text(model_id, self.legal_chunks)
        encoding_time = time.time() - start_time
        
        self.log(f"⏱️  Encoding time: {encoding_time:.2f}s for {len(self.legal_chunks)} chunks")
        
        # Build simple similarity search
        if not FAISS_AVAILABLE:
            self.log("⚠️ FAISS not available, using numpy similarity")
            chunk_embeddings_norm = chunk_embeddings / np.linalg.norm(chunk_embeddings, axis=1, keepdims=True)
        else:
            # Use FAISS for similarity search
            index = faiss.IndexFlatIP(chunk_embeddings.shape[1])
            # Normalize embeddings for cosine similarity
            chunk_embeddings_norm = chunk_embeddings / np.linalg.norm(chunk_embeddings, axis=1, keepdims=True)
            index.add(chunk_embeddings_norm.astype('float32'))
        
        # Test queries
        query_results = []
        total_query_time = 0
        
        for query, expected_article in self.test_queries:
            start_time = time.time()
            
            # Encode query
            query_embedding = self.encode_text(model_id, [query])
            query_embedding_norm = query_embedding / np.linalg.norm(query_embedding)
            
            # Search
            if FAISS_AVAILABLE:
                similarities, indices = index.search(query_embedding_norm.astype('float32'), k=5)
                top_chunks = [self.legal_chunks[i] for i in indices[0]]
                top_scores = similarities[0]
            else:
                # Numpy similarity
                similarities = np.dot(chunk_embeddings_norm, query_embedding_norm.T).flatten()
                top_indices = np.argsort(similarities)[::-1][:5]
                top_chunks = [self.legal_chunks[i] for i in top_indices]
                top_scores = similarities[top_indices]
            
            query_time = time.time() - start_time
            total_query_time += query_time
            
            # Check if expected article is in top results
            found_expected = False
            for i, chunk in enumerate(top_chunks):
                if expected_article.lower() in chunk.lower():
                    found_expected = True
                    break
            
            query_results.append({
                "query": query,
                "expected_article": expected_article,
                "found_expected": found_expected,
                "top_chunk": top_chunks[0][:100] + "..." if top_chunks else "No results",
                "top_score": float(top_scores[0]) if len(top_scores) > 0 else 0.0,
                "query_time": query_time
            })
            
            self.log(f"   Query: {query[:50]}...")
            self.log(f"   Expected: {expected_article}, Found: {found_expected}")
            self.log(f"   Top result: {top_chunks[0][:100]}..." if top_chunks else "   No results")
        
        # Calculate metrics
        accuracy = sum(1 for r in query_results if r["found_expected"]) / len(query_results)
        avg_query_time = total_query_time / len(query_results)
        
        result = {
            "model_id": model_id,
            "model_name": model_info["name"],
            "encoding_time": encoding_time,
            "avg_query_time": avg_query_time,
            "accuracy": accuracy,
            "query_results": query_results
        }
        
        self.log(f"📊 {model_id} Results:")
        self.log(f"   Accuracy: {accuracy:.2%}")
        self.log(f"   Avg query time: {avg_query_time:.3f}s")
        self.log(f"   Encoding time: {encoding_time:.2f}s")
        
        return result
    
    def run_benchmark(self):
        """Run complete benchmark"""
        self.log("🚀 Starting embedding benchmark...")
        
        # Download legal text
        self.download_legal_text()
        
        # Load models
        self.load_models()
        
        if not self.models:
            self.log("❌ No models loaded successfully")
            return
        
        # Benchmark each model
        for model_id in self.models:
            try:
                result = self.benchmark_model(model_id)
                self.results[model_id] = result
            except Exception as e:
                self.log(f"❌ Error benchmarking {model_id}: {e}")
        
        # Generate comparison report
        self._generate_comparison_report()
    
    def _generate_comparison_report(self):
        """Generate comparison report"""
        self.log("\n" + "="*80)
        self.log("📊 EMBEDDING MODELS COMPARISON REPORT")
        self.log("="*80)
        
        if not self.results:
            self.log("❌ No results to compare")
            return
        
        # Sort by accuracy
        sorted_results = sorted(self.results.items(), 
                              key=lambda x: x[1]["accuracy"], 
                              reverse=True)
        
        self.log(f"📈 RANKING BY ACCURACY:")
        for i, (model_id, result) in enumerate(sorted_results, 1):
            self.log(f"   {i}. {model_id}: {result['accuracy']:.2%} accuracy")
        
        self.log(f"\n⚡ SPEED COMPARISON:")
        for model_id, result in sorted_results:
            self.log(f"   {model_id}: {result['avg_query_time']:.3f}s per query")
        
        self.log(f"\n🎯 DETAILED RESULTS:")
        for model_id, result in sorted_results:
            self.log(f"\n   📊 {model_id.upper()} ({result['model_name']}):")
            self.log(f"      Accuracy: {result['accuracy']:.2%}")
            self.log(f"      Avg query time: {result['avg_query_time']:.3f}s")
            self.log(f"      Encoding time: {result['encoding_time']:.2f}s")
            
            # Show failed queries
            failed_queries = [r for r in result['query_results'] if not r['found_expected']]
            if failed_queries:
                self.log(f"      Failed queries ({len(failed_queries)}):")
                for fq in failed_queries:
                    self.log(f"        - {fq['query'][:50]}... (expected: {fq['expected_article']})")
        
        # Save detailed results to JSON
        json_file = self.log_file.with_suffix('.json')
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        self.log(f"\n📄 Detailed results saved to: {json_file}")
        
        # Recommendations
        self.log(f"\n💡 RECOMMENDATIONS:")
        if sorted_results:
            best_model = sorted_results[0]
            self.log(f"   🏆 Best overall: {best_model[0]} ({best_model[1]['accuracy']:.2%} accuracy)")
            
            # Find fastest model
            fastest_model = min(sorted_results, key=lambda x: x[1]['avg_query_time'])
            self.log(f"   ⚡ Fastest: {fastest_model[0]} ({fastest_model[1]['avg_query_time']:.3f}s per query)")
            
            # Recommendations based on use case
            if best_model[1]['accuracy'] >= 0.8:
                self.log(f"   ✅ Recommended: Use {best_model[0]} for best accuracy")
            elif fastest_model[1]['accuracy'] >= 0.6:
                self.log(f"   ⚡ Recommended: Use {fastest_model[0]} for balanced performance")
            else:
                self.log(f"   ⚠️ All models show low accuracy - consider data preprocessing")

def main():
    """Main benchmark function"""
    print("🧪 Starting Vietnamese Legal Embedding Benchmark...")
    
    benchmark = EmbeddingBenchmark()
    benchmark.run_benchmark()
    
    print(f"\n✅ Benchmark completed! Check log file: {benchmark.log_file}")

if __name__ == "__main__":
    main()