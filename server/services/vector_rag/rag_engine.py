# server/test/test_vector_rag.py
"""
Vector RAG System Test Suite - FIXED for optimized RAG system
"""

import asyncio
import sys
import os
import time
import json
from datetime import datetime
from typing import List, Dict, Any
import logging

# 🔥 CORRECT PATH setup
current_dir = os.path.dirname(__file__)
server_dir = os.path.dirname(current_dir)

# Add server directory to path
sys.path.insert(0, server_dir)

print(f"📁 Server dir: {server_dir}")
print(f"📁 Current dir: {current_dir}")

# Import RAG components - FIXED with better error handling
RAG_AVAILABLE = False
rag_import_error = None

try:
    print("🔍 Importing RAG Engine...")
    
    # Try different import paths
    try:
        from services.vector_rag.rag_engine import RAGEngine
        from services.vector_rag.rag_config import config
        print("✅ RAG imports successful (services.vector_rag)!")
        RAG_AVAILABLE = True
    except ImportError as e1:
        print(f"⚠️ services.vector_rag import failed: {e1}")
        
        # Try direct import from current working directory
        try:
            sys.path.insert(0, os.path.join(server_dir, 'services', 'vector_rag'))
            from rag_engine import RAGEngine
            from rag_config import config
            print("✅ RAG imports successful (direct)!")
            RAG_AVAILABLE = True
        except ImportError as e2:
            print(f"⚠️ Direct import failed: {e2}")
            rag_import_error = str(e2)
            
            # Last attempt - add all paths
            try:
                vector_rag_path = os.path.join(server_dir, 'services', 'vector_rag')
                if vector_rag_path not in sys.path:
                    sys.path.append(vector_rag_path)
                
                import rag_engine
                import rag_config
                RAGEngine = rag_engine.RAGEngine
                config = rag_config.config
                print("✅ RAG imports successful (module import)!")
                RAG_AVAILABLE = True
            except Exception as e3:
                print(f"❌ All import attempts failed. Last error: {e3}")
                rag_import_error = str(e3)
                
except Exception as e:
    print(f"❌ Unexpected import error: {e}")
    rag_import_error = str(e)

if not RAG_AVAILABLE:
    print(f"\n💡 Import troubleshooting:")
    print(f"   1. Check if files exist in: {os.path.join(server_dir, 'services', 'vector_rag')}")
    print(f"   2. Check Python path: {sys.path[:3]}...")
    print(f"   3. Last error: {rag_import_error}")
    
    # Check if files actually exist
    rag_dir = os.path.join(server_dir, 'services', 'vector_rag')
    if os.path.exists(rag_dir):
        files = os.listdir(rag_dir)
        python_files = [f for f in files if f.endswith('.py')]
        print(f"   📁 Vector RAG directory exists with files: {python_files}")
    else:
        print(f"   ❌ Vector RAG directory not found: {rag_dir}")

# Reduce logging noise
logging.basicConfig(level=logging.WARNING)

class RAGSystemTest:
    """RAG System Test Suite"""
    
    def __init__(self):
        self.rag_engine = None
        self.test_results = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'test_details': []
        }
    
    async def initialize_rag(self):
        """Initialize RAG system"""
        if not RAG_AVAILABLE:
            print("❌ RAG modules not available")
            return False
        
        print("🔧 Initializing RAG system...")
        
        try:
            # Create RAG engine instance
            self.rag_engine = RAGEngine()
            
            print("⏳ Initializing components (may take a moment)...")
            result = await asyncio.wait_for(
                self.rag_engine.initialize(force_rebuild=False), 
                timeout=120.0  # 2 minutes timeout
            )
            
            if result.get('success', False):
                print("✅ RAG system initialized successfully!")
                
                # Get stats
                stats = self.rag_engine.get_stats()
                print(f"📊 System Stats:")
                print(f"   Initialized: {stats.get('is_initialized', False)}")
                
                # Vector store stats
                vector_stats = stats.get('components', {}).get('vector_store', {})
                if vector_stats:
                    docs_count = vector_stats.get('total_documents', 0)
                    print(f"   Documents: {docs_count}")
                    print(f"   Model: {vector_stats.get('embedding_model', 'Unknown')}")
                
                # LLM providers
                llm_stats = stats.get('components', {}).get('llm_handler', {})
                if llm_stats:
                    providers = llm_stats.get('providers', {})
                    available_providers = [name for name, info in providers.items() if info.get('available', False)]
                    print(f"   LLM Providers: {available_providers}")
                
                return True
            else:
                print(f"❌ Initialization failed: {result.get('message', 'Unknown error')}")
                return False
                
        except asyncio.TimeoutError:
            print("❌ Initialization timeout (2 minutes)")
            return False
        except Exception as e:
            print(f"❌ Initialization error: {e}")
            return False
    
    def get_test_queries(self):
        """Get test queries for RAG system - UPDATED based on actual data"""
        return [
            # Basic passport queries
            {
                'query': 'Ai được cấp hộ chiếu phổ thông?',
                'category': 'basic',
                'expected_keywords': ['công dân việt nam', 'hộ chiếu', 'điều'],
                'description': 'Basic passport eligibility question'
            },
            {
                'query': 'Hồ sơ cấp hộ chiếu gồm những gì?',
                'category': 'procedure',
                'expected_keywords': ['hồ sơ', 'giấy tờ', 'chứng minh'],
                'description': 'Passport application documents'
            },
            {
                'query': 'Quy định về xuất cảnh của công dân Việt Nam',
                'category': 'legal',
                'expected_keywords': ['xuất cảnh', 'luật', 'quy định'],
                'description': 'Exit regulations for Vietnamese citizens'
            },
            {
                'query': 'Trình báo mất hộ chiếu phải làm sao?',
                'category': 'procedure',
                'expected_keywords': ['trình báo', 'mất', 'hộ chiếu'],
                'description': 'Lost passport procedure'
            },
            {
                'query': 'Điều kiện xuất cảnh của công dân Việt Nam',
                'category': 'legal',
                'expected_keywords': ['điều kiện', 'xuất cảnh', 'công dân'],
                'description': 'Exit conditions for Vietnamese citizens'
            },
            {
                'query': 'Các trường hợp bị tạm hoãn xuất cảnh',
                'category': 'legal',
                'expected_keywords': ['tạm hoãn', 'xuất cảnh', 'trường hợp'],
                'description': 'Exit suspension cases'
            },
            {
                'query': 'Làm hộ chiếu cho trẻ em dưới 14 tuổi như thế nào?',
                'category': 'complex',
                'expected_keywords': ['trẻ em', 'dưới 14 tuổi', 'hộ chiếu'],
                'description': 'Children passport procedures'
            },
            {
                'query': 'Điều 15 Luật xuất nhập cảnh',
                'category': 'legal_specific',
                'expected_keywords': ['điều 15', 'luật', 'xuất nhập cảnh'],
                'description': 'Specific legal article'
            },
            {
                'query': 'hộ chiếu',
                'category': 'short',
                'expected_keywords': ['hộ chiếu'],
                'description': 'Single keyword query'
            },
            {
                'query': 'Thủ tục cấp thị thực cho người nước ngoài',
                'category': 'visa',
                'expected_keywords': ['thị thực', 'người nước ngoài', 'cấp'],
                'description': 'Visa issuance procedures'
            },
            
            # Additional queries that should work with existing data
            {
                'query': 'Quy định về nhập cảnh',
                'category': 'legal',
                'expected_keywords': ['nhập cảnh', 'quy định'],
                'description': 'Entry regulations'
            },
            {
                'query': 'Công dân Việt Nam xuất cảnh',
                'category': 'basic',
                'expected_keywords': ['công dân việt nam', 'xuất cảnh'],
                'description': 'Vietnamese citizen exit'
            }
        ]
    
    async def run_single_test(self, test_case):
        """Run a single test case"""
        query = test_case['query']
        print(f"\n🧪 Testing: '{query}'")
        
        start_time = time.time()
        
        try:
            result = await self.rag_engine.query(query)
            response_time = time.time() - start_time
            
            # Analyze result
            success = result.get('success', False)
            answer = result.get('answer', '')
            metadata = result.get('metadata', {})
            
            print(f"⏱️ Response time: {response_time:.2f}s")
            
            if success and answer.strip():
                print(f"✅ Got answer ({len(answer)} chars)")
                print(f"📝 Preview: {answer[:150]}...")
                
                # Check for expected keywords
                answer_lower = answer.lower()
                expected_keywords = test_case.get('expected_keywords', [])
                matched_keywords = []
                
                for kw in expected_keywords:
                    if kw.lower() in answer_lower:
                        matched_keywords.append(kw)
                
                # Test passes if at least 1 keyword matches
                keyword_match = len(matched_keywords) >= 1 if expected_keywords else True
                
                if keyword_match:
                    print(f"🎯 Keywords matched: {matched_keywords}")
                    test_passed = True
                else:
                    print(f"❌ No keywords matched from: {expected_keywords}")
                    test_passed = False
                
                # Show metadata
                if metadata:
                    context_sources = metadata.get('context_sources', 0)
                    context_type = metadata.get('context_type', 'unknown')
                    query_intent = metadata.get('query_intent', 'unknown')
                    print(f"📊 Sources: {context_sources}, Type: {context_type}, Intent: {query_intent}")
                    
            else:
                print(f"❌ No answer or failed")
                if result.get('error'):
                    print(f"Error: {result['error']}")
                if result.get('reason'):
                    print(f"Reason: {result['reason']}")
                test_passed = False
            
            # Save test result
            test_result = {
                'query': query,
                'category': test_case['category'],
                'description': test_case['description'],
                'success': success,
                'test_passed': test_passed,
                'response_time': round(response_time, 3),
                'answer_length': len(answer) if answer else 0,
                'answer_preview': answer[:200] if answer else '',
                'matched_keywords': matched_keywords if 'matched_keywords' in locals() else [],
                'metadata': metadata,
                'error': result.get('error', '') if not success else ''
            }
            
            self.test_results['test_details'].append(test_result)
            self.test_results['total_tests'] += 1
            
            if test_passed:
                self.test_results['passed_tests'] += 1
            else:
                self.test_results['failed_tests'] += 1
            
            return test_result
            
        except Exception as e:
            response_time = time.time() - start_time
            print(f"❌ Test exception: {e}")
            
            test_result = {
                'query': query,
                'category': test_case['category'],
                'description': test_case['description'],
                'success': False,
                'test_passed': False,
                'response_time': round(response_time, 3),
                'error': str(e),
                'exception': True
            }
            
            self.test_results['test_details'].append(test_result)
            self.test_results['total_tests'] += 1
            self.test_results['failed_tests'] += 1
            
            return test_result
    
    async def run_all_tests(self):
        """Run all test cases"""
        print("🚀 STARTING RAG SYSTEM TEST SUITE")
        print("=" * 60)
        
        test_cases = self.get_test_queries()
        print(f"📊 Running {len(test_cases)} test cases...")
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n[{i}/{len(test_cases)}] Category: {test_case['category']}")
            await self.run_single_test(test_case)
            
            # Small delay between tests
            await asyncio.sleep(1.0)
        
        self.generate_report()
    
    def generate_report(self):
        """Generate comprehensive test report"""
        results = self.test_results
        
        print("\n" + "=" * 60)
        print("📋 RAG SYSTEM TEST REPORT")
        print("=" * 60)
        
        # Overall stats
        total = results['total_tests']
        passed = results['passed_tests']
        failed = results['failed_tests']
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"📊 OVERALL RESULTS:")
        print(f"   Total Tests: {total}")
        print(f"   Passed: {passed} ✅")
        print(f"   Failed: {failed} ❌")
        print(f"   Success Rate: {success_rate:.1f}%")
        
        # Performance stats
        response_times = [t['response_time'] for t in results['test_details'] if 'response_time' in t]
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            min_time = min(response_times)
            max_time = max(response_times)
            
            print(f"\n⚡ PERFORMANCE:")
            print(f"   Average Response Time: {avg_time:.2f}s")
            print(f"   Fastest: {min_time:.2f}s")
            print(f"   Slowest: {max_time:.2f}s")
        
        # Category breakdown
        categories = {}
        for test in results['test_details']:
            cat = test['category']
            if cat not in categories:
                categories[cat] = {'total': 0, 'passed': 0}
            categories[cat]['total'] += 1
            if test['test_passed']:
                categories[cat]['passed'] += 1
        
        print(f"\n📈 BY CATEGORY:")
        for cat, stats in categories.items():
            cat_rate = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
            print(f"   {cat.capitalize()}: {stats['passed']}/{stats['total']} ({cat_rate:.1f}%)")
        
        # Failed tests details
        failed_tests = [t for t in results['test_details'] if not t['test_passed']]
        if failed_tests:
            print(f"\n❌ FAILED TESTS:")
            for test in failed_tests:
                error_msg = test.get('error', 'No answer/keywords')
                print(f"   • {test['query'][:50]}... - {error_msg}")
        
        # Successful tests performance
        successful_tests = [t for t in results['test_details'] if t['test_passed']]
        if successful_tests:
            successful_tests.sort(key=lambda x: x['response_time'])
            print(f"\n🏆 FASTEST SUCCESSFUL TESTS:")
            for test in successful_tests[:3]:
                print(f"   • {test['query'][:40]}... - {test['response_time']:.2f}s")
        
        print(f"\n📅 Test completed at: {results['timestamp']}")
        
        return results
    
    def save_results(self, filename=None):
        """Save test results to JSON file"""
        if filename is None:
            filename = f"rag_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Save in test directory
        filepath = os.path.join(current_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.test_results, f, ensure_ascii=False, indent=2)
            
            print(f"💾 Results saved to: {filepath}")
        except Exception as e:
            print(f"❌ Failed to save results: {e}")

async def quick_test():
    """Quick smoke test with 3 essential queries"""
    print("🔥 QUICK RAG SYSTEM TEST")
    print("=" * 50)
    
    test = RAGSystemTest()
    
    if not await test.initialize_rag():
        print("❌ Failed to initialize RAG system")
        return
    
    # Essential quick test queries
    quick_queries = [
        {
            'query': 'Hồ sơ cấp hộ chiếu gồm những gì?',
            'expected': ['tờ khai', 'ảnh', 'chứng minh']
        },
        {
            'query': 'Thời gian cấp hộ chiếu',
            'expected': ['8 ngày', 'ngày làm việc']
        },
        {
            'query': 'Lệ phí làm hộ chiếu',
            'expected': ['160', 'đồng']
        }
    ]
    
    passed = 0
    total = len(quick_queries)
    
    for i, test_case in enumerate(quick_queries, 1):
        print(f"\n[{i}/{total}] Testing: {test_case['query']}")
        
        try:
            start_time = time.time()
            result = await test.rag_engine.query(test_case['query'])
            response_time = time.time() - start_time
            
            if result.get('success') and result.get('answer'):
                answer = result['answer']
                # Check for expected keywords
                matched = any(exp.lower() in answer.lower() for exp in test_case['expected'])
                
                if matched:
                    print(f"✅ Success ({response_time:.2f}s)")
                    passed += 1
                else:
                    print(f"⚠️ Answer found but no expected keywords ({response_time:.2f}s)")
                
                answer_preview = answer[:150] + "..." if len(answer) > 150 else answer
                print(f"📝 Answer: {answer_preview}")
            else:
                print(f"❌ Failed ({response_time:.2f}s)")
                print(f"Error: {result.get('error', 'No answer')}")
                
        except Exception as e:
            print(f"❌ Exception: {e}")
    
    success_rate = (passed / total * 100) if total > 0 else 0
    print(f"\n🏁 Quick test completed: {passed}/{total} passed ({success_rate:.1f}%)")

async def system_health_check():
    """Check RAG system health"""
    print("🏥 RAG SYSTEM HEALTH CHECK")
    print("=" * 50)
    
    if not RAG_AVAILABLE:
        print("❌ RAG modules not available")
        return
    
    try:
        rag_engine = RAGEngine()
        
        # Test initialization
        print("🔧 Testing initialization...")
        result = await asyncio.wait_for(
            rag_engine.initialize(force_rebuild=False),
            timeout=60.0
        )
        
        if result.get('success'):
            print("✅ Initialization successful")
            
            # Get system stats
            health = rag_engine.health_check()
            print(f"\n🏥 System Health: {health.get('system_status', 'unknown')}")
            
            components = health.get('components', {})
            for name, status in components.items():
                component_status = status.get('status', 'unknown')
                print(f"   {name}: {component_status}")
                
                if name == 'vector_store' and 'documents' in status:
                    print(f"     Documents: {status['documents']}")
                elif name == 'llm' and 'available_providers' in status:
                    print(f"     Providers: {status['available_providers']}")
            
            issues = health.get('issues', [])
            if issues:
                print(f"\n⚠️ Issues found:")
                for issue in issues:
                    print(f"   • {issue}")
            else:
                print(f"\n✅ No issues found")
                
        else:
            print(f"❌ Initialization failed: {result.get('message')}")
            
    except Exception as e:
        print(f"❌ Health check failed: {e}")

async def main():
    """Main test function"""
    if not RAG_AVAILABLE:
        print("❌ RAG system not available. Please check the setup.")
        print("💡 Make sure you're running from the server directory")
        return
    
    print("🎯 RAG System Test Options:")
    print("1. Quick test (3 queries)")
    print("2. Full test suite (10 queries)")
    print("3. System health check")
    
    try:
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice == "1":
            await quick_test()
        elif choice == "2":
            test = RAGSystemTest()
            
            if await test.initialize_rag():
                await test.run_all_tests()
                test.save_results()
            else:
                print("❌ Failed to initialize RAG system")
        elif choice == "3":
            await system_health_check()
        else:
            print("❌ Invalid choice")
                
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test error: {e}")

if __name__ == "__main__":
    asyncio.run(main())