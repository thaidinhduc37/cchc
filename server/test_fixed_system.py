# server/test_fixed_system.py
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    try:
        print("🧪 Testing fixed imports...")
        
        # Test as modules
        from services.vector_rag import lightweight_config
        print("✅ Config imported")
        
        from services.vector_rag import lightweight_embeddings
        print("✅ Embeddings imported")
        
        from services.vector_rag import lightweight_document_processor
        print("✅ Document processor imported")
        
        from services.vector_rag import lightweight_vector_manager
        print("✅ Vector manager imported")
        
        from services.vector_rag import lightweight_llm_handler
        print("✅ LLM handler imported")
        
        from services.vector_rag import lightweight_rag_engine
        print("✅ RAG engine imported")
        
        print("\n🎉 ALL IMPORTS SUCCESSFUL!")
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_imports()
    if success:
        print("\n✅ System ready! Now run:")
        print("python -m services.vector_rag.build_vector --build")