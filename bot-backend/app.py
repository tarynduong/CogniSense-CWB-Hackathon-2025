from flask import Flask
from bot_handler import bot_bp

app = Flask(__name__)
app.register_blueprint(bot_bp, url_prefix="/cognisense")

@app.route("/")
def home():
    return "Welcome to Product Management API"

if __name__ == "__main__":
    app.run(debug=True)
