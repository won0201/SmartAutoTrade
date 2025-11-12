import os
from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html", message="Hello from m3 (port 7103)!")

if __name__ == "__main__":
    port = int(os.getenv("PORT", "7103"))
    app.run(host="0.0.0.0", port=port, debug=True)
   
