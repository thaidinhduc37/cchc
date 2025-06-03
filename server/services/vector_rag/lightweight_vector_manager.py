# server/services/vector_rag/lightweight_vector_manager.py
"""
Vector manager siêu nhẹ sử dụng ChromaDB
Thay thế FAISS + HuggingFace với solution nhẹ hơn
"""
import os
import json
import uuid
from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

# Thay đổi import ở đầu file:
from .lightweight_config import VECTOR_CONFIG, SYSTEM_CONFIG
from .lightweight_embeddings import create_embeddings, LightweightEmbeddings
from .lightweight_document_processor import LegalDocument

logger = logging.getLogger(__name__)

class LightweightVectorManager:
    """
    Vector manager siêu nhẹ với ChromaDB
    RAM usage: 10x ít hơn FAISS+HuggingFace
    """
    
    def __init__(self, config=None, system_config=None):
        self.config = config or VECTOR_CONFIG
        self.system_config = system_config or SYSTEM_CONFIG
        
        # Initialize embeddings
        self.embeddings = create_embeddings()
        
        # Initialize ChromaDB
        self.client = None
        self.collection = None
        self._initialize_chromadb()
        
        # Metadata
        self.stats = {
            'total_documents': 0,
            'last_updated': None,
            'embedding_model': getattr(self.embeddings, 'config', {}).get('model_name', 'unknown')
        }
    
    def _initialize_chromadb(self):
        """Khởi tạo ChromaDB client và collection"""
        if not CHROMADB_AVAILABLE:
            raise ImportError(
                "ChromaDB không có. Cài đặt: pip install chromadb"
            )
        
        try:
            # Setup persistent client
            self.client = chromadb.PersistentClient(
                path=self.config.persist_directory
            )
            
            logger.info(f"🗄️ ChromaDB initialized at: {self.config.persist_directory}")
            
            # Get or create collection
            try:
                self.collection = self.client.get_collection(
                    name=self.config.collection_name
                )
                logger.info(f"📂 Loaded existing collection: {self.config.collection_name}")
                
                # Load stats
                self._load_stats()
                
            except Exception:
                # Create new collection
                self.collection = self.client.create_collection(
                    name=self.config.collection_name,
                    metadata={"description": "Xuất nhập cảnh legal documents"}
                )
                logger.info(f"✨ Created new collection: {self.config.collection_name}")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize ChromaDB: {e}")
            raise
    
    def _load_stats(self):
        """Load thống kê từ collection metadata"""
        try:
            collection_info = self.collection.get()
            self.stats['total_documents'] = len(collection_info['ids'])
            logger.info(f"📊 Collection has {self.stats['total_documents']} documents")
        except Exception as e:
            logger.warning(f"⚠️ Failed to load stats: {e}")
    
    def _save_stats(self):
        """Lưu thống kê"""
        self.stats['last_updated'] = datetime.now().isoformat()
        
        # Save to file
        stats_file = os.path.join(self.config.persist_directory, "stats.json")
        try:
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"⚠️ Failed to save stats: {e}")
    
    def add_documents(self, documents: List[LegalDocument]) -> bool:
        """Thêm documents vào vector store"""
        if not documents:
            logger.warning("⚠️ No documents to add")
            return False
        
        logger.info(f"🔄 Adding {len(documents)} documents to vector store...")
        
        try:
            # Prepare data for ChromaDB
            ids = []
            texts = []
            metadatas = []
            
            for doc in documents:
                # Generate unique ID
                doc_id = str(uuid.uuid4())
                ids.append(doc_id)
                texts.append(doc.page_content)
                
                # Prepare metadata (ChromaDB yêu cầu primitive types)
                metadata = {}
                for key, value in doc.metadata.items():
                    if isinstance(value, (str, int, float, bool)):
                        metadata[key] = value
                    elif isinstance(value, list):
                        # Convert list to string for ChromaDB
                        metadata[key] = json.dumps(value) if value else "[]"
                    else:
                        metadata[key] = str(value)
                
                metadatas.append(metadata)
            
            # Generate embeddings
            logger.info("🧮 Generating embeddings...")
            embeddings = self.embeddings.embed_documents(texts)
            
            # Add to ChromaDB
            self.collection.add(
                ids=ids,
                documents=texts,
                metadatas=metadatas,
                embeddings=embeddings
            )
            
            # Update stats
            self.stats['total_documents'] += len(documents)
            self._save_stats()
            
            logger.info(f"✅ Successfully added {len(documents)} documents")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to add documents: {e}")
            return False
    
    def search_similar(self, 
                      query: str, 
                      k: int = None, 
                      filter_metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Tìm kiếm similar documents"""
        k = k or self.config.k
        
        try:
            logger.debug(f"🔍 Searching for: {query[:50]}...")
            
            # Generate query embedding
            query_embedding = self.embeddings.embed_query(query)
            
            # Prepare filter (ChromaDB format)
            where_clause = None
            if filter_metadata:
                where_clause = {}
                for key, value in filter_metadata.items():
                    where_clause[key] = value
            
            # Search
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                where=where_clause,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Format results
            formatted_results = []
            if results['ids'] and results['ids'][0]:
                for i in range(len(results['ids'][0])):
                    result = {
                        'id': results['ids'][0][i],
                        'content': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'score': 1 - results['distances'][0][i],  # Convert distance to similarity
                    }
                    
                    # Parse back JSON metadata
                    if 'legal_references' in result['metadata']:
                        try:
                            result['metadata']['legal_references'] = json.loads(
                                result['metadata']['legal_references']
                            )
                        except:
                            pass
                    
                    formatted_results.append(result)
            
            logger.debug(f"🎯 Found {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
            return []
    
    def search_by_legal_reference(self, reference: str, k: int = 5) -> List[Dict[str, Any]]:
        """Tìm kiếm theo tham chiếu pháp lý (Điều, Khoản, Điểm)"""
        # Tìm exact match trong content trước
        results = self.search_similar(reference, k=k*2)
        
        # Filter và rank theo độ chính xác
        legal_results = []
        for result in results:
            content = result['content'].lower()
            ref_lower = reference.lower()
            
            # Bonus score nếu có exact match
            if ref_lower in content:
                result['score'] += 0.2
                legal_results.append(result)
        
        # Sort theo score và return top k
        legal_results.sort(key=lambda x: x['score'], reverse=True)
        return legal_results[:k]
    
    def search_by_document_type(self, doc_type: str, query: str = "", k: int = 5) -> List[Dict[str, Any]]:
        """Tìm kiếm theo loại văn bản"""
        filter_metadata = {'doc_type': doc_type}
        
        if query:
            return self.search_similar(query, k=k, filter_metadata=filter_metadata)
        else:
            # Get all documents of this type
            try:
                results = self.collection.get(
                    where=filter_metadata,
                    limit=k,
                    include=['documents', 'metadatas']
                )
                
                formatted_results = []
                for i in range(len(results['ids'])):
                    result = {
                        'id': results['ids'][i],
                        'content': results['documents'][i],
                        'metadata': results['metadatas'][i],
                        'score': 1.0  # No scoring for direct retrieval
                    }
                    formatted_results.append(result)
                
                return formatted_results
                
            except Exception as e:
                logger.error(f"❌ Document type search failed: {e}")
                return []
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Lấy thống kê collection"""
        try:
            collection_info = self.collection.get()
            
            # Count by document types
            doc_types = {}
            file_types = {}
            
            for metadata in collection_info.get('metadatas', []):
                doc_type = metadata.get('doc_type', 'unknown')
                file_type = metadata.get('file_type', 'unknown')
                
                doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
                file_types[file_type] = file_types.get(file_type, 0) + 1
            
            stats = {
                'total_documents': len(collection_info['ids']),
                'collection_name': self.config.collection_name,
                'embedding_model': self.stats.get('embedding_model', 'unknown'),
                'last_updated': self.stats.get('last_updated'),
                'doc_types': doc_types,
                'file_types': file_types,
                'persist_directory': self.config.persist_directory
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Failed to get stats: {e}")
            return {}
    
    def delete_collection(self) -> bool:
        """Xóa toàn bộ collection"""
        try:
            self.client.delete_collection(self.config.collection_name)
            logger.info(f"🗑️ Deleted collection: {self.config.collection_name}")
            
            # Recreate empty collection
            self.collection = self.client.create_collection(
                name=self.config.collection_name,
                metadata={"description": "Xuất nhập cảnh legal documents"}
            )
            
            # Reset stats
            self.stats = {
                'total_documents': 0,
                'last_updated': datetime.now().isoformat(),
                'embedding_model': getattr(self.embeddings, 'config', {}).get('model_name', 'unknown')
            }
            self._save_stats()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to delete collection: {e}")
            return False
    
    def backup_collection(self, backup_path: str) -> bool:
        """Backup collection data"""
        try:
            collection_data = self.collection.get(
                include=['documents', 'metadatas', 'embeddings']
            )
            
            backup_data = {
                'collection_name': self.config.collection_name,
                'backup_date': datetime.now().isoformat(),
                'data': collection_data,
                'stats': self.stats
            }
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 Collection backed up to: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Backup failed: {e}")
            return False
    
    def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Lấy document theo ID"""
        try:
            results = self.collection.get(
                ids=[doc_id],
                include=['documents', 'metadatas']
            )
            
            if results['ids']:
                return {
                    'id': results['ids'][0],
                    'content': results['documents'][0],
                    'metadata': results['metadatas'][0]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get document {doc_id}: {e}")
            return None

class XuatNhapCanhRetriever:
    """Retriever chuyên biệt cho lĩnh vực xuất nhập cảnh"""
    
    def __init__(self, vector_manager: LightweightVectorManager):
        self.vector_manager = vector_manager
        
        # Keywords mapping cho smart retrieval
        self.topic_keywords = {
            'visa': ['visa', 'thị thực', 'miễn thị'],
            'passport': ['hộ chiếu', 'passport'],
            'entry': ['nhập cảnh', 'xuất cảnh', 'entry', 'exit'],
            'residence': ['cư trú', 'tạm trú', 'thường trú'],
            'work': ['lao động', 'làm việc', 'work permit'],
            'procedure': ['thủ tục', 'hồ sơ', 'giấy tờ'],
            'fee': ['phí', 'lệ phí', 'chi phí'],
            'time': ['thời gian', 'thời hạn', 'hạn chế']
        }
    
    def retrieve_relevant_documents(self, 
                                  query: str, 
                                  k: int = 3,
                                  include_legal_refs: bool = True) -> List[Dict[str, Any]]:
        """Retrieve documents có liên quan đến query"""
        
        # Detect topic từ query
        detected_topics = self._detect_topics(query)
        
        # Multi-strategy search
        all_results = []
        
        # 1. Semantic search
        semantic_results = self.vector_manager.search_similar(query, k=k*2)
        all_results.extend(semantic_results)
        
        # 2. Nếu có legal reference, search specific
        if include_legal_refs:
            legal_refs = self._extract_legal_references(query)
            for ref in legal_refs:
                legal_results = self.vector_manager.search_by_legal_reference(ref, k=2)
                all_results.extend(legal_results)
        
        # 3. Topic-based boost
        for topic in detected_topics:
            topic_query = f"{query} {' '.join(self.topic_keywords[topic])}"
            topic_results = self.vector_manager.search_similar(topic_query, k=2)
            all_results.extend(topic_results)
        
        # Deduplicate và rank
        unique_results = self._deduplicate_and_rank(all_results)
        
        return unique_results[:k]
    
    def _detect_topics(self, query: str) -> List[str]:
        """Detect topics trong query"""
        query_lower = query.lower()
        detected = []
        
        for topic, keywords in self.topic_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                detected.append(topic)
        
        return detected
    
    def _extract_legal_references(self, query: str) -> List[str]:
        """Extract legal references từ query"""
        import re
        
        references = []
        
        # Patterns cho legal references
        patterns = [
            r'Điều\s+\d+[a-z]?\.?',
            r'Khoản\s+\d+[a-z]?\.?',
            r'Điểm\s+[a-z]+\)',
            r'Luật\s+[\w\s]+\s+số\s+\d+',
            r'Nghị định\s+số\s+\d+'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            references.extend(matches)
        
        return references
    
    def _deduplicate_and_rank(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate và rank kết quả"""
        # Group by document ID
        id_groups = {}
        for result in results:
            doc_id = result['id']
            if doc_id not in id_groups:
                id_groups[doc_id] = []
            id_groups[doc_id].append(result)
        
        # Get best score for each document
        unique_results = []
        for doc_id, group in id_groups.items():
            best_result = max(group, key=lambda x: x['score'])
            unique_results.append(best_result)
        
        # Sort by score
        unique_results.sort(key=lambda x: x['score'], reverse=True)
        
        return unique_results

# Test function
def test_vector_manager():
    """Test vector manager functionality"""
    from .lightweight_document_processor import LegalDocument
    
    # Create sample documents
    sample_docs = [
        LegalDocument(
            content="Điều 15. Người nước ngoài nhập cảnh Việt Nam phải có thị thực trừ trường hợp được miễn thị thực.",
            metadata={
                'source': 'test_law.txt',
                'doc_type': 'luat',
                'file_type': '.txt',
                'domain': 'xuatnhapcanh'
            }
        ),
        LegalDocument(
            content="Khoản 1. Thủ tục cấp hộ chiếu thực hiện tại Phòng Quản lý xuất nhập cảnh.",
            metadata={
                'source': 'test_procedure.txt',
                'doc_type': 'huongdan',
                'file_type': '.txt',
                'domain': 'xuatnhapcanh'
            }
        )
    ]
    
    print("🧪 Testing vector manager...")
    
    try:
        # Initialize
        vm = LightweightVectorManager()
        
        # Add documents
        success = vm.add_documents(sample_docs)
        print(f"✅ Add documents: {success}")
        
        # Search
        results = vm.search_similar("visa nhập cảnh", k=2)
        print(f"🔍 Search results: {len(results)}")
        
        # Stats
        stats = vm.get_collection_stats()
        print(f"📊 Collection stats: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

# if __name__ == "__main__":
#     test_vector_manager()