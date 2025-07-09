# debug_rag_search.py - FIXED TEST đến bước Context
"""
RAG System Test - Test 4 bước chính của hệ thống
🔍 STEP 1: Query Classification
🔍 STEP 2: Vector Search  
🔍 STEP 3: ReRanking
🔍 STEP 4: Context Optimization
📄 OUTPUT: Detailed log file để debug
"""
import sys
import os
import time
import asyncio
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from services.vector_rag.query_classifier import VietnameseQueryClassifier
from services.vector_rag.vector_store import VectorStore
from services.vector_rag.reranker import ReRanker
from services.vector_rag.context_optimizer import ContextOptimizer

# FOCUSED TEST QUERIES - test cases quan trọng
TEST_QUERIES = [
    "Tôi bị khởi tố thì có xuất cảnh được không",
    "Con tôi 12 tuổi làm hộ chiếu thế nào", 
    "Điều 33 quy định gì về điều kiện xuất cảnh",
    "Khoản 2 Điều 15 nói về vấn đề gì",
    "Làm hộ chiếu cần những giấy tờ gì",
]

class RAGSystemTester:
    """Test 4 bước chính của RAG system"""
    
    def __init__(self):
        # Initialize các modules
        self.query_classifier = VietnameseQueryClassifier()
        self.vector_store = VectorStore()
        self.reranker = ReRanker()
        self.context_optimizer = ContextOptimizer()
        
        # Setup log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = f"rag_system_test_{timestamp}.log"
        
        # Tracking issues
        self.step_issues = {
            'classification': [],
            'search': [],
            'rerank': [],
            'context': []
        }
        
        self.performance_data = []
        
        print(f"🔧 RAG System Tester initialized")
        print(f"📄 Log file: {self.log_file}")
    
    def log(self, message):
        """Write to both console and log file"""
        print(message)
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(message + '\n')
    
    async def init_check(self):
        """Initialize and check system"""
        self.log("\n🔧 SYSTEM INITIALIZATION CHECK")
        self.log("=" * 60)
        
        try:
            # Check vector store
            vector_init = await self.vector_store.initialize()
            if vector_init.get('success'):
                health = self.vector_store.get_health_status()
                docs = health.get('searcher_stats', {}).get('documents_loaded', 0)
                vectors = health.get('searcher_stats', {}).get('faiss_vectors', 0)
                
                self.log(f"✅ Vector store ready:")
                self.log(f"   📄 Documents: {docs}")
                self.log(f"   🔢 FAISS vectors: {vectors}")
                
                if docs == 0:
                    self.log(f"❌ No documents found - check vector database")
                    return False
                    
                return True
            else:
                self.log(f"❌ Vector store failed: {vector_init.get('message')}")
                return False
                
        except Exception as e:
            self.log(f"❌ Init failed: {e}")
            return False
    
    async def test_single_query(self, query, query_num):
        """Test single query through 4 steps"""
        self.log(f"\n{'='*80}")
        self.log(f"🔍 QUERY {query_num}: {query}")
        self.log(f"{'='*80}")
        
        query_start_time = time.time()
        step_times = {}
        step_results = {}
        
        # === STEP 1: QUERY CLASSIFICATION ===
        self.log(f"\n📊 STEP 1: QUERY CLASSIFICATION")
        self.log("-" * 50)
        
        start_time = time.time()
        try:
            query_features = self.query_classifier.classify(query)
            step_times['classification'] = time.time() - start_time
            
            self.log(f"⏱️ Time: {step_times['classification']:.3f}s")
            self.log(f"📤 CLASSIFICATION RESULTS:")
            self.log(f"   🎯 primary_intent: {query_features.primary_intent}")
            self.log(f"   👤 subject_type: {query_features.subject_type}")
            self.log(f"   📊 confidence: {query_features.confidence:.3f}")
            self.log(f"   ❓ needs_conclusion: {getattr(query_features, 'needs_conclusion', 'NOT_SET')}")
            self.log(f"   🔗 has_direct_article: {query_features.has_direct_article}")
            self.log(f"   🔞 age_constraint: {query_features.age_constraint}")
            self.log(f"   ⚖️ legal_status: {query_features.legal_status}")
            self.log(f"   🏷️ enhanced_keywords: {query_features.enhanced_keywords}")
            self.log(f"   🎯 focus_keywords: {query_features.focus_keywords}")
            
            # Validate classification
            classification_issues = self._validate_classification(query, query_features)
            if classification_issues:
                self.log(f"⚠️ CLASSIFICATION ISSUES:")
                for issue in classification_issues:
                    self.log(f"   • {issue}")
                self.step_issues['classification'].extend([f"Q{query_num}: {issue}" for issue in classification_issues])
            else:
                self.log(f"✅ Classification looks correct")
            
            step_results['query_features'] = query_features
            
        except Exception as e:
            error_msg = f"Classification failed: {e}"
            self.log(f"❌ {error_msg}")
            self.step_issues['classification'].append(f"Q{query_num}: {error_msg}")
            return
        
        # === STEP 2: VECTOR SEARCH ===
        self.log(f"\n🔍 STEP 2: VECTOR SEARCH")
        self.log("-" * 50)
        
        start_time = time.time()
        try:
            search_results = await self.vector_store.search(query, query_features, k=8)
            step_times['search'] = time.time() - start_time
            
            self.log(f"⏱️ Time: {step_times['search']:.3f}s")
            self.log(f"📤 SEARCH RESULTS: {len(search_results)} documents")
            
            # Show top results with quality analysis
            for i, result in enumerate(search_results[:3]):
                score = result.get('score', 0)
                source = result.get('source', 'unknown')
                content = result.get('content', '')
                metadata = result.get('metadata', {})
                
                content_preview = content.replace('\n', ' ').strip()[:100] + "..."
                
                self.log(f"   🏆 #{i+1} Score: {score:.3f} | Source: {source}")
                self.log(f"      📄 \"{content_preview}\"")
                self.log(f"      📋 Doc: {metadata.get('doc', 'N/A')} | Type: {metadata.get('type', 'N/A')}")
                
                # Quick relevance check
                relevance = self._quick_relevance_check(query, content)
                self.log(f"      🎯 Relevance: {relevance}/5")
            
            # Validate search
            search_issues = self._validate_search(query, query_features, search_results)
            if search_issues:
                self.log(f"⚠️ SEARCH ISSUES:")
                for issue in search_issues:
                    self.log(f"   • {issue}")
                self.step_issues['search'].extend([f"Q{query_num}: {issue}" for issue in search_issues])
            else:
                self.log(f"✅ Search results look relevant")
            
            step_results['search_results'] = search_results
            
        except Exception as e:
            error_msg = f"Search failed: {e}"
            self.log(f"❌ {error_msg}")
            self.step_issues['search'].append(f"Q{query_num}: {error_msg}")
            return
        
        # === STEP 3: RERANKING ===
        self.log(f"\n🎯 STEP 3: RERANKING")
        self.log("-" * 50)
        
        start_time = time.time()
        try:
            reranked_results = self.reranker.rerank(
                query=query,
                chunks=search_results,
                context_tier='general',
                query_features=query_features
            )
            step_times['rerank'] = time.time() - start_time
            
            self.log(f"⏱️ Time: {step_times['rerank']:.3f}s")
            self.log(f"📤 RERANKED RESULTS: {len(reranked_results)} documents")
            
            # Show top reranked results
            for i, result in enumerate(reranked_results[:3]):
                precision = result.get('precision_score', 0)
                is_primary = result.get('is_primary_answer', False)
                content = result.get('content', '')
                
                content_preview = content.replace('\n', ' ').strip()[:80] + "..."
                primary_flag = "🎯 PRIMARY" if is_primary else ""
                
                self.log(f"   🏆 #{i+1} Precision: {precision:.3f} {primary_flag}")
                self.log(f"      📄 \"{content_preview}\"")
                
                # Show accuracy analysis if available
                if 'accuracy_analysis' in result:
                    analysis = result['accuracy_analysis']
                    self.log(f"      📊 Intent: {analysis['intent_match']:.2f} | Structure: {analysis['structure_match']:.2f} | Content: {analysis['content_relevance']:.2f}")
            
            # Validate reranking
            rerank_issues = self._validate_reranking(query, query_features, reranked_results)
            if rerank_issues:
                self.log(f"⚠️ RERANKING ISSUES:")
                for issue in rerank_issues:
                    self.log(f"   • {issue}")
                self.step_issues['rerank'].extend([f"Q{query_num}: {issue}" for issue in rerank_issues])
            else:
                self.log(f"✅ Reranking improved result quality")
            
            step_results['reranked_results'] = reranked_results
            
        except Exception as e:
            error_msg = f"Reranking failed: {e}"
            self.log(f"❌ {error_msg}")
            self.step_issues['rerank'].append(f"Q{query_num}: {error_msg}")
            return
        
        # === STEP 4: CONTEXT OPTIMIZATION ===
        self.log(f"\n🎨 STEP 4: CONTEXT OPTIMIZATION")
        self.log("-" * 50)
        
        start_time = time.time()
        try:
            context_result = await self.context_optimizer.optimize_context(
                reranked_results, 
                query_features
            )
            step_times['context'] = time.time() - start_time
            
            self.log(f"⏱️ Time: {step_times['context']:.3f}s")
            self.log(f"📤 CONTEXT OPTIMIZATION:")
            self.log(f"   📋 Query: {context_result.query}")
            self.log(f"   📄 Primary content length: {len(context_result.primary_content)} chars")
            self.log(f"   📜 Primary citation: {context_result.primary_citation}")
            self.log(f"   🎯 Answer type: {context_result.answer_type}")
            self.log(f"   ⚠️ Exception detected: {context_result.exception_detected}")
            self.log(f"   🔚 Needs conclusion: {context_result.needs_conclusion}")
            self.log(f"   📚 Supporting contents: {len(context_result.supporting_contents)}")
            
            # Show primary content preview
            if context_result.primary_content:
                preview = context_result.primary_content[:200] + "..." if len(context_result.primary_content) > 200 else context_result.primary_content
                self.log(f"   📖 Primary content preview:")
                self.log(f"      \"{preview}\"")
            
            # Validate context optimization
            context_issues = self._validate_context(query, query_features, context_result)
            if context_issues:
                self.log(f"⚠️ CONTEXT ISSUES:")
                for issue in context_issues:
                    self.log(f"   • {issue}")
                self.step_issues['context'].extend([f"Q{query_num}: {issue}" for issue in context_issues])
            else:
                self.log(f"✅ Context optimization successful")
            
            step_results['context_result'] = context_result
            
        except Exception as e:
            error_msg = f"Context optimization failed: {e}"
            self.log(f"❌ {error_msg}")
            self.step_issues['context'].append(f"Q{query_num}: {error_msg}")
            return
        
        # === QUERY SUMMARY ===
        total_time = time.time() - query_start_time
        
        self.log(f"\n⏱️ QUERY {query_num} SUMMARY")
        self.log("-" * 30)
        self.log(f"   Classification: {step_times.get('classification', 0):.3f}s")
        self.log(f"   Search: {step_times.get('search', 0):.3f}s") 
        self.log(f"   Rerank: {step_times.get('rerank', 0):.3f}s")
        self.log(f"   Context: {step_times.get('context', 0):.3f}s")
        self.log(f"   Total: {total_time:.3f}s")
        
        # Results summary
        search_count = len(step_results.get('search_results', []))
        rerank_count = len(step_results.get('reranked_results', []))
        has_primary = any(r.get('is_primary_answer', False) for r in step_results.get('reranked_results', []))
        has_citation = bool(step_results.get('context_result', {}).primary_citation)
        
        self.log(f"   Search: {search_count} → Rerank: {rerank_count}")
        self.log(f"   Primary answer: {'Yes' if has_primary else 'No'}")
        self.log(f"   Citation extracted: {'Yes' if has_citation else 'No'}")
        
        # Store performance data
        self.performance_data.append({
            'query_num': query_num,
            'query': query,
            'total_time': total_time,
            'step_times': step_times,
            'search_count': search_count,
            'rerank_count': rerank_count,
            'has_primary': has_primary,
            'has_citation': has_citation,
            'intent': query_features.primary_intent if 'query_features' in step_results else 'unknown'
        })
    
    def _validate_classification(self, query, features):
        """Validate query classification"""
        issues = []
        query_lower = query.lower()
        
        # Check legal constraint detection
        if "khởi tố" in query_lower and not features.legal_status:
            issues.append("Legal status (khởi tố) not detected")
        
        # Check direct article detection
        if "điều" in query_lower and any(char.isdigit() for char in query):
            if not features.has_direct_article:
                issues.append("Direct article reference not detected")
        
        # Check age constraint
        if any(word in query_lower for word in ["12 tuổi", "trẻ em", "dưới 14"]):
            if not features.age_constraint:
                issues.append("Age constraint not detected")
        
        # Check conclusion need
        if "có" in query_lower and "được" in query_lower and "không" in query_lower:
            if not getattr(features, 'needs_conclusion', False):
                issues.append("Should need conclusion for yes/no question")
        
        return issues
    
    def _validate_search(self, query, features, results):
        """Validate search results"""
        issues = []
        
        if not results:
            issues.append("No search results returned")
            return issues
        
        # Check relevance
        query_lower = query.lower()
        key_terms = self._extract_key_terms(query_lower)
        relevant_count = 0
        
        for result in results:
            content_lower = result.get('content', '').lower()
            if any(term in content_lower for term in key_terms):
                relevant_count += 1
        
        relevance_rate = relevant_count / len(results) if results else 0
        if relevance_rate < 0.4:
            issues.append(f"Low relevance rate: {relevance_rate:.1%}")
        
        # Check scores
        low_score_count = sum(1 for r in results if r.get('score', 0) < 0.1)
        if low_score_count > len(results) // 2:
            issues.append(f"Many low scores: {low_score_count}/{len(results)}")
        
        return issues
    
    def _validate_reranking(self, query, features, results):
        """Validate reranking results"""
        issues = []
        
        if not results:
            issues.append("No reranked results")
            return issues
        
        # Check if primary answer found for appropriate queries
        if getattr(features, 'needs_conclusion', False):
            has_primary = any(r.get('is_primary_answer', False) for r in results)
            if not has_primary:
                issues.append("No primary answer for conclusion-needed query")
        
        # Check precision scores
        precision_scores = [r.get('precision_score', 0) for r in results]
        avg_precision = sum(precision_scores) / len(precision_scores) if precision_scores else 0
        
        if avg_precision < 0.3:
            issues.append(f"Low average precision: {avg_precision:.3f}")
        
        # Check if reranking improved order
        if len(results) >= 2:
            first_precision = results[0].get('precision_score', 0)
            second_precision = results[1].get('precision_score', 0)
            if first_precision < second_precision * 0.9:  # Allow some tolerance
                issues.append("Top result may not be best")
        
        return issues
    
    def _validate_context(self, query, features, context_result):
        """Validate context optimization"""
        issues = []
        
        # Check if primary content exists
        if not context_result.primary_content:
            issues.append("No primary content generated")
            return issues
        
        # Check citation extraction
        if not context_result.primary_citation:
            # Only issue if content seems to have legal structure
            if "điều" in context_result.primary_content.lower():
                issues.append("Legal citation not extracted from content with articles")
        
        # Check conclusion detection
        if getattr(features, 'needs_conclusion', False):
            if not context_result.needs_conclusion:
                issues.append("Context should detect need for conclusion")
        
        # Check answer type matching
        intent = getattr(features, 'primary_intent', '')
        if intent == 'PROCEDURE' and context_result.answer_type != 'procedure':
            issues.append("Answer type doesn't match query intent")
        
        return issues
    
    def _extract_key_terms(self, query_lower):
        """Extract key terms for relevance checking"""
        terms = []
        if "hộ chiếu" in query_lower:
            terms.append("hộ chiếu")
        if "xuất cảnh" in query_lower:
            terms.append("xuất cảnh")
        if "khởi tố" in query_lower:
            terms.append("khởi tố")
        if "điều" in query_lower:
            terms.append("điều")
        if "thủ tục" in query_lower:
            terms.append("thủ tục")
        return terms
    
    def _quick_relevance_check(self, query, content):
        """Quick relevance score 1-5"""
        query_lower = query.lower()
        content_lower = content.lower()
        score = 0
        
        # Key term matches
        key_matches = [
            ("hộ chiếu", "hộ chiếu"),
            ("xuất cảnh", "xuất cảnh"), 
            ("khởi tố", "khởi tố"),
            ("trẻ em", "trẻ em"),
            ("điều", "điều"),
            ("thủ tục", "thủ tục")
        ]
        
        for q_term, c_term in key_matches:
            if q_term in query_lower and c_term in content_lower:
                score += 1
        
        return min(5, score)
    
    async def run_test(self):
        """Run complete test suite"""
        self.log(f"🚀 RAG SYSTEM TEST - 4 STEP PIPELINE")
        self.log(f"Testing {len(TEST_QUERIES)} queries through full pipeline")
        self.log(f"Timestamp: {datetime.now()}")
        self.log("="*70)
        
        # Test each query
        for i, query in enumerate(TEST_QUERIES, 1):
            await self.test_single_query(query, i)
            print(f"Progress: {i}/{len(TEST_QUERIES)} completed", end='\r')
        
        # === FINAL SUMMARY ===
        self.log(f"\n{'='*80}")
        self.log(f"🎯 FINAL TEST SUMMARY")
        self.log("="*80)
        
        # Performance summary
        if self.performance_data:
            total_queries = len(self.performance_data)
            avg_total_time = sum(d['total_time'] for d in self.performance_data) / total_queries
            avg_search_count = sum(d['search_count'] for d in self.performance_data) / total_queries
            primary_found_rate = sum(1 for d in self.performance_data if d['has_primary']) / total_queries
            citation_rate = sum(1 for d in self.performance_data if d['has_citation']) / total_queries
            
            self.log(f"\n⏱️ PERFORMANCE:")
            self.log(f"   Average total time: {avg_total_time:.3f}s")
            self.log(f"   Average search results: {avg_search_count:.1f}")
            self.log(f"   Primary answer found: {primary_found_rate:.1%}")
            self.log(f"   Citation extracted: {citation_rate:.1%}")
        
        # Issue summary
        total_issues = sum(len(issues) for issues in self.step_issues.values())
        self.log(f"\n🔍 ISSUES FOUND: {total_issues}")
        
        for step, issues in self.step_issues.items():
            if issues:
                self.log(f"\n📊 {step.upper()} ISSUES ({len(issues)}):")
                for issue in issues:
                    self.log(f"   • {issue}")
        
        # Recommendations
        self.log(f"\n💡 RECOMMENDATIONS:")
        recommendations = self._generate_recommendations()
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                self.log(f"   {i}. {rec}")
        else:
            self.log(f"   ✅ System working well - no major issues!")
        
        # Final quality assessment
        self.log(f"\n📊 SYSTEM QUALITY ASSESSMENT:")
        quality_score = self._calculate_quality_score()
        self.log(f"   Overall quality: {quality_score}/10")
        self.log(f"   Status: {'Excellent' if quality_score >= 8 else 'Good' if quality_score >= 6 else 'Needs improvement'}")
        
        self.log(f"\n🎉 TEST COMPLETED!")
        self.log(f"📄 Full results saved to: {self.log_file}")
        
        print(f"\n✅ RAG System test completed! Check log: {self.log_file}")
    
    def _generate_recommendations(self):
        """Generate recommendations based on issues"""
        recommendations = []
        
        # Classification issues
        if self.step_issues['classification']:
            recommendations.append("Improve query classification patterns")
        
        # Search issues  
        if self.step_issues['search']:
            recommendations.append("Adjust search thresholds or improve embeddings")
        
        # Rerank issues
        if self.step_issues['rerank']:
            recommendations.append("Fine-tune reranking accuracy metrics")
        
        # Context issues
        if self.step_issues['context']:
            recommendations.append("Enhance context optimization and citation extraction")
        
        return recommendations
    
    def _calculate_quality_score(self):
        """Calculate overall quality score 1-10"""
        total_issues = sum(len(issues) for issues in self.step_issues.values())
        total_possible_issues = len(TEST_QUERIES) * 4  # 4 steps per query
        
        # Performance factors
        if self.performance_data:
            primary_rate = sum(1 for d in self.performance_data if d['has_primary']) / len(self.performance_data)
            citation_rate = sum(1 for d in self.performance_data if d['has_citation']) / len(self.performance_data)
            avg_time = sum(d['total_time'] for d in self.performance_data) / len(self.performance_data)
            
            # Base score from issue rate
            issue_rate = total_issues / total_possible_issues
            base_score = (1 - issue_rate) * 6  # Max 6 points from low issues
            
            # Bonus points for performance
            performance_bonus = (primary_rate + citation_rate) * 2  # Max 4 points
            
            # Time penalty
            time_penalty = max(0, (avg_time - 1.0) * 0.5)  # Penalty if > 1s
            
            final_score = min(10, max(1, base_score + performance_bonus - time_penalty))
            return round(final_score, 1)
        
        return 5.0  # Default if no performance data

async def main():
    """Main function"""
    print("🔬 RAG SYSTEM TEST - 4 Step Pipeline")
    print("📄 Query → Classification → Search → Rerank → Context")
    
    tester = RAGSystemTester()
    
    try:
        # Initialize
        init_ok = await tester.init_check()
        if not init_ok:
            print("❌ Initialization failed")
            return
        
        # Run test
        await tester.run_test()
        
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())