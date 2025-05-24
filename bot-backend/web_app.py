from flask import Flask
from bot_handler import bot_bp

app = Flask(__name__)
app.register_blueprint(bot_bp, url_prefix="/bot")

@app.route("/")
def home():
    return "Hi I'm COGNISENSE - Your AI Personal Assistant"

if __name__ == "__main__":
    app.run(debug=True)
