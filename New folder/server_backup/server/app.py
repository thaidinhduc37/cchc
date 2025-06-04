from flask import Flask
from flask_cors import CORS  # ✅ THÊM DÒNG NÀY
from routes.chat_routes import chat_routes
from routes.assistant_routes import assistant_routes

app = Flask(__name__)
CORS(app)  # ✅ Cho phép frontend gọi từ http://localhost:3000

app.register_blueprint(chat_routes)
app.register_blueprint(assistant_routes)

@app.route("/", methods=["GET"])
def health_check():
    return {"status": "OK", "message": "DVC Assistant Server is running."}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
