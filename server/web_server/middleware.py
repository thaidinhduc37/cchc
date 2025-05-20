def setup_middleware(app):
    from flask_cors import CORS
    CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:3000"])