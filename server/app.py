from flask import Flask
from flask_cors import CORS
from app.api.chat_routes import chat_routes

app = Flask(__name__, static_folder=None)
CORS(app)

app.register_blueprint(chat_routes)


@app.route("/", methods=["GET"])
def health_check():
    return {"status": "OK", "message": "DVC Assistant Server is running."}

# ===== SỬA LOGIC: AUTO-INITIALIZE VECTOR RAG ON STARTUP =====
try:
    # SỬA: Import đúng class thay vì function
    from app.services.vector_rag.rag_engine import RAGEngine
    VECTOR_RAG_AVAILABLE = True
    print("✅ Vector RAG class loaded successfully")
    
    # SỬA: AUTO-INITIALIZE RAG với class
    print("🚀 Auto-initializing Vector RAG on server startup...")
    
    from app.services.unified_processor import initialize_rag_engine
    import asyncio
    import threading
    
    def init_rag_sync():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # SỬA: Sử dụng function có sẵn
            result = loop.run_until_complete(initialize_rag_engine())
            if result:
                print("✅ Vector RAG auto-initialized successfully on startup!")
            else:
                print("❌ Vector RAG auto-initialization failed")
        except Exception as e:
            print(f"❌ RAG startup error: {e}")
        finally:
            loop.close()
    
    # Khởi tạo trong thread riêng để không block server
    rag_thread = threading.Thread(target=init_rag_sync, daemon=True)
    rag_thread.start()
    
except ImportError as e:
    VECTOR_RAG_AVAILABLE = False
    print(f"⚠️ Vector RAG not available: {e}")
except Exception as e:
    print(f"❌ RAG startup setup error: {e}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)