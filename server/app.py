from flask import Flask
from web_server.routes import chatbot, navigation  # Thêm navigation
from web_server.middleware import setup_middleware

app = Flask(__name__)
setup_middleware(app)

app.register_blueprint(chatbot.bp)
app.register_blueprint(navigation.bp)  # Thêm dòng này

if __name__ == '__main__':
    app.run(debug=True)
