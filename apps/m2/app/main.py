import os
from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html", message="Hello from m2!")

if __name__ == "__main__":
    port = int(os.getenv("PORT", "7102"))
    app.run(host="0.0.0.0", port=port, debug= True)
    
