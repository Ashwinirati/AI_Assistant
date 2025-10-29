from flask import Flask, request, render_template, redirect
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
import requests

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite://assistant.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Models
class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(10))  # 'user' or 'assistant'
    content = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=db.func.now())

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prompt = db.Column(db.Text)
    was_helpful = db.Column(db.String(5))  # 'yes' or 'no'
    timestamp = db.Column(db.DateTime, default=db.func.now())

# RapidAPI setup
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST")
RAPIDAPI_URL = f"https://{RAPIDAPI_HOST}/chat"

def get_response(prompt):
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}]
    }
    headers = {
        "content-type": "application/json",
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }
    try:
        response = requests.post(RAPIDAPI_URL, json=payload, headers=headers)
        result = response.json()
        if "choices" in result:
            return result["choices"][0]["message"]["content"]
        elif "message" in result:
            return f"API Error: {result['message']}"
        elif "error" in result:
            return f"API Error: {result['error']}"
        else:
            return f"Unexpected response format: {result}"
    except Exception as e:
        return f"Request failed: {str(e)}"

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        user_input = request.form['user_input']
        function = request.form['function']

        if function == "summarize":
            prompt = f"Summarize this: {user_input}"
        elif function == "creative":
            prompt = user_input
        else:
            prompt = user_input

        response = get_response(prompt)

        db.session.add(ChatMessage(role="user", content=user_input))
        db.session.add(ChatMessage(role="assistant", content=response))
        db.session.commit()

    messages = ChatMessage.query.order_by(ChatMessage.timestamp).all()
    return render_template('index.html', chat_history=messages)

@app.route('/feedback', methods=['POST'])
def feedback():
    feedback_value = request.form['feedback']
    last_user = ChatMessage.query.filter_by(role="user").order_by(ChatMessage.timestamp.desc()).first()
    if last_user:
        db.session.add(Feedback(prompt=last_user.content, was_helpful=feedback_value))
        db.session.commit()
    return redirect('/')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))